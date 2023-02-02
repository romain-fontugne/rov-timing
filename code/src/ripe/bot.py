import argparse
import arrow
import json
import logging
import pyotp
import radix
import random
import requests
import time
import urllib.parse

from lxml import etree


class Bot(object):

    def __init__(self, config_fname="config.json"):
        """ Initialize crawler with variables from config file"""

        with open(config_fname, 'r') as fp:
            config = json.load(fp)

            logging.basicConfig(filename=config['log']['error'],
                            filemode='a',
                            format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S',
                            level=logging.WARN)

            self.auth_url = config['auth_url']
            self.url = config['url']

            self.username = config['credentials']['username']
            self.password = config['credentials']['password']
            self.totp_secret = config['credentials']['totp_secret']
            self.totp = pyotp.TOTP(self.totp_secret)

            self.rtree = radix.Radix()
            for prefix in config['resources']['prefix']:
                self.rtree.add(prefix)

            self.asns = config['resources']['asn']

            self.cookies = requests.cookies.RequestsCookieJar()
            self.cookies.set(
                    'activeMembershipId', 
                    config['credentials']['active_membership'],
                    domain='.ripe.net'
                    )

        self.log = open(config['log']['timing'], 'a')

    # Code from: https://gist.github.com/ties/b5f5572f2578b6b5b6c304fee019ad0a
    def login(self):
        """ Input username/password on the login page and complete 2fa.

        Returns True if succesful login."""

        # Get the initial form for SSO token
        s = requests.Session()
        res = s.get(self.auth_url)
        root = etree.HTML(res.text)

        csrf = root.xpath('//input[@name="org.scalatra.CsrfTokenSupport.key"]')[0].get('value')
        print('csrf ', csrf)

        auth_resp = s.post(
            self.auth_url,
            headers={
                "referer": self.auth_url
            },
            data={
                "org.scalatra.CsrfTokenSupport.key": csrf,
                "username": self.username,
                "password": self.password,
                "originalUrl": self.auth_url
            },
            allow_redirects=False)

        print(auth_resp.text)
        if "Two-step verification" in auth_resp.text:
            if not self.totp_secret:
                raise ValueError("Two-factor verification was enabled for account but secret was not provided.")

            print('2fa ')
            root = etree.HTML(auth_resp.text)
            csrf = root.xpath('//input[@name="org.scalatra.CsrfTokenSupport.key"]')[0].get('value')

            # Try to create totp instance
            totp_code = self.totp.now()

            auth_resp = s.post(
                urllib.parse.urljoin(self.auth_url, "two-factor-authentication"),
                headers={
                    "referer": auth_resp.url
                },
                data={
                    "org.scalatra.CsrfTokenSupport.key": csrf,
                    "securityCode": totp_code
                },
                allow_redirects=False)

        # The HTTP 200 for 2fa is handled above. Both paths that arrive here have
        # a HTTP 302 for success.
        print('next code', auth_resp.status_code)
        if auth_resp.status_code != 302:
            raise ValueError("Authentication failed. Status code=%s" % auth_resp.status_code)

        self.cookies.set( 
                'crowd.token_key', 
                auth_resp.cookies['crowd.token_key'], 
                domain='.ripe.net'
                )

        return True


    def create_roa(self, prefix, asn, maxlength):
        """Create a ROA for the given prefix, ASN, and max. prefix length.

        Assumes the bot is already logged in
        """

        # check that prefix/asn match the configured resources
        assert str(asn) in self.asns
        rnode = self.rtree.search_best(prefix)
        assert rnode is not None

        data = { 
                "added":[
                    {
                    "asn":"AS"+str(asn),
                    "prefix":prefix,
                    "maximalLength":str(maxlength)
                    }
                ],
                }

        # sending post request and saving response as response object
        headers = {'Content-type': 'application/json'}
        api_resp = requests.post(
                url = self.url, 
                headers=headers, 
                data = json.dumps(data), 
                cookies=self.cookies
                )

        if api_resp.status_code == 204:
            now = arrow.utcnow().format()
            self.log.write(f'{now},create,{prefix},{asn},{maxlength}\n')

            return True

        return False


    def delete_roa(self, prefix, asn, maxlength=None):
        """Delete the ROA for the given prefix, ASN.

        Assumes the bot is already logged in
        """
        # check that prefix/asn match the configured resources
        assert str(asn) in self.asns
        rnode = self.rtree.search_best(prefix)
        assert rnode is not None

        if maxlength is None:
            maxlength = prefix.rpartition('/')[2]

        data = { 
                "deleted":[
                    {
                    "asn":"AS"+str(asn),
                    "prefix":prefix,
                    "maximalLength": maxlength
                    }
                ],
                }

        # sending post request and saving response as response object
        headers = {'Content-type': 'application/json'}
        api_resp = requests.post(
                url = self.url, 
                headers=headers, 
                data = json.dumps(data), 
                cookies=self.cookies
                )
        
        if api_resp.status_code == 204:
            now = arrow.utcnow().format()
            self.log.write(f'{now},delete,{prefix},{asn},{maxlength}\n')
            return True

        return False


    def close(self):
        """Close log/error files."""

        self.log.close()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Automated creation/deletion of ROAs.')
    parser.add_argument('--delay_max', default=0, type=int, 
            help='time window to preform the action in minutes (default: 0)')

    # Subcommands
    subcommands = parser.add_subparsers(dest='action', required=True)

    ## Print 2FA token
    token = subcommands.add_parser('token')
    
    ## Create ROA
    create = subcommands.add_parser('create')
    create.add_argument('prefix', help='prefix for the ROA')
    create.add_argument('asn', help='origin ASN for the ROA (e.g. 2497)')
    create.add_argument('maxPrefixLength', help='Maximum prefix length for the ROA')

    ## Delete ROA
    delete = subcommands.add_parser('delete')
    delete.add_argument('prefix', help='prefix for the ROA')
    delete.add_argument('asn', help='origin ASN for the ROA (e.g. 2497)')

    args = parser.parse_args()

    try:
        # Wait to perform the action
        win_sec = args.delay_max*60
        delay = random.randint(0, win_sec) 
        time.sleep(delay)

        bot = Bot()

        if args.action == 'token':
            print(bot.totp.now())
        elif bot.login():
            success = False
            if args.action == 'create':
                success = bot.create_roa(args.prefix, args.asn, args.maxPrefixLength)
            elif args.action == 'delete':
                success = bot.delete_roa(args.prefix, args.asn)

            if not success:
                raise Exception(f'Failed to {args.action} ROA!')
        else:
            raise Exception('Failed login!')

        bot.close()

    # Log any error that could happen
    except Exception as e:
        logging.error('Error', exc_info=e)

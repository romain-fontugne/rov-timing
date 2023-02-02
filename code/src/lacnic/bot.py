import argparse
import arrow
import json
import logging
import radix
import random
import time
from oauthlib.oauth2 import LegacyApplicationClient
from requests_oauthlib import OAuth2Session


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
            self.client_id = config['credentials']['client_id']
            self.client_secret = config['credentials']['client_secret']

            self.rtree = radix.Radix()
            for prefix in config['resources']['prefix']:
                self.rtree.add(prefix)

            self.asns = config['resources']['asn']

        self.log = open(config['log']['timing'], 'a')

    def login(self):
        """ OAuth2 authentication with LACNIC.

        Returns True if succesful login."""

        client = LegacyApplicationClient(client_id=self.client_id)
        self.api = OAuth2Session( client=client )
        self.api.fetch_token(token_url=self.auth_url,
            username=self.username, password=self.password, 
            client_id=self.client_id, client_secret=self.client_secret, 
            scope=['roa:info', 'roa:delete', 'roa:create'])

        return self.api.authorized

    def create_roa(self, prefix, asn, maxlength, startdate=None, enddate=None):
        """Create a ROA for the given prefix, ASN, and max. prefix length.

        Assumes the bot is already logged in
        """

        # check that prefix/asn match the configured resources
        assert str(asn) in self.asns
        rnode = self.rtree.search_best(prefix)
        assert rnode is not None

        if startdate == None:
            startdate = arrow.utcnow()
        if enddate == None:
            enddate = startdate.shift(years=1)
        roa_id = prefix+'_AS'+str(asn)+'_'+startdate.format('YYYY-MM-DD')


        data = {
            "asn": int(asn),
            "name": roa_id,
            "notValidAfter": enddate.format("YYYY-MM-DD"),
            "notValidBefore": startdate.format("YYYY-MM-DD"),
            "resources": [
                {
                "maximalLegth": str(maxlength),
                "prefix": prefix
                }
            ]
        }

        # sending post request and saving response as response object
        headers = {'Content-type': 'application/json'}
        api_resp = self.api.post(
                url = self.url, 
                headers=headers, 
                data = json.dumps(data), 
                )

        if api_resp.status_code == 200:
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

        # sending get request and saving response as response object
        headers = {'accept': 'application/json'}
        params = {'asn': asn}
        api_resp = self.api.get(
                url = self.url, 
                headers=headers, 
                params=params
                )

        if api_resp.status_code != 200:
            logging.error(f'Failed to list existing ROAs. Status code {api_resp.status_code}')
            logging.error(api_resp.text)
            return False

        deleted = False
        roas = api_resp.json()
        for roa in roas:
            for res in roa['resources']:
                if roa['asn'] == int(asn) and res['prefix'] == prefix and res['maximalLegth'] == maxlength:
                    api_delete = self.api.delete(self.url+f'/{roa["serialNumber"]}')
            
                    if api_delete.status_code == 200:
                        now = arrow.utcnow().format()
                        self.log.write(f'{now},delete,{prefix},{asn},{maxlength}\n')
                        deleted = True
                    else:
                        logging.error(f'Failed to delete existing ROA. Status code {api_delete.status_code}')
                        logging.error(api_delete.text)

        return deleted


    def close(self):
        """Close log/error files."""

        self.log.close()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Automated creation/deletion of ROAs.')
    parser.add_argument('--config', default='config.json', type=str, 
            help='configuration file with credentials and resources details')
    parser.add_argument('--delay_max', default=0, type=int, 
            help='time window to preform the action in minutes (default: 0)')

    # Subcommands
    subcommands = parser.add_subparsers(dest='action', required=True)

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

        bot = Bot(config_fname=args.config)

        if bot.login():
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

import argparse
import base64
import arrow
import ipaddress
import json
import logging
import radix
import random
import requests
import time

from lxml import objectify

import OpenSSL
from OpenSSL import crypto


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

            self.apikey = config['credentials']['apikey']
            self.orgid = config['credentials']['orgid']
            self.urls = config['urls']
            self.key_fname = config['credentials']['keypair']

            self.rtree = radix.Radix()
            for prefix in config['resources']['prefix']:
                self.rtree.add(prefix)

            self.asns = config['resources']['asn']

        self.log = open(config['log']['timing'], 'a')


    def create_roa(self, prefix, asn, maxlength):
        """Create a ROA for the given prefix, ASN, and max. prefix length.

        Assumes the bot is already logged in
        """

        # check that prefix/asn match the configured resources
        assert str(asn) in self.asns
        rnode = self.rtree.search_best(prefix)
        assert rnode is not None

        # Retrieve private key
        key_file = open(self.key_fname, "r")
        key = key_file.read()
        key_file.close()
        pkey = crypto.load_privatekey(crypto.FILETYPE_PEM, key)

        # ROA attributes
        now = int(arrow.utcnow().timestamp())
        roa_name = now 
        startdate = arrow.utcnow().format('MM-DD-YYYY')
        enddate = arrow.utcnow().shift(years=1).format('MM-DD-YYYY')
        prefix_net, _, prefix_len = prefix.partition('/')
        roa = f'1|{now}|{roa_name}|{asn}|{startdate}|{enddate}|{prefix_net}|{prefix_len}|{maxlength}|'

        # Sign ROA
        sign = OpenSSL.crypto.sign(pkey, bytes(roa, 'utf8'), "sha256") 
        sign64 = base64.b64encode(sign).decode('utf-8')
        roa_payload = f"""
        <roa xmlns="http://www.arin.net/regrws/rpki/v1"> 
            <signature>{sign64}</signature> 
            <roaData>{roa}</roaData> 
        </roa>"""

        # sending post request and saving response as response object
        url = self.urls['create'].format(orgid=self.orgid, apikey=self.apikey)
        api_resp = requests.post(
                url = url,
                params = {'apikey': self.apikey, 'format': 'xml'},
                data = roa_payload,
                )

        if api_resp.status_code == 200:
            now = arrow.utcnow().format()
            self.log.write(f'{now},create,{prefix},{asn},{maxlength}\n')

            return True
        else:
            print(api_resp)
            print(api_resp.text)

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

        # get existing roas
        url = self.urls['list'].format(orgid=self.orgid)
        api_resp = requests.get(
                url = url,
                params = {'apikey': self.apikey}
                )

        # find matching roas
        deleted = False
        queried_net = ipaddress.ip_network(prefix)
        roas = objectify.fromstring(api_resp.content)
        for roa in roas.roaSpec:
            roa_asn, _, _, _, roa_resource, roa_handle = roa.getchildren()
            roa_len, _, roa_af, _, roa_start = roa_resource.getchildren()
            
            roa_prefix = str(roa_start)
            if roa_af == 4:
                roa_prefix = roa_prefix.replace('000','0')
            
            roa_net = ipaddress.ip_network(f'{roa_prefix}/{roa_len}')

            if str(roa_asn) == str(asn) and roa_net == queried_net:
                # Delete this ROA 
                url = self.urls['delete'].format(roa_handle=roa_handle)
                api_resp = requests.delete(
                        url = url,
                        params = {'apikey': self.apikey}
                )

                if api_resp.status_code == 200:
                    now = arrow.utcnow().format()
                    self.log.write(f'{now},delete,{prefix},{asn},{maxlength}\n')
                    deleted = True
                else:
                    logging.error(api_resp.status_code)
                    logging.error(api_resp.text)

        return deleted


    def close(self):
        """Close log/error files."""

        self.log.close()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Automated creation/deletion of ROAs.')
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

        bot = Bot()

        success = False
        if args.action == 'create':
            success = bot.create_roa(args.prefix, args.asn, args.maxPrefixLength)
        elif args.action == 'delete':
            success = bot.delete_roa(args.prefix, args.asn)

        if not success:
            raise Exception(f'Failed to {args.action} ROA!')

        bot.close()

    # Log any error that could happen
    except Exception as e:
        logging.error('Error', exc_info=e)







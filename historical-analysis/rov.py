#!/usr/bin/env python3

import appdirs
from collections import defaultdict
import glob
import gzip
import json
import os
import math
import portion
import radix
import shutil
import sys
import csv
import argparse
import pandas as pd

import urllib.request as request
from contextlib import closing

from config import *

# RPKI_ARCHIVE_URLS = [ 
#         'https://ftp.ripe.net/ripe/rpki/afrinic.tal/{year:04d}/{month:02d}/{day:02d}/roas.csv',
#         'https://ftp.ripe.net/ripe/rpki/apnic.tal/{year:04d}/{month:02d}/{day:02d}/roas.csv',
#         'https://ftp.ripe.net/ripe/rpki/arin.tal/{year:04d}/{month:02d}/{day:02d}/roas.csv',
#         'https://ftp.ripe.net/ripe/rpki/lacnic.tal/{year:04d}/{month:02d}/{day:02d}/roas.csv',
#         'https://ftp.ripe.net/ripe/rpki/ripencc.tal/{year:04d}/{month:02d}/{day:02d}/roas.csv',
#         ]

# DEFAULT_RPKI_URLS = [ 
#         'https://rpki.gin.ntt.net/api/export.json'
#         ]

# CACHE_DIR = appdirs.user_cache_dir('rov', 'IHR')
# DEFAULT_RPKI_DIR = CACHE_DIR+'/db/rpki/'
# RPKI_FNAME = '*.*'

class ROV(object):

    def __init__( self, rpki_urls=DEFAULT_RPKI_URLS, rpki_dir=DEFAULT_RPKI_DIR):
        """Initialize ROV object with databases URLs"""
        
        self.urls = {}
        self.rpki_dir = rpki_dir
        self.urls[rpki_dir] = rpki_urls
          
        self.roas = {
                'rpki': radix.Radix()
                }
    
    def load_rpki(self):
        """Parse the RPKI data and load it in a radix tree"""

        for fname in glob.glob(self.rpki_dir+RPKI_FNAME):
            sys.stderr.write(f'Loading: {fname}\n')
            with open(fname, 'r') as fd:
                if fname.endswith('.json'):
                    data = json.load(fd)
                elif fname.endswith('.csv'):
                    ta = guess_ta_name(fname)
                    data = {'roas': [] }
                    rows = csv.reader(fd, delimiter=',')

                    # skip the header
                    next(rows)

                    for row in rows:
                        # Assume the same format as the one in RIPE archive
                        # https://ftp.ripe.net/ripe/rpki/
                        maxLength = int(row[3]) if row[3] else int(row[2].rpartition('/')[2])
                        data['roas'].append( {
                            'uri': row[0],
                            'asn': row[1],
                            'prefix': row[2],
                            'maxLength': maxLength,
                            'startTime': row[4],
                            'endTime': row[5],
                            'ta': ta
                        } )

                else:
                    sys.stderr.write('Error: Unknown file format for RPKI data!')
                    return 


                for rec in data['roas']:
                    if( isinstance(rec['asn'], str) 
                       and rec['asn'].startswith('AS') ):
                        asn = int(rec['asn'][2:])
                    else:
                        asn = int(rec['asn'])

                    rnode = self.roas['rpki'].search_exact(rec['prefix'])
                    if rnode is None:
                        rnode = self.roas['rpki'].add(rec['prefix'])

                    if asn not in rnode.data:
                        rnode.data[asn] = []

                    roa_details = {
                        'maxLength': rec['maxLength'],
                        'ta': rec['ta']
                    }

                    if 'startTime' in rec:
                        roa_details['startTime'] = rec['startTime']
                        roa_details['endTime'] = rec['endTime']

                    if 'uri' in rec:
                        roa_details['uri'] = rec['uri']

                    rnode.data[asn].append( roa_details )


    def download_databases(self, overwrite=True):
        """Download databases in the cache folder. 

            Overwrite=True clears the cache before downloading new files.
            Set overwrite=False to download only missing databases."""

        # TODO implement automatic update based on 

        for folder, urls in self.urls.items():

            # Clear the whole cache if overwrite
            if overwrite and os.path.exists(folder):
                shutil.rmtree(folder)

            # Create the folder if needed
            os.makedirs(folder, exist_ok=True)

            for url in urls:
                print(url)
                # Check if the file already exists
                fname = url.rpartition('/')[2]

                # all files from RIPE's RPKI archive have the same name
                # 'roas.csv', change it with the tal name
                if fname == 'roas.csv':
                    fname = guess_ta_name(url)+'.csv'

                    if os.path.exists(folder+fname) and not overwrite:
                        continue

                    sys.stderr.write(f'Downloading: {url}\n')
                    with closing(request.urlopen(url)) as r:
                        with open(folder+fname, 'wb') as f:
                                print(folder+fname)
                                shutil.copyfileobj(r, f)

                                
    def check(self, row):
            """Compute the state of the given prefix, origin ASN pair"""
            
            prefix = row['prefix']
            origin_asn = row['origin_asn']
            
            try:
                origin_asn = int(origin_asn)
            except:
                return None
            
            #skip the reserved asns
            if (int(origin_asn) in R1 or int(origin_asn) in R2):
                return None

            prefix_in = prefix.strip()
            prefixlen = int(prefix_in.partition('/')[2])
            states = {}

            # include the query in the results
            states['query'] = {
                    'prefix': prefix,
                    'asn': origin_asn
                    }

            # Check routing status
            for name, rtree in self.roas.items():
                # Default to NotFound 
                selected_roa = None
                status = {'status': 'NotFound', 'status_code' : 0}

                rnodes = rtree.search_covering(prefix)
                if len(rnodes) > 0:
                    # report invalid with the first roa of the most specific prefix
                    rnode = rnodes[0]
                    status = {'status': 'Invalid', 'status_code': 2, 'prefix': rnode.prefix}
                    key = next(iter(rnode.data.keys()))
                    selected_roa = rnode.data[key][0]

                for rnode in rnodes:
                    if origin_asn in rnode.data: # Matching ASN

                        for roa in rnode.data[origin_asn]:
                            status = {'status': 'Invalid,more-specific','status_code':3, 'prefix': rnode.prefix}
                            selected_roa = roa

                            # check prefix length
                            if( ('maxLength' in roa and roa['maxLength'] >= prefixlen) 
                                or (prefix_in == rnode.prefix)):

                                status = {'status': 'Valid', 'status_code': 1, 'prefix': rnode.prefix}
                                selected_roa = roa

                                break

                        if status['status'] == 'Valid':
                            break

                # copy roa attributes in the status report
                if selected_roa is not None:
                    for k,v in selected_roa.items():
                        status[k] = v

                states[name] = status

            #return {'status_code':status['status_code'],'startTime': status['startTime'], 'tal':status['ta']}
            return status

def guess_ta_name(url):
    rirs = ['afrinic', 'arin', 'lacnic', 'ripencc', 'apnic']

    for rir in rirs:
        if (rir+'.tal' in url or rir+'.csv' in url):
            return rir

    return 'unknown'
                                
def main():
    
    parser = argparse.ArgumentParser(
            description='Check the validity of the given prefix and origin ASN in \
                the historical RPKI RIPE repo https://ftp.ripe.net/rpki/')
    
    parser.add_argument(
            '--rpki_archive',
            help='Load past RPKI data for the given date (format is year/mo/da). \
                    The given date should be greater than 2018/04/04.',
            )
        
    parser.add_argument(
            '--input',
            help='Input file. Should be a csv file with header as \"prefix, origin_as\"',
    )
    
    args = parser.parse_args()
    
    #rpki_url = args.rpki_url
    rpki_dir = DEFAULT_RPKI_DIR 
    # Compute RPKI archive URLs if the rpki_archive option is given
    if args.rpki_archive is not None:
        year, month, day = args.rpki_archive.split('/')
        rpki_dir += '/'+args.rpki_archive+'/'
        rpki_url = []
        for url in RPKI_ARCHIVE_URLS:
            rpki_url.append( url.format(year=int(year), month=int(month), day=int(day)) )
    
    if args.input is not None:
        df = pd.read_csv(args.input)
    
    # Main program
    rov = ROV(rpki_url, rpki_dir=rpki_dir)
    rov.download_databases(False)
    rov.load_rpki()
    
    #validation_results = rov.check(args.prefix, args.ASN),
    validation_results = rov.check({'prefix':'103.138.210.254/32', 'origin_asn':'139038'})
    print(json.dumps(validation_results, indent=4))
    
    #df['status'] = df.apply(rov.check, axis=1)
    
    #df = df.loc[df.status.str.contains('Invalid')]
    
    #df.to_csv('data/out.csv',index=False)
    
    
if __name__ == "__main__":
    main()


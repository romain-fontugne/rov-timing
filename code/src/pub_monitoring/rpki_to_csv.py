import arrow
from collections import defaultdict
import os
import sys
from glob import glob
import tarfile
import ujson
import subprocess

ROA_URI = [
        #'AFRINIC': 
        'F362FC0B/97F3543019E311ECB7BBB859D8A014CE',
        #'APNIC': 
        'A91A001E/35FA0F561D7811E293771FC408B02CD2',
        #'ARIN': 
        '5e4a23ea-e80a-403e-b08c-2171da2157d3/521eb33f-9672-4cd9-acce-137227e971ac/f5a8e327-ebf4-4f4b-9073-90acd61797cc',
        #'LACNIC': 
        '5ecad2d5-c291-4a29-99f5-bfbe943581bc', 
        '9ddc4dcd-fff1-4698-bc7c-be5edda4e615',
        #'RIPE': 
        'eb/6f232e-2275-44e9-91c0-c7397a2669a9/1'
        ]

class RPKI_to_CSV():
    def __init__(self, dumps_folder, asn, reverse=False):
        """ 
        dumps_folder: copy from one of http://www.rpkiviews.org/ vantage point
        asn: extract only timing for the given ASN. All if set to None.
        """

        self.jsons_folder = './rpki-client-jsons/'
        os.makedirs(self.jsons_folder, exist_ok=True)

        self.dumps_folder = dumps_folder
        self.asn = int(asn)

        self.json_files = []
        self.reverse = reverse

    def extract_rpki_client_jsons(self, overwrite=False, readonly=False):
        """Extract rpki-client.json file for each downloaded archive and populate
        the list of existing json files (self.json_files)"""

        self.json_files = []
        all_tgz = glob(self.dumps_folder+'**/*.tgz', recursive=True)

        for file in all_tgz:
            tar_fname = file.rpartition('/')[2].replace('.tgz', '')
            json_fname = tar_fname+'/output/rpki-client.json'
            self.json_files.append(self.jsons_folder+json_fname)
            
            if( readonly or 
                (os.path.exists(self.jsons_folder+json_fname) and not overwrite) ):
                continue

            with tarfile.open(file) as tar:
                json_file = tar.getmember(json_fname)
                print(json_file)
                tar.extract(json_file, path=self.jsons_folder)

    def extract_roas(self, overwrite=False, readonly=False):
        """Extract ROA data to '{self.asn}.json' files each downloaded archive 
        and populate the list of existing json files (self.json_files)"""

        self.json_files = []
        all_tgz = glob(self.dumps_folder+'**/*.tgz', recursive=True)

        for file in all_tgz:
            tar_fname = file.rpartition('/')[2].replace('.tgz', '')
            json_fname = tar_fname+f'/output/{self.asn}.json'
            log_fname = tar_fname+'/output/rpki-client.log'
            self.json_files.append(self.jsons_folder+json_fname)

            if ( readonly or 
                (os.path.exists(self.jsons_folder+json_fname) and not overwrite)
                ):
                continue

            if not os.path.exists(self.jsons_folder+log_fname):
                with tarfile.open(file) as tar:
                    # Extract all files of interest
                    to_extract = []
                    tar_members = tar.getmembers()
                    if self.reverse:
                        tar_members.reverse()

                    for file in tar_members:
                        if( any(directory in file.name for directory in ROA_URI) or
                            'rpki-client.log' in file.name
                            ):
                            to_extract.append(file)
                    tar.extractall(path=self.jsons_folder, members=to_extract)

            # Set publication time to log start time
            with open(self.jsons_folder+log_fname,'r') as fp:
                time, _, _ = fp.readline().partition(' ')

            roas_json = {
                    'metadata': { "buildtime": time },
                    'roas': []
                    }

            # Read ROAs content
            roas = glob(self.jsons_folder+tar_fname+"/**/*.roa", recursive=True)
            txt_output = subprocess.run(
                ["python2", "./print_roa", "--list"] + roas,
                capture_output=True, text=True)

            for line in txt_output.stdout.splitlines(): 

                sign, not_before, not_after, id, asn, prefix = line.split(" ")
                if self.asn is not None and int(asn) != self.asn :
                    continue

                roas_json['roas'].append( 
                        {
                            "expires": int(id), "time": time, "asn": int(asn), 
                            "prefix": prefix, "sign": sign, 
                            "not_before": not_before, "not_after": not_after
                        } )

            # Write json file
            with open(self.jsons_folder+json_fname, 'w') as fp:
                ujson.dump(roas_json, fp)

    def convert(self, outputfile, key=''):
        # Make sure the list of files is sorted
        self.json_files.sort()
        previous_vrps = set()

        print(f'{len(self.json_files)} json files to process')
        with open(outputfile, 'w') as csv:
            for current_file in self.json_files:

                # fetch active vrps
                current_vrps = set()
                try:
                    with open(current_file) as fp:
                        payload = fp.read()
                        if 'pub' in outputfile or 'sign' in outputfile or 'not_before' in outputfile:
                            # fix: missing expire value
                            payload = payload.replace(':,', ':"0",')

                        vrps = ujson.loads(payload)
                        current_timestamp = vrps['metadata']['buildtime']
                        key_ts = {}
                        for vrp in vrps['roas']:
                            if int(vrp['asn']) == self.asn:
                                current_vrps.add( (vrp['prefix'], vrp['expires']) )
                                if key:
                                    key_ts[(vrp['prefix'],vrp['expires'])] = vrp[key]

                except FileNotFoundError:
                    print(f'Error: could not open {current_file}\n')
                    continue

                # diff with previous vrps
                if previous_vrps:
                    for prefix in previous_vrps.union(current_vrps):
                        # Revoked ROA
                        if prefix in previous_vrps and prefix not in current_vrps:
                            csv.write(f'{prefix[0]},{current_timestamp},revoke\n')

                        # New ROA
                        if prefix not in previous_vrps and prefix in current_vrps:
                            if key:
                                csv.write(f'{prefix[0]},{key_ts[prefix]},create\n')
                            else:
                                csv.write(f'{prefix[0]},{current_timestamp},create\n')

                previous_vrps = current_vrps
                
if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('usage: {sys.argv[0]} rpkiviews_dumps/ asn')
        
    rtc = RPKI_to_CSV(sys.argv[1], sys.argv[2], reverse=False)
    rtc.extract_rpki_client_jsons()
    rtc.convert('rp_timings.csv')
    rtc.extract_roas()
    rtc.convert('pub_timings.csv')
    rtc.convert('sign_timings.csv', key='sign')
    rtc.convert('not_before_timings.csv', key='not_before')

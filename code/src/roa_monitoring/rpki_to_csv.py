import arrow
from collections import defaultdict
import subprocess
import sys
from glob import glob

class RPKI_to_CSV():
    def __init__(self, dumps_folder, asn):
        """ 
        dumps_folder: folder containing afrinic, apnic, arin, lacnic, ripe subfolders
        asn: extract only timing for the given ASN. All if set to None.
        """

        self.dumps_folder = dumps_folder
        self.asn = asn


    def convert(self):
        for rir in ['afrinic', 'apnic', 'arin', 'lacnic', 'ripe']:
            with open(f'{self.dumps_folder}/{rir}/rir_timings.csv', 'w') as csv:

                roa_serials = defaultdict(list) 
                roas_fname = glob(f'{self.dumps_folder}/{rir}/*/*.roa')
                roas_fname.sort()
                apnic_prefixes= set()

                for roa_attr in self.read_roas(roas_fname):
                    roa_serials[int(roa_attr['id'])].append(roa_attr)

                    # APNIC overwrite ROAs when adding new prefixes
                    if rir == 'apnic':
                        apnic_prefixes.add( (roa_attr['prefix'], roa_attr['asn']) )
                    csv.write(','.join(str(x) for x in roa_attr.values())+',sign\n')

                crls_fname = glob(f'{self.dumps_folder}/{rir}/*/*.crl')
                crls_fname.sort()
                for revocation in self.read_crl(crls_fname[-1], roa_serials, apnic_prefixes):
                    csv.write(','.join(str(x) for x in revocation.values())+',revoke\n')

    def read_roas(self, roas_fname):
        txt_output = subprocess.run(
            ["python2", "print_roa", "--list"] + roas_fname,
            capture_output=True, text=True)

        for line in txt_output.stdout.splitlines(): 

            time, id, asn, prefix = line.split(" ")

            if self.asn is not None and asn != self.asn :
                continue

            yield {"id": int(id), "time": time, "asn": asn, "prefix": prefix}

    def read_crl(self, crl_fname, roa_serials, prefixes):
        txt_output = subprocess.run(
            ["openssl", "crl", "-inform", "DER", "-text", "-noout", "-in", crl_fname],
            capture_output=True, text=True)

        serial = None
        for line in txt_output.stdout.splitlines():
            value = line.partition(':')[2]
            if line.strip().startswith('Serial Number:'):
                serial = int(value, base=16)

            if line.strip().startswith('Revocation Date:'):
                try:
                    timestamp = arrow.get(value, 'MMM  D HH:mm:ss YYYY ZZZ')
                except arrow.parser.ParserMatchError:
                    timestamp = arrow.get(value, 'MMM DD HH:mm:ss YYYY ZZZ')

                if serial in roa_serials:

                    for roa_attr in roa_serials[serial]:
                        yield {
                            'id': serial, 
                            'time': timestamp, 
                            'asn': roa_attr['asn'], 
                            'prefix': roa_attr['prefix']
                            }
                else:
                    # APNIC overwrite ROAs when adding new prefixes
                    if prefixes:
                        for prefix, asn in prefixes:
                            yield {
                                'id': serial, 
                                'time': timestamp, 
                                'asn': asn,
                                'prefix': prefix
                                }


                    else:
                        yield {
                            'id': serial, 
                            'time': timestamp, 
                            'asn': 'unknown', 
                            'prefix': 'unknown'
                            }


if __name__ == '__main__':
    rtc = RPKI_to_CSV(sys.argv[1], sys.argv[2])
    rtc.convert()

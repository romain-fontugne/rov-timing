# Read in the data here
from mrtparse import *
import json
import requests
import os.path
import pandas as pd
import config

class RIB(object):
    
    def __init__( self ):
        """Initialize RIB object with databases URLs"""
        pass
        
        
    def retrieveFile(self, url):

        a = url.split('/')
        fn = a[3] + '-' + a[-1]

        if os.path.exists(config.TMP_DIR + fn):
            return fn

        try:
            r = requests.get(url, allow_redirects=True, timeout=10)
            f = open(config.TMP_DIR + fn, 'wb').write(r.content)
        except Exception as e:
            print(e)
        
        return fn

    def parseMRT(self, filename):
        df = pd.DataFrame(columns=['prefix','origin_asn'])
        for entry in Reader(filename):
            data = json.loads(json.dumps([entry.data], indent=2)[2:-2])

            if (list(data['subtype'].keys())[0] == '2'):
                prefix = data['prefix']
                pl = data['prefix_length']
                as_path = data['rib_entries'][0]['path_attributes'][1]['value'][0]['value']
                origin_asn = as_path[-1]
                p = prefix + '/' + str(pl)
                df = df.append({'prefix':p, 'origin_asn':origin_asn}, ignore_index=True)
                #df.loc[df.shape[0]] = [p,origin_asn]

                df.drop_duplicates(['prefix','origin_asn'],inplace=True)
        #df.to_csv(OUTPUT_DIR + filename + '.txt', index=False)
        return df
    
def main():
    args = sys.argv[1:]
    
    rib = RIB()
    
    file = rib.retrieveFile(args[0])
    rib.parseMRT(file)
    
if __name__ == "__main__":
    main()


import config
from rib import RIB
from ipaddress import IPv6Address, IPv6Network, IPv4Network
from rov import ROV
#from roa import ROA
from bgp import BGP
from datetime import date, datetime, timedelta
import pandas as pd
import numpy as np
import os, sys

from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool

# Divide dataframe to chunks
prs = 100 # define the number of processes
SAMPLE_SIZE = 50

def download_rib(url):
    rib = RIB()
    file = rib.retrieveFile(url)
    df = rib.parseMRT(config.TMP_DIR + file)
    return df

def apply_to_df(df_chunks):
    
    for index, row in df_chunks.iterrows():
        status = rov.check(row)

        if (status is None):
            continue

        if (status['status_code'] > 1):
            df_chunks.loc[index,'status_code'] = status['status_code']
            df_chunks.loc[index,'startTime'] = status['startTime']
            df_chunks.loc[index,'ta'] = status['ta']
        else:
            continue

    return df_chunks

def process_rov(df,d):

    rpki_dir = config.DEFAULT_RPKI_DIR 
    ##Compute RPKI archive URLs
    
    rpki_url = []
    rpki_dir += "/" + "/".join([str(d.year), str(d.month), str(d.day)]) + '/' 
    for url in config.RPKI_ARCHIVE_URLS:
        rpki_url.append( url.format(year=int(d.year), month=int(d.month), day=int(d.day)) )
        
    global rov 
    rov = ROV(rpki_url, rpki_dir=rpki_dir)
    rov.download_databases(False)
    rov.load_rpki()
    
    chunk_size = int(df.shape[0]/prs)
    chunks = [df.iloc[df.index[i:i + chunk_size]] for i in range(0, df.shape[0], chunk_size)]
    
    with ThreadPool(prs) as p:
        result = p.map(apply_to_df, chunks)
    
    return pd.concat(result)

def process_bgp(df, session, date, version, hours, project, source):
    #### /!\/!\/!\/!\/!\this takes a lot of time
    bgp = BGP()
    filename = config.OUTPUT_FILE.format(date.isoformat()) + '_v' + str(version) + '.csv'
    

    if (not os.path.exists(filename)):
        f = open(filename ,'a')
        f.write("prefix,tal,peer_ip,roa_create_time,withdrawal_time,delta\n")
    else:
        f = open(filename ,'a')

    for index, row in df.iterrows():
        prefix = row['prefix']
        t = row['startTime']
        tal = row['ta']

        #elements = {}
        #elements = bgp.extractWithdrawalTimePyBGPStream(prefix, t, 1, True)
        #elements = bgp.extractWithBGPKITAPI(prefix, t, 1, project='riperis', collector=config.RIS_COLLECTOR[tal], verbose=True) 
        elements = bgp.extractWithBGPKITAPI(prefix, t, hours, project=project, collector = source, verbose=True) 
        #for peer_ip, wtime in elements.items():
        
        print('fetching',prefix,t,tal, source, 'found:', len(elements))

        for msg in elements:
            roa_create_time = datetime.strptime(t, '%Y-%m-%d %H:%M:%S')
            withdrawal_time = datetime.fromtimestamp(int(msg['timestamp']))
            delta = (withdrawal_time - roa_create_time).seconds
            
            if (session is None):
                f.write("{},{},{},{},{},{}\n".format(prefix,tal,msg['peer_ip'],roa_create_time,withdrawal_time,delta))
            else:
                query = "INSERT INTO roa_timing (prefix, tal, peer_ip, roa_create_time, withdrawal_time, delta)"
                query = query + "VALUES (%s, %s, %s, %s, %s, %s)"
                session.execute(query, (prefix, tal, peer_ip, roa_create_time, withdrawal_time, delta))
            
    if (session is None):
        f.close()

def main():
    """
    This is the main function to start the ETL process
    :return: None
    """
    args = sys.argv[1:]
    if args[0] == '--date':
        y = datetime.strptime(args[1], '%Y-%m-%d')
    else:
        d = date.today()
        y = d - timedelta(days=1)
        # Read in the data here

    #get yesterday date
    url = config.RIB_SOURCE_URL.format(y.year,str(y.month).zfill(2),str(y.day).zfill(2))
    
    if not os.path.exists(args[3] + '.tmp'):
        print("Generating tmp file")
        df = pd.read_csv(args[3], sep='|', names=['prefix','as_path'])
        df['origin_asn'] = df.apply(lambda x: x['as_path'].split(' ')[-1], axis=1)
        df.drop_duplicates(['prefix','origin_asn'], inplace=True)
        df.to_csv(args[3]+'.tmp', index=False)
        del df
    else:
        print("Tmp file found")

    df = pd.read_csv(args[3]+'.tmp', header='infer')

    if not os.path.exists(args[3] + '.rov'):
        print('Processing ROV')
        df_rov = process_rov(df,y)
        df_rov = df_rov.dropna()
        df_rov['af'] = df_rov.apply(lambda x: getVersion(x), axis=1)
        df_rov.to_csv(args[3] + '.rov', index=False)
    else:
        df_rov = pd.read_csv(args[3] + '.rov', header='infer')
        print('Rov file found',args[3] + '.rov', len(df_rov))

    df_rov4 = df_rov.loc[df_rov.af==4]
    df_rov6 = df_rov.loc[df_rov.af==6]

    print('Retrieving BGP messages')
    process_bgp(df_rov4, session=None, date=y, version=4, hours=int(args[5]), project=args[6], source=args[7])
    process_bgp(df_rov6, session=None, date=y, version=6, hours=int(args[5]), project=args[6], source=args[7])

    #os.remove(args[3])

def getVersion(row):
    try:
        network = IPv4Network(row['prefix'])
        return 4
    except:
        network = IPv6Network(row['prefix'])
        return 6

def getSample(df, size):
    try:
        df = df.sample(n=size)
    except:
        return df
    finally:
        return df

if __name__ == "__main__":
    main()
    

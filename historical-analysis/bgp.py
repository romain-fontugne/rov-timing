import json
import pybgpstream
from datetime import date, datetime, timedelta
import requests
import config
#API_ENDPOINT = "http://45.129.227.22:8001/search?"

class BGP(object):
    
    def __init__( self ):
        """Initialize BGP object with databases URLs"""
        pass
    
    def extractWithBGPKITAPI(self, prefix, starttime, hours, project, collector, verbose):
        t1 = datetime.strptime(starttime, '%Y-%m-%d %H:%M:%S')
        t2 = t1 + timedelta(hours=hours)

        params = {'prefix':prefix, 'ts_start': t1, 'ts_end': t2.isoformat(), 'project': project, 'collector': collector, 'include_super':'false','include_sub':'false','msg_type':'w','dry_run':'false'}

        headers = {"Accept": "application/json"}
        
        try:
            response = requests.post(config.API_ENDPOINT, params=params, headers=headers)
        
            #print(response.request.url)
            #print(response.request.headers)
        
            json_response = response.json()
        except Exception as e:
            print(e)
            return []

        return json_response['msgs']
       

    def extractWithdrawalTimeBGPKIT(self, broker, prefix, starttime, hours, verbose):
        t1 = datetime.strptime(starttime, '%Y-%m-%dT%H:%M:%S')
        t2 = t1 + timedelta(hours=hours)

        elems = dict()

        try:
            bgp_dumps = broker.query(start_ts=round(t1.timestamp()), end_ts=round(t2.timestamp()), data_type="update")
        except Exception as e:
            return elems

        if verbose:
            print(len(bgp_dumps), t1, t2) 

        for d in bgp_dumps:
            try:
                messages = bgpkit.Parser(url=d.url, 
                                     filters={"prefix": prefix,
                                          "type": "withdraw",
                                          }   
                                      ).parse_all()
            except Exception as e:
                continue

            for m in messages:
                if m.peer_ip not in elems:
                    elems[m.peer_ip] = m.timestamp
                if verbose:
                    print(f"{m.peer_ip},{datetime.fromtimestamp(m.timestamp)}")
  
        return elems

    def extractWithdrawalTimePyBGPStream(self,prefix, starttime, hours, verbose):
        t1 = datetime.strptime(starttime, '%Y-%m-%d %H:%M:%S')
        t2 = t1 + timedelta(hours=hours)

        elems = dict()
        
        if verbose:
            print(prefix, t1, t2)
        
        try:

            stream = pybgpstream.BGPStream(
                from_time=starttime, until_time=t2.isoformat(),
                collectors=["rrc00","rrc14"],
                record_type="updates",
                filter="prefix " + prefix
            )

            #stream.set_data_interface_option("broker", "cache-dir", "cache")

        except Exception as e:
            print(e)
            return elems


        for m in stream:

            if m.type != 'W':
                continue

            peer_ip = m.peer_address

            if peer_ip not in elems:
                elems[peer_ip] = m.time
            if verbose:
                print(f"{peer_ip},{m.time}")

        return elems

    
def main():
    
    #broker = broker = bgpkit.Broker()
    bgp = BGP()
    #elements = bgp.extractWithdrawalTimePyBGPStream('194.133.122.0/24', '2018-01-01T01:09:53', 1, True)
    #print(elements)
    bgp.extractWithBGPKITAPI('87.232.255.0/24', '2018-04-30 08:28:20', 1, project='riperis', collector='rrc00', verbose=True)

if __name__ == "__main__":
    main()



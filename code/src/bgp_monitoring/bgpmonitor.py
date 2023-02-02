import argparse
import appdirs
import arrow
from collections import defaultdict
import pickle
import pybgpstream
import os

FILTER = 'prefix more {}'

class BGPMonitor(object):
    def __init__(self, prefix_list, starttime, endtime, my_asns):
        """Initialize BGP monitors for the given list of prefixes.

        prefix_list: list of prefixes to monitor
        starttime: start of the monitoring period of time. Should be close to 
        RIB dump times (00:00, 08:00, or 16:00 UTC).
        endtime: end of the monitoring period of time.
        my_asns: is the list of the last managed ASNs on the path (used to find upstream nets)
        """

        self.prefix_list = prefix_list
        self.my_asns = my_asns
        self.monitors = { prefix.lower():{} for prefix in prefix_list}
        self.log_data = { 
            prefix: {
                'time': [],
                'reachability': [],
                'upstream': [],
                'aspath': []
            } 
            for prefix in prefix_list }

        self.starttime = arrow.get(starttime)
        self.endtime = arrow.get(endtime)

        self.cachedir = appdirs.user_cache_dir('rov-timing', 'IHR')+'/mrt'
        os.makedirs(self.cachedir, exist_ok=True)


    def fetch_data(self, collector='rrc00'):

        print('reading ribs..')
        bm.read_rib(collector)

        # Log state at the begining of the mesurement period
        for prefix in self.prefix_list:
            self.log_state(prefix, self.starttime)

        print('reading updates..')
        bm.read_updates(collector)

        # Log state at the end of the mesurement period
        for prefix in self.prefix_list:
            self.log_state(prefix, self.endtime)


    def read_rib(self, collector='rrc00'):
        """Read a RIB to bootstrap the monitoring process"""

        start = self.starttime.shift(hours=-1)
        end = self.starttime.shift(hours=1)
        stream = pybgpstream.BGPStream(
            from_time=int(start.timestamp()), until_time=int(end.timestamp()),
            record_type="ribs", collector=collector,
        )
        stream.set_data_interface_option("broker", "cache-dir", self.cachedir)

        # Filter for given prefixes
        for prefix in self.prefix_list:
            stream.stream.parse_filter_string(FILTER.format(prefix))

        for elem in stream:
            # Extract the prefix and origin ASN
            msg = elem.fields
            prefix = msg['prefix']
            router = elem.peer_address
            self.monitors[prefix][router] = msg['as-path'].split(' ')

    def read_updates(self, collector='rrc00' ):
        """Read update messages and plot reachability over time."""

        stream = pybgpstream.BGPStream(
            from_time=int(self.starttime.timestamp()), 
            until_time=int(self.endtime.timestamp()),
            record_type="updates", collector=collector,
        )
        stream.set_data_interface_option("broker", "cache-dir", self.cachedir)

        # Filter for given prefixes
        for prefix in self.prefix_list:
            stream.stream.parse_filter_string(FILTER.format(prefix))

        for elem in stream:
            # Update routers state
            msg = elem.fields
            prefix = msg['prefix']
            router = elem.peer_address

            # Log new state only if it really changed
            log = False

            if elem.type == 'W':
                if router in self.monitors[prefix]:
                    del self.monitors[prefix][router] 
                    log = True
            else:
                current_aspath = None
                if router in self.monitors[prefix]:
                    current_aspath = ' '.join(self.monitors[prefix][router])
                if current_aspath != msg['as-path'] or current_aspath is None:
                    self.monitors[prefix][router] = msg['as-path'].split(' ') 
                    log = True

            if log:
                self.log_state(prefix, elem.time)

    def log_state(self, prefix, timestamp):
        """Timestamp the current number of active monitors/upstreams for the 
        given prefix."""

        self.log_data[prefix]['time'].append( arrow.get(timestamp).datetime )

        # keep the number of peers seeing the prefix
        nb_active = len(self.monitors[prefix])
        self.log_data[prefix]['reachability'].append( nb_active )

        # keep track of upstream seen in AS paths
        upstreams = defaultdict(int)
        for aspath in self.monitors[prefix].values():
            my_asn = [asn for asn in self.my_asns if asn in aspath] 
            if len(my_asn) == 0:
                print(f'Error! {self.my_asns} is not on the path for {prefix}: {aspath}')
                continue

            upstream = aspath[ aspath.index(my_asn[0]) - 1 ]
            upstreams[upstream] += 1
        self.log_data[prefix]['upstream'].append( upstreams )

        # keep track of all AS paths
        self.log_data[prefix]['aspath'].append( list(self.monitors[prefix].values()) )


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Retrieve RIS/RV data for monitored prefixes')
    parser.add_argument('--collector', default='rrc00',
            help='Name of the BGP collector (default: rrc00)')
    parser.add_argument('--start-date', default='2021-10-07', 
            help='Starting date of the measurement (default: 2021-10-07).')
    parser.add_argument('--end-date', default = arrow.now().format('YYYY-MM-DD'),
            help="Ending date of the measurement (default is today's date)")
    parser.add_argument('--my-upstream', help='Upper AS in my control', nargs='+',
            default=['3130', '17660', '55722', '23676'])
    parser.add_argument('--prefixes', help='Prefixes to monitor', nargs='+',
            default = [
                # APNIC
                "103.171.218.0/24", "103.171.219.0/24", 
                "2001:df7:5380::/48", "2001:df7:5381::/48",
                # RIPE
                "151.216.4.0/24", "151.216.5.0/24", 
                "2001:7fc:2::/48", "2001:7fc:3::/48",
                # AFRINIC
                "102.218.96.0/24", "102.218.97.0/24",
                "2001:43f8:df0::/48", "2001:43f8:df1::/48",
                # ARIN
                "165.140.104.0/24", "165.140.105.0/24",
                "2620:9e:6000::/48", "2620:9e:6001::/48",
                # LACNIC
                "201.219.252.0/24", "201.219.253.0/24",
                "2801:1e:1800::/48", "2801:1e:1801::/48",
                # RIPE /23
                "151.216.32.0/24", "151.216.33.0/24",
                "151.216.34.0/24"
            ])

    args = parser.parse_args()

    print(f'starting date: {args.start_date}')
    print(f'ending date: {args.end_date}')

    bm = BGPMonitor(args.prefixes, args.start_date, args.end_date, args.my_upstream)

    bm.fetch_data(args.collector)
    print('saving..')
    with open(f'bgpmonitor_{args.start_date}_{args.end_date}_{args.collector}.pickle', 'wb') as fp:
        pickle.dump(bm, fp)

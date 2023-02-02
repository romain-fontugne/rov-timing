import argparse
import pickle
import arrow
import datetime
import numpy as np
from collections import Counter, defaultdict
from matplotlib import pylab as plt
import os
import pickle
import ujson
from bgpmonitor import BGPMonitor

asn_file = open('rrc00_asns.txt', 'w')

MY_ASNS = ['3130', '3970', '17660', '55722', '23676']
MIN_NB_PEERS = 5
MAX_DELAY_HOURS = 24 # ROA wiggling should be less than 24h

PREFIX_PROP = {
        "103.171.219.0/24": {'label': "APNICv4", 'color': 'C0', 'linestyle': '-', 
            'startdate': arrow.get('2021-11-01'), 'enddate': arrow.get('2022-11-01') },
        "2001:df7:5381::/48": {'label': "APNICv6", 'color': 'C0', 'linestyle': '--', 
            'startdate': arrow.get('2021-11-01'), 'enddate': arrow.get('2022-11-01') },
        "151.216.5.0/24": {'label': "RIPEv4", 'color': 'C2', 'linestyle': '-', 
            'startdate': arrow.get('2021-11-01'), 'enddate': arrow.get('2022-11-01') }, 
        "2001:7fc:3::/48":{'label': "RIPEv6", 'color': 'C2', 'linestyle': '--',
            'startdate': arrow.get('2021-11-01'), 'enddate': arrow.get('2022-11-01') },
        "102.218.97.0/24":{'label': "AFRINICv4", 'color': 'C1', 'linestyle': '-',
            'startdate': arrow.get('2021-11-01'), 'enddate': arrow.get('2022-11-01') },
        "2001:43f8:df1::/48":{'label': "AFRINICv6", 'color': 'C1', 'linestyle': '--', 
            'startdate': arrow.get('2021-11-01'), 'enddate': arrow.get('2022-11-01') },
        "165.140.105.0/24": {'label': "ARINv4", 'color': 'C9', 'linestyle': '-',
            'startdate': arrow.get('2021-11-01'), 'enddate': arrow.get('2022-04-21')},
        "2620:9e:6001::/48": {'label': "ARINv6", 'color': 'C9', 'linestyle': '--', 
            'startdate': arrow.get('2021-11-01'), 'enddate': arrow.get('2022-04-21')},
        "201.219.253.0/24": {'label': "LACNICv4", 'color': 'C3', 'linestyle': '-',
            'startdate': arrow.get('2022-02-01'), 'enddate': arrow.get('2022-11-01') },
        "2801:1e:1801::/48": {'label': "LACNICv6", 'color': 'C3', 'linestyle': '--',
            'startdate': arrow.get('2022-02-01'), 'enddate': arrow.get('2022-11-01') },
        }

PREFIX_PROP_RIPE= {
        #MARIIX
        "151.216.32.0/24": {'label': "RIPE-A", 'color': 'C0', 'linestyle': '-', 
            'startdate': arrow.get('2022-05-06'), 'enddate': arrow.get('2023-05-01') },
        #CENPAC
        "151.216.33.0/24": {'label': "RIPE-B", 'color': 'C2', 'linestyle': '-', 
            'startdate': arrow.get('2022-05-06'), 'enddate': arrow.get('2023-05-01') },
        #BT
        "151.216.34.0/24": {'label': "RIPE-C", 'color': 'C1', 'linestyle': '-', 
            'startdate': arrow.get('2022-05-06'), 'enddate': arrow.get('2023-05-01') },
        }

PREFIX_PROP_FIX = {
        "103.171.219.0/24": {'label': "APNICv4", 'color': 'C0', 'linestyle': '-', 
            'startdate': arrow.get('2025-04-21'), 'enddate': arrow.get('2022-11-01') },
        "2001:df7:5381::/48": {'label': "APNICv6", 'color': 'C0', 'linestyle': '--', 
            'startdate': arrow.get('2025-04-21'), 'enddate': arrow.get('2022-11-01') },
        "151.216.5.0/24": {'label': "RIPEv4", 'color': 'C2', 'linestyle': '-', 
            'startdate': arrow.get('2022-04-21'), 'enddate': arrow.get('2022-11-01') }, 
        "2001:7fc:3::/48":{'label': "RIPEv6", 'color': 'C2', 'linestyle': '--',
            'startdate': arrow.get('2022-04-21'), 'enddate': arrow.get('2022-11-01') },
        "102.218.97.0/24":{'label': "AFRINICv4", 'color': 'C1', 'linestyle': '-',
            'startdate': arrow.get('2022-04-21'), 'enddate': arrow.get('2022-11-01') },
        "2001:43f8:df1::/48":{'label': "AFRINICv6", 'color': 'C1', 'linestyle': '--', 
            'startdate': arrow.get('2022-04-21'), 'enddate': arrow.get('2022-11-01') },
        "165.140.105.0/24": {'label': "ARINv4", 'color': 'C9', 'linestyle': '-',
            'startdate': arrow.get('2022-04-21'), 'enddate': arrow.get('2023-04-21')},
        "2620:9e:6001::/48": {'label': "ARINv6", 'color': 'C9', 'linestyle': '--', 
            'startdate': arrow.get('2022-04-21'), 'enddate': arrow.get('2023-04-21')},
        "201.219.253.0/24": {'label': "LACNICv4", 'color': 'C3', 'linestyle': '-',
            'startdate': arrow.get('2025-04-21'), 'enddate': arrow.get('2022-11-01') },
        "2801:1e:1801::/48": {'label': "LACNICv6", 'color': 'C3', 'linestyle': '--',
            'startdate': arrow.get('2025-04-21'), 'enddate': arrow.get('2022-11-01') },
        }


def ecdf(a, ax=None, add_zero=True, **kwargs):
    """Plot the Empirical Cumulative Density Function.
    
    parameters:
        a: The data of interest. Should be a list or a 1D numpy array.
        ax: The axes of the figure.
        add_zero: Set to True to connect the graph to y=0
        **kwargs: Any other option to pass to pylab.plot.
        
    Returns a dictionary providing the CDF value for each point on the x axis.
    """
    sorted=np.sort( a )
    yvals=np.arange(len(sorted)+1)/float(len(sorted))
    if add_zero:
        starti = 0
        sorted = np.append( sorted[0], sorted )
    else:
        starti=1
    if ax is None:
        plt.plot( sorted, yvals[starti:], **kwargs )
    else:
        ax.plot( sorted, yvals[starti:], **kwargs )

    return {k:v for k,v in zip(sorted, yvals)}


class BGPPlot():
    def __init__(self, bgpmonitors, roa_timings):
        
        self.bgpmonitors = bgpmonitors
        self.roa_timings = roa_timings
        self.peer_counts = defaultdict(lambda: defaultdict(int) )
        self.log_updates = defaultdict(list)
        self.log_updates_counts = defaultdict(Counter)
        self.log_long_updates = []
        self.log_long_updates_counts = defaultdict(Counter)

    def plot_timeline(self, upstream=False, all_asn=False):
        """Plot reachability and AS path breakdown as a function of time."""

        for collector, bm in self.bgpmonitors.items():

            for prefix, data in bm.log_data.items():
                print('plotting data for '+prefix)
                # Plot prefix reachability
                plt.figure(figsize=(20,4))
                plt.title('Reachability of '+prefix)
                plt.ylabel('# RIS Peers')
                plt.grid(visible=True, alpha=0.2)
                plt.xticks(rotation=45)
                if data['reachability']:
                    plt.ylim( [0, max(data['reachability'])+1])
                
                # Find index of start_date
                start_idx = min(i for i, ts in enumerate(data['time']) if not prefix in PREFIX_PROP 
                        or ts > PREFIX_PROP[prefix]['startdate']
                        or ts < PREFIX_PROP[prefix]['enddate']
                        )

                plt.step(data['time'][start_idx:], data['reachability'][start_idx:], where='post')

                # Add ROA creation/deletion timings
                for roa_log in self.roa_timings:
                    with open(roa_log, 'r') as log:
                        for line in log:
                            time, action, roa_prefix, asn, _ = line.split(',')

                            if prefix != roa_prefix:
                                continue

                            time = arrow.get(time)

                            if time > bm.starttime and time < bm.endtime and ( 
                                    not prefix in PREFIX_PROP 
                                    or time > PREFIX_PROP[prefix]['startdate']
                                    or time < PREFIX_PROP[prefix]['enddate']
                                    ):
                                plt.annotate(action, xy=(time.datetime, 0), xytext=(0, 75),
                                    textcoords="offset points", 
                                    ha='center', va='top',
                                    arrowprops={'arrowstyle':'->'}, 
                                # rotation=60, 
                                    fontsize=8
                                    )

                plt.tight_layout()
                plt.savefig(f'fig/{prefix.replace("/","_")}_{collector}.png')
                plt.close()


                # Plot upstream breakdown
                if upstream:
                    ## Find all possible upstreams
                    upstreams = set()
                    for datapoint in data['upstream']:
                        upstreams.update( datapoint.keys() )

                    # Sample data for all upstream
                    x = []
                    y = [[] for _ in upstreams]
                    for time_idx, datapoint in enumerate(data['upstream']):

                        if prefix in PREFIX_PROP and(
                                data['time'][time_idx] < PREFIX_PROP[prefix]['startdate']
                                or data['time'][time_idx] > PREFIX_PROP[prefix]['enddate']
                                ):
                            continue

                        ## x-axis
                        x.append(data['time'][time_idx])
                        # Make nice flat steps
                        if time_idx+1 < len(data['time']):
                            x.append(data['time'][time_idx+1])

                        ## y-axis
                        for up_idx, upstream in enumerate(upstreams):
                            y[up_idx].append(datapoint.get(upstream, 0))
                            # Make nice flat steps
                            if time_idx+1 < len(data['time']):
                                y[up_idx].append(datapoint.get(upstream, 0))

                    if len(x) > 3:
                        plt.figure(figsize=(8,3))
                        plt.title('Upstream of '+prefix)
                        plt.ylabel('# RIS Peers')
                        plt.grid(visible=True, alpha=0.2)
                        plt.xticks(rotation=45)
                        plt.stackplot(x, y, labels=upstreams)
                        plt.legend()
                        plt.tight_layout()
                        plt.savefig(f'fig/{prefix.replace("/","_")}_upstreams_{collector}.png')
                        plt.savefig(f'fig/{prefix.replace("/","_")}_upstreams_{collector}.pdf')
                        plt.close()

                # Plot all AS breakdown
                if all_asn:
                    ## Find all prominent asns
                    asns = set()
                    for datapoint in data['aspath']:
                        nb_peers = Counter()
                        for aspath in datapoint:
                            nb_peers.update(aspath)
                            
                        for asn, count in nb_peers.items():
                            if asn not in MY_ASNS and count > MIN_NB_PEERS:
                                asns.add( asn )

                    # Sample data for all as on the path
                    x = []
                    y = [[] for _ in asns]
                    for time_idx, datapoint in enumerate(data['aspath']):

                        if prefix in PREFIX_PROP and(
                                data['time'][time_idx] < PREFIX_PROP[prefix]['startdate']
                                or data['time'][time_idx] > PREFIX_PROP[prefix]['enddate']
                                ):
                            continue

                        ## x-axis
                        x.append(data['time'][time_idx])
                        # Make nice flat steps
                        if time_idx+1 < len(data['time']):
                            x.append(data['time'][time_idx+1])

                        ## y-axis
                        ### Count how many time ASNs appear in AS paths
                        nb_peers = Counter()
                        for aspath in datapoint:
                            nb_peers.update(aspath)
                            
                        ## Store as a step graph
                        for asn_idx, asn in enumerate(asns):
                            y[asn_idx].append(nb_peers.get(asn, 0))
                            # Make nice flat steps
                            if time_idx+1 < len(data['time']):
                                y[asn_idx].append(nb_peers.get(asn, 0))

                    if len(x) > 3 and len(y) > 2:
                        plt.figure(figsize=(8,3))
                        plt.title('ASNs in path to '+prefix)
                        plt.ylabel('# AS Paths')
                        plt.grid(visible=True, alpha=0.2)
                        plt.xticks(rotation=45)
                        plt.stackplot(x, y, labels=asns)
                        plt.legend()
                        plt.tight_layout()
                        plt.savefig(f'fig/{prefix.replace("/","_")}_aspath_{collector}.png')
                        plt.savefig(f'fig/{prefix.replace("/","_")}_aspath_{collector}.pdf')
                        plt.close()



    def plot_delay_dist(self):
        """Plot distibution of the different timings found in logs"""
        
        
        # all_delays[create/delete][peer|'all'][prefix]= [...]
        all_delays = {
                'create': defaultdict(lambda: defaultdict(list)),
                'delete': defaultdict(lambda: defaultdict(list))
        }

        for roa_log in self.roa_timings:

            # Retrieve the start/end timings for each ROA create and delete
            # binned_log[prefix][create][ [start, end], [start,end], ...]
            binned_log = defaultdict(lambda: {
                'create': [[]],
                'delete': [[]]
                })
            inverse_action = {'create': 'delete', 'delete': 'create'}

            with open(roa_log, 'r') as log:
                for line in log:
                    time_str, action, prefix, asn, _ = line.split(',')
                    timestamp = arrow.get(time_str, tzinfo='UTC')
                    prefix = prefix.lower()

                    binned_log[prefix][action].append([timestamp])
                    binned_log[prefix][inverse_action[action]][-1].append(timestamp)

            # timings[create|delete][prefix][peer] = [...]
            timings = {
                'create': defaultdict(lambda: defaultdict(list)),
                'delete': defaultdict(lambda: defaultdict(list))
                    } 

            for prefix, action_log in binned_log.items():
                for action, log in action_log.items():
                    for bin in log:
                        if len(bin) !=  2:
                            print('error ', action, bin)
                            continue

                        bin_start, bin_end = bin

                        # Check ARIN results after 5am
                        # if bin_start.hour < 5:
                            # continue

                        if prefix in PREFIX_PROP and (
                                bin_start < PREFIX_PROP[prefix]['startdate']
                                or bin_end > PREFIX_PROP[prefix]['enddate']
                                ):
                            continue

                        #print(action, bin_start, bin_end)
                        #if( bin_end - bin_start > datetime.timedelta(hours=MAX_DELAY_HOURS) ):
                        #    print(f'WARNING: Ignoring {action} starting on {bin_start} and ending on {bin_end}')
                        #    continue

                        for bm in self.bgpmonitors.values():
                            if( prefix not in bm.log_data
                                    or bin_end < bm.log_data[prefix]['time'][0]
                                    or bin_end > bm.log_data[prefix]['time'][-1]):
                                continue

                            start_idx = next(x for x, val in enumerate(bm.log_data[prefix]['time'])
                                                if val > bin_start)
                            end_idx = next(x for x, val in enumerate(bm.log_data[prefix]['time'])
                                                if val > bin_end)

                            bgp = {
                                'time': bm.log_data[prefix]['time'][start_idx-1:end_idx],
                                'aspath': bm.log_data[prefix]['aspath'][start_idx-1:end_idx],
                                }

                            peers_state = dict()
                            prev_peers = None
                            for bgp_time, aspaths in zip(bgp['time'], bgp['aspath']):
                                if prev_peers is None:
                                    prev_peers = set([path[0] for path in aspaths])
                                    continue

                                peers = set([path[0] for path in aspaths])
                                diff = prev_peers.symmetric_difference(peers) 

                                for updated_peer in diff:
                                    # ignore flapping
                                    if (
                                        (action == 'create' and updated_peer in prev_peers and updated_peer not in peers)
                                        or 
                                        (action == 'delete' and updated_peer not in prev_peers and updated_peer in peers)
                                        ):
                                        continue

                                    if updated_peer not in peers_state:
                                        delay = bgp_time - bin_start
                                        peers_state[updated_peer] = delay
                                        delay_min = delay.total_seconds()/60
                                        # we don't want to interfer with next day
                                        # measurement
                                        if delay_min < MAX_DELAY_HOURS*60/2:
                                            timings[action][prefix][updated_peer].append(delay_min)
                                            self.peer_counts[updated_peer][action+'_ok'] += 1
                                            updated_peer_path = [path for path in aspaths if path[0] == updated_peer]

                                            self.log_updates[updated_peer].append(
                                                ( 
                                                    action,
                                                    updated_peer,
                                                    prefix,
                                                    bin_start,
                                                    bgp_time,
                                                    delay_min,
                                                    updated_peer_path
                                                ) 
                                            )
                                            self.log_updates_counts[action+'_peer'].update([updated_peer])

                                            # log worst cases
                                            if ( delay_min > 100 
                                                and prefix in PREFIX_PROP
                                                and not PREFIX_PROP[prefix]['label'][:4] in ['ARIN', 'LACN']):

                                                self.log_long_updates.append(
                                                    ( 
                                                        action,
                                                        updated_peer,
                                                        prefix,
                                                        bin_start,
                                                        bgp_time,
                                                        delay_min,
                                                        updated_peer_path
                                                    ) 
                                                )
                                                self.log_long_updates_counts[action+'_peer'].update([updated_peer])

                                        else:
                                            self.peer_counts[updated_peer][action+'_missed'] += 1

                                        if( delay_min > 100 and action == 'create' 
                                                and prefix in PREFIX_PROP
                                                and not PREFIX_PROP[prefix]['label'][:4] in ['ARIN', 'LACN']):
                                            print(updated_peer, PREFIX_PROP[prefix]['label'], delay_min, bin_start, bgp_time)


                                prev_peers = peers


            for action, prefix_data in timings.items():
                for prefix, peer_data in prefix_data.items():
                    #print(action, prefix)
                    for peer, data in peer_data.items():
                        all_delays[action][peer][prefix].extend(data)
                        all_delays[action]['all'][prefix].extend(data)


        # Plot all distributions
        os.makedirs('fig/distributions/', exist_ok=True)

        stats = ujson.load(open('../summary_stats.json'))

        for action, peer_data in all_delays.items():
            for peer, prefix_data in peer_data.items():

                if action == 'create':
                    asn_file.write(f"{peer}\n")

                plt.figure()

                max_value = 0
                for prefix, data in prefix_data.items():

                    if prefix.lower() in PREFIX_PROP:
                        props = PREFIX_PROP[prefix.lower()]
                    else:
                        continue

                    if peer == 'all':
                        if props['label'] not in stats[action]:
                            stats[action][props['label']] = {}
                        stats[action][props['label']]['BGP'] = np.median(data)
                        print(f'{action} median for {props["label"]}: {np.median(data):.0f}')
                    else:
                        with open(f'fig/distributions/AS{peer}_median.txt', 'a') as fp:
                            fp.write(f'{action} {props["label"]} median = {np.median(data):.0f}\n')

                    ecdf(data, label=props['label'], color=props['color'], 
                            linestyle=props['linestyle'])
                    max_value = np.max([max_value, np.max(data)])

                peer_label = 'AS'+peer
                if peer == 'all':
                    peer_label = 'All peers'

                action_label = ''
                if action == 'create':
                    action_label = 'User query to BGP update delay'
                elif action == 'delete':
                    action_label = 'User query to BGP withdraw delay'

                plt.grid(visible=True, which='major', alpha=0.35)
                plt.grid(visible=True, which='minor', linestyle='--', alpha=0.25)
                plt.title(f'{action_label} - {peer_label}')
                plt.xlabel('Delay (minutes)')
                plt.ylabel('CDF')
                plt.legend()
                if max_value > 200:
                    plt.xscale('log')
                    plt.xlim([1, 800])
                    plt.savefig(f'fig/distributions/{action}_{peer}_log.pdf')
                    pickle.dump(plt.gcf(), open(f'fig/distributions/{action}_{peer}_log.pickle', 'wb')) 

                plt.xscale('linear')
                plt.xlim([0, 60])
                plt.savefig(f'fig/distributions/{action}_{peer}.pdf')
                pickle.dump(plt.gcf(), open(f'fig/distributions/{action}_{peer}.pickle', 'wb')) 

                plt.close()
                
        ujson.dump(stats, open('../summary_stats.json', 'w'))
                                    

        ## Plot Tier1 together
        peer_color = []
        for action, peer_data in all_delays.items():

            plt.figure()

            for peer, prefix_data in peer_data.items():

                # tier1 clique: 174 209 286 701 1239 1299 2828 2914 3257 3320 3356 3491 5511 6453 6461 6762 6830 7018 12956

                if peer not in ['174', '209', '286', '701', '1239', '1299', '2828',
                        '2914', '3257', '3356', '3491', '5511', '6453', '6461',
                        '6830', '7018', '12956']:
                    continue

                if peer not in peer_color:
                    peer_color.append(peer)

                if action == 'create':
                    asn_file.write(f"{peer}\n")


                peer_data = []
                for prefix, data in prefix_data.items():

                    if prefix.lower() in PREFIX_PROP:
                        props = PREFIX_PROP[prefix.lower()]
                    else:
                        continue

                    peer_data.extend(data)

                if peer_data:
                    ecdf(peer_data, label=f'AS{peer}', color=f'C{peer_color.index(peer)}')

                    action_label = ''
                    if action == 'create':
                        action_label = 'User query to BGP update delay - Tier1'
                    elif action == 'delete':
                        action_label = 'User query to BGP withdraw delay - Tier1'

                    plt.grid(visible=True, which='major', alpha=0.35)
                    plt.grid(visible=True, which='minor', linestyle='--', alpha=0.25)
                    plt.title( action_label )
                    plt.xlabel('Delay (minutes)')
                    plt.ylabel('CDF')
                    plt.legend()
                    plt.xlim([0, 60])
                    plt.savefig(f'fig/distributions/{action}_tier1.pdf')
                    pickle.dump(plt.gcf(), open(f'fig/distributions/{action}_tier1.pickle', 'wb')) 

            plt.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
            description="Plot timeseries and distributions of prefixes reachability and ROA delay.")

    parser.add_argument('--roa_timings', nargs='+',
            help='CSV files containing ROAs creation and deletion times.',
            default=['../apnic/roa_timings.csv','../ripe/roa_timings.csv',
        '../afrinic/roa_timings.csv', '../arin/roa_timings.csv', 
        '../lacnic/roa_timings.csv'])
    parser.add_argument('bgp_timings', nargs='+',
            help='Pickle files containing BGP timings for monitored prefixes.')

    args = parser.parse_args()

    # Loading pickle files
    bgpmonitors = {}
    for bm_fname in args.bgp_timings:
        with open(bm_fname, 'rb') as fp:
            collector = bm_fname.rpartition('_')[2].partition('.')[0]
            bgpmonitors[collector] = pickle.load(fp)

    bplot = BGPPlot( bgpmonitors, args.roa_timings )
    bplot.plot_delay_dist()
    #bplot.plot_timeline()

    # Save stats to files
    ujson.dump(bplot.peer_counts, open('peer_counts.json', 'w'))

    with open('log_long_updates.csv', 'w') as fp:
        for update in bplot.log_long_updates:
            fp.write(','.join([str(u) for u in update])+'\n')

    with open('log_long_updates_counts.txt', 'w') as fp:
        for label, counter in bplot.log_long_updates_counts.items():
            fp.write(f'# Top 10 {label}\n')
            for peer, count in counter.most_common():
                fp.write(f'\t{peer}\t{count}\n')

    for peer, updates in bplot.log_updates.items():
        with open(f'log/{peer}_updates.csv', 'w') as fp:
            for update in updates:
                fp.write(','.join([str(u) for u in update])+'\n')


    with open('log_updates_counts.txt', 'w') as fp:
        for label, counter in bplot.log_long_updates_counts.items():
            fp.write(f'# Top 10 {label}\n')
            for peer, count in counter.most_common():
                fp.write(f'\t{peer}\t{count}\n')



import argparse
import arrow
import ujson
import numpy as np
from collections import defaultdict
from matplotlib import pylab as plt
import os
import glob

MAX_DELAY_HOURS = 24 # ROA wiggling should be less than 24h
MAX_OUT_OF_SYNC = 60 # allow x seconds out-of-sync between user and RIR timestamps
                     # i.e. the RIR signing timestamp may be X sec. before
                     # the user's query timestamp

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


PREFIX_PROP_FIX = {
        "103.171.219.0/24": {'label': "APNICv4", 'color': 'C0', 'linestyle': '-', 
            'startdate': arrow.get('2025-11-01'), 'enddate': arrow.get('2022-11-01') },
        "2001:df7:5381::/48": {'label': "APNICv6", 'color': 'C0', 'linestyle': '--', 
            'startdate': arrow.get('2025-11-01'), 'enddate': arrow.get('2022-11-01') },
        "151.216.5.0/24": {'label': "RIPEv4", 'color': 'C2', 'linestyle': '-', 
            'startdate': arrow.get('2025-11-01'), 'enddate': arrow.get('2022-11-01') }, 
        "2001:7fc:3::/48":{'label': "RIPEv6", 'color': 'C2', 'linestyle': '--',
            'startdate': arrow.get('2025-11-01'), 'enddate': arrow.get('2022-11-01') },
        "102.218.97.0/24":{'label': "AFRINICv4", 'color': 'C1', 'linestyle': '-',
            'startdate': arrow.get('2025-11-01'), 'enddate': arrow.get('2022-11-01') },
        "2001:43f8:df1::/48":{'label': "AFRINICv6", 'color': 'C1', 'linestyle': '--', 
            'startdate': arrow.get('2025-11-01'), 'enddate': arrow.get('2022-11-01') },
        "165.140.105.0/24": {'label': "ARINv4", 'color': 'C9', 'linestyle': '-',
            'startdate': arrow.get('2022-04-21'), 'enddate': arrow.get('2023-04-21')},
        "2620:9e:6001::/48": {'label': "ARINv6", 'color': 'C9', 'linestyle': '--', 
            'startdate': arrow.get('2022-04-21'), 'enddate': arrow.get('2023-04-21')},
        "201.219.253.0/24": {'label': "LACNICv4", 'color': 'C3', 'linestyle': '-',
            'startdate': arrow.get('2025-02-01'), 'enddate': arrow.get('2022-11-01') },
        "2801:1e:1801::/48": {'label': "LACNICv6", 'color': 'C3', 'linestyle': '--',
            'startdate': arrow.get('2025-02-01'), 'enddate': arrow.get('2022-11-01') },
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


class RIRPlot():
    def __init__(self, pub_timings, userquery_timings ):
        
        self.pub_timings = pub_timings
        self.prefix = pub_timings.rpartition('.')[0]
        self.userquery_timings = userquery_timings

        # load publication times
        self.pub_log = defaultdict(list)
        csv = open(self.pub_timings, 'r')
        for line in csv.readlines():
            prefix, timestamp, action = line.strip().split(',')

            if prefix.lower() not in PREFIX_PROP:
                continue

            self.pub_log[prefix].append( 
                        {
                        'time':arrow.get(timestamp, tzinfo='UTC'),
                        'action': action
                        }
                    ) 

        # Sort RIR timestamps
        for prefix in self.pub_log.keys():
            self.pub_log[prefix] = sorted(self.pub_log[prefix], key=lambda x: x['time'])


    def plot_delay_dist(self):
        """Plot distibution of delay between user query and signing times"""
        
        
        # all_delays[create/delete][peer|'all'][prefix]= [...]
        all_delays = {
                'create': defaultdict(list),
                'delete': defaultdict(list)
        }

        for userquery_log in self.userquery_timings:

            # Retrieve the start/end timings for each ROA create and delete
            # binned_log[prefix][create][ [start, end], [start,end], ...]
            binned_log = defaultdict(lambda: {
                'create': [[]],
                'delete': [[]]
                })
            inverse_action = {'create': 'delete', 'delete': 'create'}

            with open(userquery_log, 'r') as log:
                for line in log:
                    time_str, action, prefix, asn, _ = line.split(',')
                    timestamp = arrow.get(time_str, tzinfo='UTC')
                    prefix = prefix.lower()

                    binned_log[prefix][action].append([timestamp])

                    # Make sure we don't make bin longer than MAX_DELAY_HOURS
                    if len(binned_log[prefix][inverse_action[action]][-1]) == 0:
                        binned_log[prefix][inverse_action[action]][-1].append(timestamp)
                    elif (timestamp-binned_log[prefix][inverse_action[action]][-1][0]).seconds < MAX_DELAY_HOURS*60*60:
                        binned_log[prefix][inverse_action[action]][-1].append(timestamp)
                    else:
                        binned_log[prefix][inverse_action[action]].append([timestamp])


            for prefix, action_log in binned_log.items():
                for action, log in action_log.items():
                    for bin in log:
                        if len(bin) !=  2:
                            #print('error ', action, bin)
                            continue

                        bin_start, bin_end = bin

                        # Check ARIN behavior after 5am
                        #if bin_start.hour < 5:
                        #    continue

                        if( prefix.lower() not in PREFIX_PROP
                            or bin_start > PREFIX_PROP[prefix.lower()]['enddate'] 
                            or bin_start < PREFIX_PROP[prefix.lower()]['startdate'] ):
                            continue

                        if( prefix not in self.pub_log
                                or bin_end < self.pub_log[prefix][0]['time']
                                or bin_end > self.pub_log[prefix][-1]['time']):
                            continue

                        rir_idx, rir_start = next((i, val) for i, val in enumerate(self.pub_log[prefix])
                                            if val['time'] > bin_start.shift(seconds=-MAX_OUT_OF_SYNC))

                        if( (action == 'create' and rir_start['action'] == 'sign')
                                or (action == 'delete' and rir_start['action'] == 'revoke') 
                                or True
                                ):
                            delay = rir_start['time'] - bin_start
                            delay_min = delay.total_seconds()/60

                            # we don't want to interfer with next day
                            # measurement
                            if delay_min < MAX_DELAY_HOURS*60/2:
                                if delay_min > 30 and action == 'create'  and PREFIX_PROP[prefix]['label'].startswith('APNIC'):

                                    print( '##### ', bin_start, rir_start, action, 
                                            prefix, PREFIX_PROP[prefix]['label'])

                                all_delays[action][prefix].append( delay_min )

                                # Remove the timestamp from RIR log to make sure we 
                                # don't use it twice (may happen with RIPE and APNIC)
                                #self.rir_log[prefix].pop(rir_idx)

        # Plot all distributions
        os.makedirs('fig/distributions/', exist_ok=True)

        stats = ujson.load(open('../summary_stats.json'))
        metric = 'Unk'
        if 'pub' in self.pub_timings:
            metric = 'Pub.'
        elif 'rp' in self.pub_timings:
            metric = 'RP'
        elif 'sign' in self.pub_timings:
            metric = 'CA'

        for action, prefix_data in all_delays.items():
            plt.figure()

            max_value = 0
            for prefix, data in prefix_data.items():

                if prefix.lower() in PREFIX_PROP:
                    props = PREFIX_PROP[prefix.lower()]
                else:
                    continue

                stats[action][props['label']][metric] = np.median(data)
                print(f'{action} median for {props["label"]}: {np.median(data):.0f}')

                ecdf(data, label=props['label'], color=props['color'], 
                        linestyle=props['linestyle'])
                max_value = np.max([max_value, np.max(data)])

            action_label = ''
            if action == 'create':
                action_label = 'User query to ROA publication delay (creation)'
            elif action == 'delete':
                action_label = 'User query to ROA publication delay (revocation)'

            plt.grid(visible=True, which='major', alpha=0.35)
            plt.grid(visible=True, which='minor', linestyle='--', alpha=0.25)
            plt.title(f'{action_label}')
            plt.xlabel('Delay (minutes)')
            plt.ylabel('CDF')
            plt.legend()
            if max_value > 200:
                plt.xscale('log')
                plt.savefig(f'fig/distributions/{self.prefix}_{action}_log.pdf')
                #plt.savefig(f'fig/distributions/{action}_log.png')

                plt.xscale('linear')
                plt.xlim([-5, 300])
                plt.savefig(f'fig/distributions{self.prefix}_{action}.pdf')
                #plt.savefig(f'fig/distributions/{action}.png')
            else:
                plt.xlim([0, 300])
                plt.savefig(f'fig/distributions/{self.prefix}_{action}.pdf')
                #plt.savefig(f'fig/distributions/{action}.png')

            plt.close()
                
        ujson.dump(stats, open('../summary_stats.json', 'w'))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
            description="Plot distributions of ROA publication delay.")

    parser.add_argument('--roa_timings', nargs='+',
            help='CSV files containing users creation and deletion query times.',
            default=['../apnic/roa_timings.csv','../ripe/roa_timings.csv',
        '../afrinic/roa_timings.csv', '../arin/roa_timings.csv',
        '../lacnic/roa_timings.csv'])
    parser.add_argument('pub_timings', 
            help='Files containing publication times for monitored prefixes.')

    args = parser.parse_args()

    bplot = RIRPlot( args.pub_timings, args.roa_timings )
    bplot.plot_delay_dist()

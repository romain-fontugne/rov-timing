# ROA Propagation time extraction

## Purpose
The purpose of this project extract the propagation time of ROA (Route Origin Authorization) objects into BGP.

On the Internet, networks announce their prefixes (IP address ranges) to other networks through the BGP protocol. However, based on an external database called RPKI containing ROAs, those announcements can be tagged as valid, invalid or not-found. Whenever the announcement of a prefix is tagged as invalid, networks receiving those announcements will drop these prefixes if they are performing Route Origin Validation (ROV). The aim is to capture the BGP propagation time following changes in the RPKI using historical information.

## Dataset
Dataset 1: We start with getting a list of prefixes from RIB (Routing Information Base) files from [RouteViews](http://archive.routeviews.org/)
Format: Compressed binary format (.bz2)
Numbers of rows : 13914909
```
>>> import pandas as pd
>>> df = pd.read_csv('route-views3-rib.20180501.0000.csv', sep='|')
>>> df.shape
(13914909, 15)
```

Dataset 2: We then need to validate the prefixes against information found in [RPKI](http://ftp.ripe.net/rpki)
Format: csv
```
root@aaee69ee5086:/home/workspace# wc -l /root/.cache/rov/db/rpki//2022/4/17/*
    4646 /root/.cache/rov/db/rpki//2022/4/17/afrinic.csv
   89706 /root/.cache/rov/db/rpki//2022/4/17/apnic.csv
   54368 /root/.cache/rov/db/rpki//2022/4/17/arin.csv
   21819 /root/.cache/rov/db/rpki//2022/4/17/lacnic.csv
  157326 /root/.cache/rov/db/rpki//2022/4/17/ripencc.csv
  327865 total
```

The csv files are loaded into a `radix` tree to enable fast-lookup of a prefix. The radix tree is commonly used for routing table lookups. It efficiently stores network prefixes of varying lengths and allows fast lookups of containing networks.

Dataset 3: We then need to extract which ROAs made the prefixes in (1) **Invalid**, for this we used the information in the radix tree to validate the prefix-origin pair.

Dataset 4: We then extract the time at which a "Withdraw" message was found in BGP. For this we used [PyBGPStream](https://bgpstream.caida.org/docs/install/pybgpstream)
Format: API

```
    stream = pybgpstream.BGPStream(
        from_time=starttime, until_time=t2.isoformat(),
        collectors=["rrc00","rrc14"],
        record_type="updates",
        filter="prefix " + prefix
    )
```

## Output
Our final output is a csv file containing the following information "prefix", "tal", "peer_ip", "roa_create_time", "withdrawal_time", "delta".
We are mainly interested in the "delta" value i.e. the ROA propagation time.
```
df = pd.read_csv('data/results.csv', header='infer', dtype={'delta':np.int32}, parse_dates=['roa_create_time','withdrawal_time'], skip_blank_lines=True)
df['delta_min'] = df.delta/60
df.head()
```


## Data Analysis
We then analyse the results first by creating a box plot to understand the distribution (min, max and median) values for each category (RIR).
This is achieved by running:
```
fig, ax = plt.subplots(figsize=(10, 6))
df.boxplot(by ='tal', column =['delta_min'], grid = False, ax=ax)

ax.set_xlabel("RIR")
ax.set_ylabel("Withdrawal time (minutes)")
ax.grid(True)

plt.show()
```
    
## Project Structure
- **data** folder nested at the home of the project, where all needed data reside.
- **rib.py** the code used to download a RIB file
- **rov.py** the code used to validate prefixes in the RIB file
- **roa.py** the code used to extract ROAs from the API for a given prefix
- **bgp.py** the code used to check for withdrawal messages on the global routing table
- **etl.py** the code to automate the ETL process
- **README.md** current file, provides description of the project.
    
# Build Instructions
Run `bash install.sh`

# Run Instructions
Run `python etl.py`

# Setup Instructions
To automate the process, a cronjob can be setup to collect the data on a regular basis (e.g. monthly)

# Propose how often the data should be updated and why.
Here, we are interested in collecting once a month. For this we will setup a cronjob accordingly.
`0 0 1 * * python etl.py`

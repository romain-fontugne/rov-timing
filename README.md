# RPKI Time-of-Flight: Tracking Delays in the Management, Control, and Data Planes

See the complete report here: [Fontugne et al. PAM'23](https://www.iijlab.net/en/en/members/romain/pdf/romain_pam23.pdf)

## Summary

Route Origin Validation (ROV) has recently received more attention from network
operators. Overall ROV is a fairly complex process that involves, RPKI data from
the five RIRs, open source software for fetching and validating data, and the
various router software that implement the actual route origin validation
functionality.  This is currently in deployment on the Internet but many
questions are left unanswered about the interactions of the different pieces
involved in the ROV process.

One wonders how long it takes for the effect of RPKI changes to appear in the data plane.
Does an operator that adds, fixes, or removes a Route Origin Authoriza-
tion (ROA) have time to brew coffee or rather enjoy a long meal before
the Internet routing infrastructure integrates the new information and
the operator can assess the changes and resume work? The chain of
ROA publication, from creation at Certification Authorities all the way
to the routers and the effect on the data plane involves a large number
of players, is not instantaneous, and is often dominated by ad hoc ad-
ministrative decisions. 

This is the first comprehensive study to measure
the entire ecosystem of ROA manipulation by all five Regional Internet
Registries (RIRs), propagation on the management plane to Relying Par-
ties (RPs) and to routers; measure the effect on BGP as seen by global
control plane monitors; and finally, measure the effects on data plane
latency and reachability. We found that RIRs usually publish new RPKI
information within five minutes, except APNIC which averages ten min-
utes slower. At least one national CA is said to publish daily. We observe
significant disparities in ISPs’ reaction time to new RPKI information,
ranging from a few minutes to one hour. The delay for ROA deletion
is significantly longer than for ROA creation as RPs and BGP strive
to maintain reachability. Incidentally, we found and reported significant
issues in the management plane of two RIRs and a Tier1 network.


## Experiments
We deploy experimental prefixes on the Internet
and measure the management plane latency from ROA creation and subsequent
publication by the RIRs to receipt by the routers, and then the resulting effects
on the BGP control plane using RIPE RIS data. We also measure some of the
results on the data plane using RIPE Atlas traceroutes; showing topological
effects of ROAs, BGP path hunting, and latency shifts.

### First experiment

To better understand the challenges affecting ROA propagation and the impact on BGP, and to have a global understanding, we generate ROAs for multiple prefixes at the different RIRs.
The following experimental resources have been obtained from the five RIRs:

| RIR | type | IPv4 | IPv6 | 
|-----|------|------|------|
| AFRINIC | control | 102.218.96.0/24 | 2001:43f8:df0::/48 |
| AFRINIC | test | 102.218.97.0/24 | 2001:43f8:df1::/48 |
| APNIC | control | 103.171.218.0/24 | 2001:DF7:5380::/48 |
| APNIC | test | 103.171.219.0/24 | 2001:DF7:5381::/48 |
| ARIN | control | 165.140.104.0/24 | 2620:9E:6000::/48 |
| ARIN | test | 165.140.105.0/24 | 2620:9E:6001::/48 |
| LACNIC | control | 201.219.252.0/24 | 2801:1e:1800::/48 |
| LACNIC | test | 201.219.253.0/24 | 2801:1e:1801::/48 |
| RIPE | control | 151.216.4.0/24 | 2001:7fc:2::/48 |
| RIPE | test | 151.216.5.0/24 | 2001:7fc:3::/48 |

The control prefixes are expected to be always reachable, with an always valid RPKI
status. For the test prefixes, the BGP announcements do not change,
but we periodically add and remove a ROA to alternatively validate and invalidate the origin AS of the test prefixes’ in BGP.
These resources have be announced by an AS number used for research purposes (AS3970).

### Second experiment

For the second experiment (§5.1), we used three /24 prefixes from 151.216.32.0/21 and announced them from three diverse
networks, including an IXP and a national ISP with 149 peer ASes. The three
prefixes are used as test prefixes, meaning that we daily alternate the ROA status
for all of them. 

## Data

The above experiments have been monitored in the management (RPKI), control (BGP), and data (traceroute) planes.

The time of our ROA creation/deletion requests to RIRs is available here: TODO

The BGP data is available in [RIPE RIS](https://www.ripe.net/analyse/internet-measurements/routing-information-service-ris) and [Routeviews](https://www.routeviews.org/).

For the data plane, we performed traceroutes every 15 minutes from RIPE Atlas with probes
in 6 different ASes. The data is available via Atlas's API:

| Atlas measurement ID | target | RIR | type |
|----|--------|-----|------|
[40388150](https://atlas.ripe.net/api/v2/measurements/40388150/results/)| 103.171.218.1 | APNIC | control |
[40388151](https://atlas.ripe.net/api/v2/measurements/40388151/results/)| 103.171.219.1 | APNIC | test |
[40388152](https://atlas.ripe.net/api/v2/measurements/40388152/results/)| 2001:DF7:5380::1 | APNIC | control |
[40388153](https://atlas.ripe.net/api/v2/measurements/40388153/results/)| 2001:DF7:5381::1 | APNIC | test |
[40388154](https://atlas.ripe.net/api/v2/measurements/40388154/results/)| 151.216.4.1 | RIPE | control |
[40388155](https://atlas.ripe.net/api/v2/measurements/40388155/results/)| 151.216.5.1 | RIPE | test |
[40388156](https://atlas.ripe.net/api/v2/measurements/40388156/results/)| 2001:7fc:2::1 | RIPE | control |
[40388157](https://atlas.ripe.net/api/v2/measurements/40388157/results/)| 2001:7fc:3::1 | RIPE | test |
[40388158](https://atlas.ripe.net/api/v2/measurements/40388158/results/)| 102.218.96.1 | AFRINIC | control |
[40388159](https://atlas.ripe.net/api/v2/measurements/40388159/results/)| 102.218.97.1 | AFRINIC | test |
[40388160](https://atlas.ripe.net/api/v2/measurements/40388160/results/)| 2001:43f8:df0::1 | AFRINIC | control |
[40388161](https://atlas.ripe.net/api/v2/measurements/40388161/results/)| 2001:43f8:df1::1 | AFRINIC | test |
[40388162](https://atlas.ripe.net/api/v2/measurements/40388162/results/)| 165.140.104.1 | ARIN | control |
[40388163](https://atlas.ripe.net/api/v2/measurements/40388163/results/)| 165.140.105.1 | ARIN | test |
[40388164](https://atlas.ripe.net/api/v2/measurements/40388164/results/)| 2620:9E:6000::1 | ARIN | control |
[40388165](https://atlas.ripe.net/api/v2/measurements/40388165/results/)| 2620:9E:6001::1 | ARIN | test |
[40388166](https://atlas.ripe.net/api/v2/measurements/40388166/results/)| 201.219.252.1 | LACNIC | control |
[40388167](https://atlas.ripe.net/api/v2/measurements/40388167/results/)| 201.219.253.1 | LACNIC | test |
[40388168](https://atlas.ripe.net/api/v2/measurements/40388168/results/)| 2801:1e:1800::1 | LACNIC | control |
[40388169](https://atlas.ripe.net/api/v2/measurements/40388169/results/)| 2801:1e:1801::1 | LACNIC | test |


## Source code
The source code used for these experiments is available at: TODO

## Inquiries
For any inquiries please contact: romain@iij.ad.jp, pelsser@unistra.fr, & randy@psg.com

## Further reading
- Fontugne et al. PAM'23 - https://www.iijlab.net/en/en/members/romain/pdf/romain_pam23.pdf
- Geoff Huston, HKNOG - https://www.potaroo.net/presentations/2020-09-25-rpki-hknog.pdf
- draft-ietf-sidrops-rpki-rov-timing-04: https://datatracker.ietf.org/doc/html/draft-ietf-sidrops-rpki-rov-timing-03.txt
- Kistoff et al. IMC'20 - https://archive.psg.com/201029.imc-rp.pdf


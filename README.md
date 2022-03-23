# rov-timing

## Route Origin Validation 

Route Origin Validation (ROV) has recently received more attention from network
operators. Overall ROV is a fairly complex process that involves, RPKI data from
the five RIRs, open source software for fetching and validating data, and the
various router software that implement the actual route origin validation
functionality.  This is currently in deployment on the Internet but many
questions are left unanswered about the interactions of the different pieces
involved in the ROV process.

## Experiments

### First

To better understand the challenges affecting ROA propagation and the impact on BGP, and to have a global understanding, we need to generate ROAs for multiple prefixes at the different RIRs.

The following experimental resources will be required from each RIR:
- Two /24 IPv4
- Two /48 IPv6

These resources will be announced in BGP by AS numbers used for research purposes. There will be no end-hosts on the prefixes. Ingress and egress traffic towards and from the underlying network will be blackholed.

We will be collecting metrics from both RPKI repositories and BGP, as detailed in here: https://datatracker.ietf.org/doc/html/draft-ietf-sidrops-rpki-rov-timing-03.txt.

We will need access to the RIR portal or API to create ROAs for the assigned prefixes.

### Second

To compare the control and data planes during ROV flux, a selection of /24s will be announced by various providers.  Traceroutes from Atlas will be recorded while ROAs are fluxed at the NCC.

The following experimental resources from the NCC will be used:
- Eight /24s IPv4 from 151.216.32.0/21
- Eight /48s IPv6

Frome these prefixes, we will generate between 100 Kpps and 200 Kpps traffic using FlashRoute (https://github.com/lambdahuang/FlashRoute).

## Results
Results from our experiments will be publicly available at https://github.com/romain-fontugne/rov-timing.  And, of course, we hope the resulting paper(s) will be accepted at significant venues.

## Inquiries
For any inquiries please contact: romain@iij.ad.jp, pelsser@unistra.fr, & randy@psg.com

## References
- Geoff Huston, HKNOG - https://www.potaroo.net/presentations/2020-09-25-rpki-hknog.pdf
- draft-ietf-sidrops-rpki-rov-timing-04: https://datatracker.ietf.org/doc/html/draft-ietf-sidrops-rpki-rov-timing-03.txt
- Kistoff et al. IMC'20 - https://archive.psg.com/201029.imc-rp.pdf


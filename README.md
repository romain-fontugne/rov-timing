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
To better understand ROA propagation and how BGP may be affected, we are creating frequent ROAs and BGP announcements for the following prefixes:
- `list of prefixes and period of time   TBD`


Results from our experiments will be publicly available at https://github.com/romain-fontugne/rov-timing.

## Inquiries
For any inquiries please contact: romain@psg.com

## References
- Geoff Huston, HKNOG - https://www.potaroo.net/presentations/2020-09-25-rpki-hknog.pdf
- draft-ietf-sidrops-rpki-rov-timing-04: https://datatracker.ietf.org/doc/html/draft-ietf-sidrops-rpki-rov-timing-03.txt
- Kistoff et al. IM - https://archive.psg.com/201029.imc-rp.pdf


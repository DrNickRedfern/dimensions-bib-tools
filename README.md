# dimensions-bib-tools
Tools for analysing bibliometric data from the Dimensions database

## Co-citation percentile rank
The file `co_citation_percentile_rank.py` estimates the percentile rank of a target publication among its co-citation cohort, applying the method described in 

> Seppänen, JT., Värri, H. & Ylönen, I. (2022) Co-citation Percentile Rank and JYUcite: a new network-standardized output-level citation influence metric and its implementation using Dimensions API. *Scientometrics* 127: 3523–3541. [https://doi.org/10.1007/s11192-022-04393-8](https://doi.org/10.1007/s11192-022-04393-8).

This requires access to the Dimensions API, and is limited by the number of requests you can make in a query based on your Dimensions subscription.

The results are comparable (albeit slightly different) to the results produced by the [JYUcite online calculator](https://oscsolutions.cc.jyu.fi/jyucite/about/), which does not require a Dimensions subscription but is limited to 50 DOIs per day.

## Feet of Clay
The file `feet_of_clay.py` gets the data for publications from an institution in a given year and checks to see if

- any of those publications are listed in the Retraction Watch/Crossref database
- any of the research cited by those publications are listed in the Retraction Watch/Crossref database

This script may require modification if an institution has lots of publications that cite a very large number of works. In that case it would be better to reduce the number of publications you want to check or use Google Big Query to access Dimensions.

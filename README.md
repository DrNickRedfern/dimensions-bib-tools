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

This script will potentially produce three outputs:

- A csv file containing a list of all the publications that appear in the Retraction Watch/Crossref database, i.e. outputs that have been retracted.
- A csv file containing identifiers for publications cited by outputs from an institution - this reduces the need to repeatedly requets the same information from the Dimensions API (published outputs will not start citing new sources) while making it possible to check if any of the cited publications have been retracted at a later date.
- A csv file listing which outputs from an institution cite publications in the Retraction Watch/Crossref database.

## Talent Program Checker

The file `talent_program_checker.py` checks whether a any Chinese talent programs are listed in the funding section of a publication in the Dimensions database.

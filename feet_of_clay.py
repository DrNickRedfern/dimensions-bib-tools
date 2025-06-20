import dimcli
from dotenv import load_dotenv
import numpy as np
import pandas as pd

import json
import os
import sys

load_dotenv()

# Set search paramters
# Crossref asks you to be polite by providing an email when making API requests
EMAIL: str = os.getenv('EMAIL')
GRIDID: str = 'grid.6268.a'
YEAR: int = 2024

# Housekeeping
HOME_DIR: str = os.getcwd()
DATA_DIR: str = os.path.join(HOME_DIR, 'data')
if not os.path.isdir(DATA_DIR):
    os.mkdir(DATA_DIR)
    print('Created folder : ', DATA_DIR)
else:
    print('Data folder already exists.')

# Log into Dimensions API
API_KEY = os.getenv('API_KEY')
dimcli.login(key=API_KEY, endpoint='https://app.dimensions.ai/api/dsl/v2')
dsl = dimcli.Dsl()

# Get the data for all publications from an institution published in a given year
results = dsl.query_iterative(f"""search publications where research_orgs = "{GRIDID}"
                                    and year = "{YEAR}"
                                    return publications[id+doi+date+authors+title+source_title+publisher+reference_ids]"""
                                    )

df_publications = results.as_dataframe()
df_publications = (
    df_publications
    .rename(columns={'id': 'pub_id', 'source_title.title': 'source_title'})
    .filter(['pub_id', 'doi', 'date', 'publisher', 'title', 'source_title', 'reference_ids'])
)

df_affiliations = results.as_dataframe_authors_affiliations()
df_affiliations = (
    df_affiliations
    .assign(full_name = lambda df: df[['first_name', 'last_name']].apply(' '.join, axis=1))
    .filter(['pub_id', 'aff_id', 'aff_name', 'aff_raw_affiliation', 'researcher_id', 'full_name'])
)
df_affiliations = df_affiliations[df_affiliations['aff_id'] == GRIDID]

# Access the Retraction Watch/Crossref database
'''
This is best done via the URL to ensure the database is up to date, but you could
download the file to the current working directory and load it as a csv file using 

retractions = pd.read_csv('retractions.csv', encoding='ISO-8859-1')

You MUST make sure the encoding variable is set or Pandas will report an error
'''
url = 'https://api.labs.crossref.org/data/retractionwatch?' + EMAIL
retractions = pd.read_csv(url, encoding='ISO-8859-1')

retractions.columns = (
    retractions.columns
    .str.replace('(?<=[a-z])(?=[A-Z])', '_', regex=True)
    .str.replace(' ', '_')
    .str.lower()
)

retractions = retractions.drop(columns=['retraction_pub_med_id', 'unnamed:_20', 'notes', 'paywalled', 
                                        'original_paper_pub_med_id', 'urls', 'article_type', 'country',
                                        'publisher', 'journal', 'subject', 'institution', 'author',
                                        'original_paper_date', 'title'])

retractions = (
    retractions
    .assign(retraction_date = lambda df: df['retraction_date'].str.split(' ').str[0])
)
retractions['retraction_date'] = pd.to_datetime(retractions['retraction_date'])

# Identify research from an institution that is listed in the Retraction Watch/Crossref database
retracted_research = df_publications[df_publications['doi'].isin(retractions['original_paper_doi'])]
retracted_research = (
    retracted_research
    .drop(columns=['reference_ids'])
)
retracted_research = pd.merge(
    retracted_research,
    retractions,
    left_on='doi',
    right_on='original_paper_doi',
    how='left'
)

if retracted_research.empty or retracted_research['doi'].isnull().all():
    pass
else:
    retracted_research = (
    retracted_research
    .rename(columns={'reason': 'retraction_reason', 
                     'record_id': 'rw_record_id'})
    .drop(columns=['original_paper_doi'])
    .assign(rw_record_id = lambda df: df['rw_record_id'].astype(int))
    )
    
    retracted_research = pd.merge(
    retracted_research,
    df_affiliations,
    on='pub_id',
    how='left'
    )
    
    retracted_research.to_csv(os.path.join(DATA_DIR, ''.join(['retracted_research_', str(YEAR), '.csv'])), index=False, encoding = 'utf-8')

# Get the list of references cited by an institution's outputs
df_references = df_publications.filter(['pub_id', 'reference_ids']).explode('reference_ids')
df_references = df_references[df_references['reference_ids'].notnull()]

'''
Publications aren't going to suddenly cite new publications after they have 
been published, so we only need to get this data once and store it in the 
working directory. We can then reload the list of cited references and check
that against the updated Retraction Watch/Crossref database.

An exception to this rule is the current year of publication, where new
outputs from an instituion will have to be checked and new references added
to the list.
 
 To re-collect the data for a particluar year of publication, delete the 
 relevant cited_publications_*.csv file from the current working directory 
 prior to running this code.
'''
if not os.path.exists(os.path.join(DATA_DIR, ''.join(['cited_publications_', str(YEAR), '.csv']))):
    
    split: int = int(np.ceil(df_references.shape[0]/390))
    df_references_split: list = np.array_split(df_references, split)
    
    df_cited_publications = pd.DataFrame()

    for i in range(len(df_references_split)):
        pubs = df_references_split[i]['reference_ids'].drop_duplicates()
        results = dsl.query_iterative(f"""search publications
               where id in {json.dumps(list(pubs))}
               return publications[id+doi]
               """).as_dataframe()
        df_cited_publications = pd.concat([df_cited_publications, results])
        
    df_cited_publications.to_csv(os.path.join(DATA_DIR, ''.join(['cited_publications_', str(YEAR), '.csv'])), index=False)
else:
    df_cited_publications = pd.read_csv(os.path.join(DATA_DIR, ''.join(['cited_publications_', str(YEAR), '.csv'])))

dimcli.logout()

# Check if any of the cited references are in the Retraction Watch/Crossref and
# get the institution's citing outputs
df_problematic_publications = df_cited_publications[df_cited_publications['doi'].isin(retractions['original_paper_doi'])]
df_problematic_publications = df_problematic_publications[df_problematic_publications['doi'].notnull()]
df_problematic_publications = df_problematic_publications.rename(columns={'id': 'reference_ids'})

df_problematic_publications = pd.merge(
    df_references,
    df_problematic_publications,
    on='reference_ids',
    how='left'
)

df_problematic_publications = df_problematic_publications.rename(columns={'doi': 'original_paper_doi'})
df_problematic_publications = df_problematic_publications[df_problematic_publications['original_paper_doi'].notnull()]
df_problematic_publications = df_problematic_publications.drop_duplicates()

df_problematic_publications = pd.merge(
    df_problematic_publications,
    retractions,
    on='original_paper_doi',
    how='left'
)

df_problematic_publications = (
    df_problematic_publications
    .rename(columns={'id': 'pub_id', 
                     'reason': 'retraction_reason', 
                     'record_id': 'rw_record_id', 
                     'original_paper_doi': 'retracted_paper_doi'})
)

df_problematic_publications = pd.merge(
    df_publications,
    df_problematic_publications,
    on='pub_id',
    how='inner'
)

df_problematic_publications = pd.merge(
    df_affiliations,
    df_problematic_publications,
    on='pub_id',
    how='left'
)

df_problematic_publications = df_problematic_publications.rename(columns={'reference_ids_y': 'retracted_pub_id'}).drop(columns=['reference_ids_x'])
df_problematic_publications['date'] = pd.to_datetime(df_problematic_publications['date'])
df_problematic_publications['cited_after_retraction'] = df_problematic_publications.apply(lambda df: True if df['retraction_date'] < df['date'] else False, axis=1)

excluded_cols = ['researcher_id', 'full_name']
df_problematic_publications = (
    df_problematic_publications
    .groupby([col for col in df_problematic_publications.columns if col not in excluded_cols]).agg({'researcher_id': list, 'full_name': list})
    .reset_index()
)

# Relocating columns is so much easier in dplyr
df_problematic_publications = df_problematic_publications[['researcher_id', 'full_name'] + [col for col in df_problematic_publications.columns if col not in excluded_cols]]
title, pub_id = df_problematic_publications.pop('title'), df_problematic_publications.pop('pub_id')
df_problematic_publications.insert(5, 'pub_id', pub_id)
df_problematic_publications.insert(9, 'title', title)
df_problematic_publications = df_problematic_publications.assign(rw_record_id = lambda df: df['rw_record_id'].astype(int))

df_problematic_publications.to_csv(os.path.join(DATA_DIR, ''.join(['problematic_publications_', str(YEAR), '.csv'])), index=False)
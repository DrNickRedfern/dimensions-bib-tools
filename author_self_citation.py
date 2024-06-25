import dimcli
from dotenv import load_dotenv
import numpy as np
import pandas as pd

import json
import os

load_dotenv()

# Set the Dimensions id of the researcher
RESEARCHER_ID: list[str] = ['ur.0723623633.34']

# Log into Dimensions API
API_KEY = os.getenv('API_KEY')
dimcli.login(key=API_KEY, endpoint='https://app.dimensions.ai/api/dsl/v2')
dsl = dimcli.Dsl()

# Search Dimensions for publications by the researcher
# TODO This needs a loop for a list of researchers
results = dsl.query_iterative(f"""search publications where researchers.id in {json.dumps(RESEARCHER_ID)}
                             return publications[id+year+reference_ids+times_cited+authors]""")

publications = results.as_dataframe()
affiliations = results.as_dataframe_authors_affiliations()

dimcli.logout()

# Summarise the publication data
# count number of publications
n_publications = publications.id.count()
# total number of citations
citations = publications.times_cited.sum()
# Get the author's name
temp = affiliations[affiliations['researcher_id'] == RESEARCHER_ID[0]].iloc[0]
name = temp.first_name + ' ' + temp.last_name

# Get the references for each paper by the researcher
references = (
    publications
    .filter([
        'id', 
        'reference_ids'
    ])
    .explode('reference_ids')
    .set_index('id')
    .reset_index()
)

# Limit the references to publications that have been authored by the researcher
references = references[references['reference_ids'].isin(publications['id'])]

self_cites = references.groupby('reference_ids').count().reset_index()
self_cites = (
    self_cites
    .rename(columns={
        'id': 'self_cites',
        'reference_ids': 'id'
    })
)

# Summarise the self citations
# number of papers self cited
n_self_cited = self_cites.id.nunique()

# number of self citations
total_self_cites = self_cites.self_cites.sum()

# proportion of papers self_cited
p_self_cited = round(100 * (n_self_cited / n_publications), 1)

# self citations as a porportion of citations
p_self_citations = round(100 * (total_self_cites / citations), 1)

# Create data frame for export
df_self_citation = pd.DataFrame({
    'researcher': [name],
    'n_publications': [n_publications],
    'citations': [citations],
    'n_self_cited': [n_self_cited],
    'total_self_cites': [total_self_cites],
    'percent_self_cited': [p_self_cited],
    'percent_self_citations': [p_self_citations]
})

df_self_citation.to_csv('self_citation.csv', index=False)
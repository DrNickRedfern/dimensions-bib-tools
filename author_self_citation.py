import dimcli
from dotenv import load_dotenv
import numpy as np
import pandas as pd

import json
import os

load_dotenv()

# Set the Dimensions id of the researcher
publications = pd.read_csv('publications.csv')

researcher_ids = publications['researcher_id'].drop_duplicates().tolist()

# Log into Dimensions API
API_KEY = os.getenv('API_KEY')
dimcli.login(key=API_KEY, endpoint='https://app.dimensions.ai/api/dsl/v2')
dsl = dimcli.Dsl()

df_self_citation = pd.DataFrame()

for i in range(len(researcher_ids)):
    researcher: str = researcher_ids[i]
    results = dsl.query_iterative(f"""search publications where researchers.id = {json.dumps(researcher)}
                             return publications[id+year+reference_ids+times_cited+authors]""")
    publications = results.as_dataframe()
    affiliations = results.as_dataframe_authors_affiliations()
    
    # Summarise the publication data
    # Count number of publications
    n_publications = publications.id.count()
    # Total number of citations
    citations = publications.times_cited.sum()
    # Get the author's name
    temp = affiliations[affiliations['researcher_id'] == researcher_ids[i]].iloc[i]
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
    # Number of self cited papers
    n_self_cited = self_cites.id.nunique()
    
    # Number of self citations
    total_self_cites = self_cites.self_cites.sum()
    
    # Proportion of papers self_cited
    p_self_cited = round(100 * (n_self_cited / n_publications), 1)
    
    # Self citations as a porportion of citations
    p_self_citations = round(100 * (total_self_cites / citations), 1)
    
    # Create data frame for export
    df_self_temp = pd.DataFrame({
        'researcher': [name],
        'total_publications': [n_publications],
        'self_cited_publications': [n_self_cited],
        'percent_self_cited': [p_self_cited],
        'total_citations': [citations],
        'total_self_citations': [total_self_cites],
        'percent_self_citations': [p_self_citations]
    })
    
    df_self_citation= pd.concat([df_self_citation, df_self_temp])

dimcli.logout()

df_self_citation.to_csv('self_citation.csv', index=False)
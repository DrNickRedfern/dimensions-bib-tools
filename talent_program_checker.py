'''
talent_program_checker.py code is designed to extract information from Dimensions
about publications that are funded by specific talent programs.

The input to the code is a CSV file called "publications.csv" that contains a 
list of publication ids in the Dimensions database.

The output of the code is a new CSV file called "talent_plans.csv" that contains 
two columns: "pub_id" (the publication ID) and "talent_plan" (the name of the 
talent program associated with that publication).
'''
import dimcli
from dotenv import load_dotenv
import numpy as np
import pandas as pd

import json
import os
import re

publications = pd.read_csv('publications.csv')
publications = publications.filter(['publication_id']).drop_duplicates(['publication_id'])

split = int(np.ceil(publications.shape[0]/512))
dat_split = np.array_split(publications, split)

# Log into Dimensions
load_dotenv()
API_KEY = os.getenv('API_KEY')
dimcli.login(key=API_KEY, endpoint='https://app.dimensions.ai/api/dsl/v2')
dsl = dimcli.Dsl()

df_publications = pd.DataFrame()
df_authors = pd.DataFrame()
df_affiliations = pd.DataFrame()
for i in range(len(dat_split)):
    pubs = dat_split[i]['doi']
    results = dsl.query(f'''search publications
                    where id in {json.dumps(list(pubs))}
                    return publications[id+funding_section+funders]
                    limit 1000 skip 0
                    '''
    )
    
    df_pubs_temp = results.as_dataframe()
    df_authors_temp = results.as_dataframe_authors()
    df_affiliations_temp = results.as_dataframe_authors_affiliations()
    
    df_publications = pd.concat([df_publications, df_pubs_temp])
    df_authors = pd.concat([df_authors, df_authors_temp])
    df_affiliations = pd.concat([df_affiliations, df_affiliations_temp])
    
dimcli.logout()

df_publications_filtered = df_publications[df_publications['funding_section'].notnull()]
talents_programs = df_publications_filtered[df_publications_filtered['funding_section'].str.contains('talents program', case=False)]

talent_plans = pd.DataFrame()

for i in range(talents_programs.shape[0]):
    match = re.search(r',([^,]*Talents Program),', talents_programs['funding_section'].iloc[i])
    if match:
        result = match.group(1).strip()
        df_temp = pd.DataFrame({'talent_plan': result}, index=[0])
        df_temp['pub_id'] = talents_programs['id'].iloc[i]
    
    talent_plans = pd.concat([talent_plans, df_temp])

talent_plans = talent_plans[['pub_id'] + ['talent_plan']]
talent_plans.to_csv('talent_plans.csv', index=False)
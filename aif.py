import dimcli
from dotenv import load_dotenv
import numpy as np
import pandas as pd

import json
import os

load_dotenv()

# Set variables
RESEARCHER_ID: list[str] = ['ur.01024019836']
DELTA: int = 5

# Log into Dimensions
API_KEY = os.getenv('API_KEY')
dimcli.login(key=API_KEY, endpoint='https://app.dimensions.ai/api/dsl/v2')
dsl = dimcli.Dsl()

# Retrieve the publications for a disambiguated researcher in Dimensions
publications = dimcli.query(f"""search publications where researchers.id = {json.dumps(RESEARCHER_ID)} 
                             return publications[id+year+reference_ids+times_cited]""").as_dataframe()

references = publications.filter(['reference_ids']).explode('reference_ids')
references = references[references['reference_ids'].notnull()]

split: int = int(np.ceil(references.shape[0]/390))
references_split: list = np.array_split(references, split)

# Get the publication id and year of publication for all publications citing publications by a researcher
citations = pd.DataFrame()

for i in range(len(references_split)):
    # TODO Make sure that duplicates are not dropped in order to fully count the number of citations of each publication
    pubs = references_split[i]['id']#.drop_duplicates()
    results = dimcli.query_iterative(f"""search publications where reference_ids in {json.dumps(list(pubs))}
                            return publications[id+year]
                            """).as_dataframe()
    citations = pd.concat([citations, results])

dimcli.logout()

# Calculate the number of publications published in each year
publications_per_year = publications.groupby('year').count().reset_index()

# Calculate the number of citations in each year
citations_per_year = citations.groupby('year').count().reset_index()

# Calculate the ratio of the number of publications in year t to the number of citations in [t-DELTA, t-1]
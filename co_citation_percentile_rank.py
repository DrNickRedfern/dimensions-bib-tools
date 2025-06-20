'''
This code analyses the citation patterns of a set of publications and calculate 
a percentile rank for each publication based on its co-citation rate. The 
purpose of the code is to provide insights into the relative impact and 
influence of publications within a specific research field or domain.

This method is based on JYUcite (https://oscsolutions.cc.jyu.fi/jyucite/), but
returns comparable if slightly different results.

The code uses several Python libraries, including pandas for data manipulation, 
numpy for numerical operations, and dimcli for interacting with the Dimensions API.

The code takes a CSV file named 'publications.csv' as input, which should 
contain a column named 'doi' with the Digital Object Identifiers (DOIs) of the 
publications to be analyzed.

The output of the code is another CSV file named 
'co_citation_percentile_rank.csv', which contains various metrics related to 
the citations and co-citations of the input publications, including a 
percentile rank for each publication based on its co-citation rate.

To achieve its purpose, the code follows these steps:

- It reads the input CSV file containing the DOIs of the publications to be 
analyzed.
- It connects to the Dimensions API, which is a database of scholarly 
publications and citation data.
- It retrieves the citation data for the input publications from the Dimensions API.
- For each input publication, it finds the publications that cite it.
- It retrieves the citation data for the co-cited publications from the Dimensions API.
- It calculates various metrics for the co-cited publications, such as the 
number of citations, the citation rate, and the percentile rank based on the 
citation rate.
- It filters the results to include only the input publications and their 
corresponding metrics.
- It saves the final results to the output CSV file.

One important data transformation happening in the code is the calculation of 
the citation rate (rate) for each co-cited publication. This is done by 
dividing the number of citations (times_cited) by the number of days since the 
publication date (days) and then multiplying by 365 to get an annualized rate.

Another key step is the calculation of the percentile rank (percentrank) for 
each co-cited publication within the group of publications co-cited with the 
same input publication. This is done using the rank() function from pandas, 
which assigns a rank to each value in a group based on the specified method 
(in this case, 'max' for the maximum value).
'''
from dotenv import load_dotenv

import dimcli
import numpy as np
import pandas as pd

import json
import os

# Load a csv file containing the dois of publications to search for
# The column containg DOIs should be called doi
df_publications = pd.read_csv('publications.csv')

# Housekeeping
DATA_DIR: str = os.path.join(os.getcwd(), 'data')
if not os.path.isdir(DATA_DIR):
    os.mkdir(DATA_DIR)
    print('Created folder : ', DATA_DIR)
else:
    print('Data folder already exists.')

# Log into Dimensions API
load_dotenv()
API_KEY = os.getenv('API_KEY')
dimcli.login()
dsl = dimcli.Dsl()

# Get the data for our publications
split: int = int(np.ceil(df_publications.shape[0]/400))
df_publications_split: list = np.array_split(df_publications, split)
df_target_pubs = pd.DataFrame()
for i in range(len(df_publications_split)): 
    pubs = df_publications_split[i]['doi'].drop_duplicates()
    results = dsl.query_iterative(f"""search publications where doi in {json.dumps(list(pubs))}
                                      return publications[id+times_cited+date]""").as_dataframe()
    df_target_pubs = pd.concat([df_target_pubs, results])

# Get the co-citation cohort for our publications
split: int = int(np.ceil(df_target_pubs.shape[0]/400))  
df_target_pubs_split: list = np.array_split(df_target_pubs, split)
df_co_cites = pd.DataFrame()
for index, row in df_target_pubs.iterrows():
    co_cites = dsl.query(f"""search publications where reference_ids = "{row['id']}"
                             return publications[reference_ids] limit 1000""").as_dataframe()
    co_cites['target_id'] = np.repeat(row['id'], len(co_cites))
    df_co_cites = pd.concat([df_co_cites, co_cites])

df_co_cites = df_co_cites.explode('reference_ids').drop_duplicates()  # This may be redundant for this evolution

# Get the data for the co-citation cohort
split: int = int(np.ceil(df_co_cites.shape[0]/400))
df_co_cites_split = np.array_split(df_co_cites, split)
df_final_data = pd.DataFrame()
for i in range(len(df_co_cites_split)):
    pubs = df_co_cites_split[i]['reference_ids'].drop_duplicates()
    final_data = dsl.query_iterative(f"""search publications where id in {json.dumps(list(pubs))}
                                         return publications[id+times_cited+date]""").as_dataframe()
    df_final_data = pd.concat([df_final_data, final_data])

dimcli.logout()

df_final_data = pd.merge(
    df_co_cites,
    df_final_data,
    left_on='reference_ids',
    right_on='id',
    how='left'
).drop(columns=['id'])

# Calculations
df_final_data = df_final_data[df_final_data['date'].notnull()]
df_final_data = df_final_data.sort_values('times_cited', ascending=False)
df_final_data['times_cited'] = df_final_data['times_cited'].astype(int)
df_final_data['date'] = pd.to_datetime(df_final_data['date'])
df_final_data['days'] = pd.to_datetime('now') - df_final_data['date']
df_final_data['days'] = df_final_data['days'].dt.days
df_final_data['rate'] = round((df_final_data['times_cited']/df_final_data['days']) * 365, 2)
df_final_data['percentrank'] = df_final_data.groupby(['target_id'])['rate'].rank(pct=True, method='max')
df_final_data['percentrank'] = (df_final_data['percentrank'].round(2)) * 100
df_final_data['percentrank'] = df_final_data['percentrank'].astype(int)
df_output = df_final_data[df_final_data['reference_ids'] == df_final_data['target_id']].drop_duplicates()

df_output.to_csv('co_citation_percentile_rank.csv', index=False)
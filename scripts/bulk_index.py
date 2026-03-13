import pandas as pd
import numpy as np
from opensearchpy import OpenSearch, helpers

client = OpenSearch(
    hosts=[{"host": "opensearch", "port": 9200}]
)

# Load CSV
df = pd.read_csv("data/final_data.csv", low_memory=False)

# Remove unwanted column
df = df.drop(columns=["Unnamed: 0"], errors="ignore")

# Replace NaN values
df = df.replace({np.nan: None})

# Ensure numeric columns are correct
numeric_columns = ["length", "size", "weight"]

for col in numeric_columns:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.replace({np.nan: None})

actions = []

for _, row in df.iterrows():

    doc = row.to_dict()

    actions.append({
        "_index": "jewellery_products",
        "_id": str(doc["products_id"]),
        "_source": doc
    })

helpers.bulk(client, actions, chunk_size=500)

print("Bulk indexing completed successfully")
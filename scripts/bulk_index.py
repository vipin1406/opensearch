import pandas as pd
import numpy as np
import re
from opensearchpy import OpenSearch, helpers
from prepare_data import generate_tags


NORMALIZATION_MAP = {
    "pendent": "pendant",
    "pendant": "pendant",
    "doller": "dollar",
    "dollar": "dollar",
    "attigai": "attigai",
    "adigai": "attigai",
    "chian":"chain",
    "enamal":"enamel"
}

def normalize_text(value):
    if not value:
        return value

    words = str(value).lower().split()

    normalized_words = []

    for w in words:
        if w in NORMALIZATION_MAP:
            normalized_words.append(NORMALIZATION_MAP[w])
        else:
            normalized_words.append(w)

    return " ".join(normalized_words)

# ------------------------------------------------
# CONNECT TO OPENSEARCH
# ------------------------------------------------
client = OpenSearch(
    hosts=[{"host": "opensearch", "port": 9200}]
)


# ------------------------------------------------
# NORMALIZE LAYERS FUNCTION
# ------------------------------------------------
def normalize_layers(value):

    if not value:
        return None

    value = str(value).lower().strip()

    # handle multiple layers
    if "multiple" in value or "multi" in value:
        return 4

    # extract numeric value
    match = re.search(r"\d+", value)

    if match:
        return int(match.group())

    return None


# ------------------------------------------------
# LOAD CSV
# ------------------------------------------------
df = pd.read_csv("data/final_data.csv", low_memory=False)

print("\nCSV Loaded")
print("Total rows:", len(df))


# ------------------------------------------------
# REMOVE UNWANTED COLUMN
# ------------------------------------------------
df = df.drop(columns=["Unnamed: 0"], errors="ignore")


# ------------------------------------------------
# REPLACE NaN VALUES
# ------------------------------------------------
df = df.replace({np.nan: None})


# ------------------------------------------------
# ENSURE NUMERIC COLUMNS
# ------------------------------------------------
numeric_columns = ["length", "size", "weight"]

for col in numeric_columns:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.replace({np.nan: None})

import re

def normalize_layers(value):

    if not value:
        return None

    value = str(value).lower().strip()

    if value == "none":
        return None

    if "multiple" in value or "multi" in value:
        return 4

    match = re.search(r"\d+", value)

    if match:
        return int(match.group())

    return None


# apply normalization
if "layers" in df.columns:
    df["layers"] = df["layers"].apply(normalize_layers)

print("\nLayer distribution after normalization:")
print(df["layers"].value_counts(dropna=False))


# ------------------------------------------------
# NORMALIZE LAYERS COLUMN
# ------------------------------------------------
if "layers" in df.columns:

    print("\nNormalizing layers column...")

    df["layers"] = df["layers"].apply(normalize_layers)

    print("Unique normalized layer values:")
    print(df["layers"].unique())

df = df.where(pd.notnull(df), None)

# ------------------------------------------------
# PREPARE BULK ACTIONS
# ------------------------------------------------
actions = []



for _, row in df.iterrows():

    doc = row.to_dict()

    # 🔧 FIX: convert NaN → None
    for key, value in doc.items():
        if pd.isna(value):
            doc[key] = None

    # 🔥 NORMALIZE HERE (CORRECT PLACE)
    for field in ["product_name", "product_type"]:
        if field in doc and doc[field]:
            doc[field] = normalize_text(doc[field])
    


    # 🔥 ADD TAG GENERATION HERE
    doc["tags"] = generate_tags(doc)

    # 🔥 DEBUG (TEMP)
    print("\nINDEXING:", doc.get("product_name"))
    print("TAGS:", doc.get("tags"))

    actions.append({
        "_index": "jewellery_products",
        "_id": str(doc["products_id"]),
        "_source": doc
    })


print("\nPreparing to index documents...")
print("Total documents:", len(actions))


# ------------------------------------------------
# BULK INDEX
# ------------------------------------------------
helpers.bulk(client, actions, chunk_size=500)

print("\nBulk indexing completed successfully!")
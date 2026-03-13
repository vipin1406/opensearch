import pandas as pd

df = pd.read_csv("data/result.csv")

# remove unwanted column
df = df.drop(columns=["Unnamed: 0"], errors="ignore")

# normalize NA values
df = df.replace("<na>", None)

# lowercase text fields
text_fields = [
    "metal",
    "purity",
    "product_type",
    "stone_type",
    "gender"
]

for col in text_fields:
    if col in df.columns:
        df[col] = df[col].str.lower()

df.to_csv('data/fina_result.csv')

print("Data cleaned successfully")
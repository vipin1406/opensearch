import re

# ------------------------------------------------
# PURITY NORMALIZATION
# ------------------------------------------------
PURITY_MAP = {
    "22k": "22k",
    "22karat":"22k",
    "22 karat":"22k",
    "22carat":"22k",
    "22 carat":"22k",
    "22kt": "22K",
    "916": "22K",
    "18karat":"22k",
    "18 karat":"22k",
    "18carat":"22k",
    "18 carat":"22k",
    "18k": "18k",
    "18kt": "18k",
    "750": "18k"
}

import re

def normalize_query(query: str) -> str:
    print("\n========== NORMALIZER ==========")

    # 🔥 split merged tokens: with24 → with 24
    query = re.sub(r"([a-zA-Z])(\d)", r"\1 \2", query)

    # 🔥 split: 24grams → 24 grams
    query = re.sub(r"(\d)([a-zA-Z])", r"\1 \2", query)

    # normalize spaces
    query = re.sub(r"\s+", " ", query).strip()

    print("Normalized Query:", query)
    print("================================\n")

    return query

import re

def normalize_purity(query):
    """
    Extract purity and REMOVE it completely from query
    """

    purity = None

    # Match: 22k, 22 k, 22 karat, 22kt
    match = re.search(r"\b(22|18|24)\s*(k|kt|karat)?\b", query)

    if match:
        value = match.group(1)
        purity = f"{value}k"

        # 🔥 Remove the full matched pattern
        query = query.replace(match.group(0), "")

    # 🔥 Remove leftover words (important)
    query = re.sub(r"\b(k|kt|karat)\b", "", query)

    # 🔥 Clean extra spaces
    query = " ".join(query.split())

    return query, purity

# ------------------------------------------------
# WEIGHT NORMALIZATION
# ------------------------------------------------
WEIGHT_PATTERN = r'(\d+(?:\.\d+)?)\s*(grams|gram|graam|grms|grm|gm|g)\b'

def normalize_weight(query):
    match = re.search(WEIGHT_PATTERN, query)

    if not match:
        return query, None

    weight = round(float(match.group(1)), 2)

    query = re.sub(WEIGHT_PATTERN, "", query)

    print(f"[NORMALIZER] Weight → {weight} grams")

    return query, weight


# ------------------------------------------------
# WEIGHT RANGE
# ------------------------------------------------
RANGE_PATTERN = r'(under|below|above|over)\s*(\d+(?:\.\d+)?)\s*(grams|gram|gm|g)\b'

def normalize_weight_range(query):
    match = re.search(RANGE_PATTERN, query)

    if not match:
        return query, None

    condition = match.group(1)
    value = float(match.group(2))

    if condition in ["under", "below"]:
        result = {"lte": value}
    else:
        result = {"gte": value}

    query = re.sub(RANGE_PATTERN, "", query)

    print(f"[NORMALIZER] Weight range → {result}")

    return query, result


# ------------------------------------------------
# FINAL CLEANUP
# ------------------------------------------------
def clean_query(query):
    query = re.sub(r'\s+', ' ', query).strip()
    return query
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

def normalize_purity(query):
    pattern = r"(22\s?k|22\s?kt|916|18\s?k|18\s?kt|750|14\s?k|14\s?kt|585)"
    match = re.search(pattern, query)

    if not match:
        return query, None

    raw = match.group(0).replace(" ", "").lower()
    normalized = PURITY_MAP.get(raw)

    query = re.sub(pattern, "", query)

    print(f"[NORMALIZER] Purity → {raw} → {normalized}")

    return query, normalized


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
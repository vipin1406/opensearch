import re

GENDER_MAP = {
    "ladies": "WOMEN",
    "women": "WOMEN",
    "mens": "MEN",
    "men": "MEN",
    "unisex": "UNISEX",
    "baby": "BABY"
}

NORMALIZATION_MAP = {
    "pendent": "pendant",
    "doller": "dollar",
    "adigai": "attigai"
}


# 🔥 NORMALIZATION FUNCTION
def normalize_query_text(text: str):

    words = text.split()

    normalized_words = []

    for w in words:
        if w in NORMALIZATION_MAP:
            normalized_words.append(NORMALIZATION_MAP[w])
        else:
            normalized_words.append(w)

    return " ".join(normalized_words)


# 🔥 PARSE QUERY (ONLY PLACE FOR NORMALIZATION)
def parse_query(query: str):

    filters = {}

    clean_query = query.lower()

    # ✅ NORMALIZE HERE (IMPORTANT)
    clean_query = normalize_query_text(clean_query)

    # -------- Gender Detection --------
    for word, value in GENDER_MAP.items():
        if word in clean_query:
            filters["gender"] = value
            clean_query = clean_query.replace(word, "")

    # -------- Purity Detection --------
    purity_match = re.search(r"(22|18)\s?kt", clean_query)
    if purity_match:
        kt = purity_match.group(1)
        if kt == "22":
            filters["purity"] = 916
        elif kt == "18":
            filters["purity"] = 750
        clean_query = re.sub(r"(22|18)\s?kt", "", clean_query)

    # -------- Weight Detection --------
    weight_match = re.search(r"(\d+)\s?(g|gm|gram|grams)", clean_query)
    if weight_match:
        filters["product_weight"] = float(weight_match.group(1))
        clean_query = re.sub(r"(\d+)\s?(g|gm|gram|grams)", "", clean_query)

    return clean_query.strip(), filters


# 🔥 TOKENIZER (NO NORMALIZATION HERE)
def tokenize_query(query: str):

    print("\n========== TOKENIZATION ==========")

    query = query.lower().strip()

    tokens = query.split()

    print("Original Query:", query)
    print("Tokens:", tokens)

    print("==================================\n")

    return tokens
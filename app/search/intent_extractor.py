from difflib import get_close_matches
from metaphone import doublemetaphone
from app.search.entity_loader import load_catalog_entities
import re
from app.search.config import PURITY_MAP,GENDER_MAP
CATALOG_ENTITIES = None


def phonetic_code(word):
    return doublemetaphone(word)[0]


def fuzzy_match(token, values):

    match = get_close_matches(token, values, n=1, cutoff=0.8)

    return match[0] if match else None


def phonetic_match(token, values):

    token_ph = phonetic_code(token)

    for value in values:

        if phonetic_code(value) == token_ph:
            return value

    return None


def extract_intent(query):

    global CATALOG_ENTITIES

    print("\n================================================")
    print("INTENT EXTRACTION STARTED")
    print("================================================")

    print("\nIncoming Query:", query)

    # ------------------------------------------------
    # STEP 1 — INITIALIZE STRUCTURES
    # ------------------------------------------------

    filters = {}
    search_terms = []

    # ------------------------------------------------
    # STEP 2 — PURITY DETECTION
    # ------------------------------------------------

    print("\n[STEP 1] PURITY DETECTION")

    purity_pattern = r"(22\s?k|22\s?kt|22\s?carat|916|18\s?k|18\s?kt|18\s?carat|750|14\s?k|14\s?kt|585)"

    match = re.search(purity_pattern, query.lower())

    if match:

        purity_raw = match.group(0).replace(" ", "")
        print("Detected purity token:", purity_raw)

        purity = PURITY_MAP.get(purity_raw)

        if purity:
            filters["purity"] = purity
            print("✔ Matched PURITY →", purity)

        # remove purity from query
        query = query.replace(match.group(0), "")

    else:
        print("No purity detected")

    print("Query after purity removal:", query)


    # ------------------------------------------------
    # STEP 3 — LAYER DETECTION
    # ------------------------------------------------
    print("\n[STEP 2] LAYER DETECTION")

    layer_pattern = r"(\d+)\s*layer"

    match = re.search(layer_pattern, query.lower())

    if match:

        layer_value = int(match.group(1))

        # If layer >= 4 treat as multiple layer
        if layer_value >= 4:

            filters["layers_range"] = layer_value

            print("✔ Matched MULTIPLE LAYERS → >=", layer_value)

        else:

            filters["layers"] = layer_value

            print("✔ Matched LAYERS →", layer_value)

        query = query.replace(match.group(0), "")



    # ------------------------------------------------
    # STEP 3 — WEIGHT DETECTION
    # ------------------------------------------------

    print("\n[STEP] WEIGHT DETECTION")

    query_lower = query.lower()

    # detect sovereign
    sovereign_match = re.search(r'(under|below|above|over)?\s*(\d+)\s*sovereign', query_lower)

    if sovereign_match:

        condition = sovereign_match.group(1)
        sovereign = int(sovereign_match.group(2))

        grams = sovereign * 8

        if condition in ["under", "below"]:

            filters["weight_range"] = {"lte": grams}
            print(f"✔ Matched WEIGHT → <= {grams} grams")

        elif condition in ["above", "over"]:

            filters["weight_range"] = {"gte": grams}
            print(f"✔ Matched WEIGHT → >= {grams} grams")

        else:

            filters["weight_range"] = {"gte": grams, "lte": grams}
            print(f"✔ Matched WEIGHT → {grams} grams")

        query = query.replace(sovereign_match.group(0), "")


    gram_match = re.search(r'(\d+)\s*(g|gram|grams)', query_lower)


    if gram_match:

        weight = int(gram_match.group(1))

        filters["weight_range"] = {"gte": weight, "lte": weight}

        print(f"✔ Matched WEIGHT → {weight} grams")

        query = query.replace(gram_match.group(0), "")
    
    # under weight
    under_match = re.search(r'(under|below)\s*(\d+)\s*(g|gram|grams)', query_lower)

    if under_match:

        weight = int(under_match.group(2))

        filters["weight_range"] = {"lte": weight}

        print(f"✔ Matched WEIGHT → <= {weight}g")

        query = query.replace(under_match.group(0), "")

    # above weight
    above_match = re.search(r'(above|over)\s*(\d+)\s*(g|gram|grams)', query_lower)

    if above_match:

        weight = int(above_match.group(2))

        filters["weight_range"] = {"gte": weight}

        print(f"✔ Matched WEIGHT → >= {weight}g")

        query = query.replace(above_match.group(0), "")

    # ------------------------------------------------
    # STEP 4 — LOAD CATALOG ENTITIES
    # ------------------------------------------------

    if CATALOG_ENTITIES is None:

        print("\n[STEP 2] LOADING CATALOG ENTITIES")

        CATALOG_ENTITIES = load_catalog_entities()

        print("Catalog entities loaded:")
        print(CATALOG_ENTITIES)

    # ------------------------------------------------
    # STEP 5 — TOKENIZATION
    # ------------------------------------------------

    print("\n[STEP 3] TOKENIZATION")

    # Stop words for search
    STOP_WORDS = {"under", "below", "above", "over", "with", "of","for","without"}

    tokens = [
        token for token in query.lower().split()
        if token not in STOP_WORDS
    ]

    print("Tokens after stop-word removal:", tokens)

    # ------------------------------------------------
    # STEP 6 — TOKEN PROCESSING
    # ------------------------------------------------

    print("\n[STEP 4] TOKEN PROCESSING")

    for token in tokens:

        print("\nProcessing token:", token)

        matched = False

        # -------- GENDER DETECTION --------

        if token in GENDER_MAP:

            gender_value = GENDER_MAP[token]

            filters["gender"] = gender_value

            print(f"✔ Matched GENDER → {gender_value}")

            continue

        for field, values in CATALOG_ENTITIES.items():
            print("Checking field:", field)

            # -------- EXACT MATCH --------
            if token in values:

                filters[field] = token

                print(f"✔ Exact match → {field} = {token}")

                matched = True
                break

            # -------- FUZZY MATCH --------
            fuzzy = fuzzy_match(token, values)

            if fuzzy:

                filters[field] = fuzzy

                print(f"✔ Fuzzy match → {field} = {fuzzy}")

                matched = True
                break

            # -------- PHONETIC MATCH --------
            phonetic = phonetic_match(token, values)

            if phonetic:

                filters[field] = phonetic

                print(f"✔ Phonetic match → {field} = {phonetic}")

                matched = True
                break

        if not matched:

            print("Token added to search text")

            search_terms.append(token)

    # ------------------------------------------------
    # STEP 7 — FINAL SEARCH TEXT
    # ------------------------------------------------

    search_text = " ".join(search_terms)

    print("\n================================================")
    print("INTENT EXTRACTION RESULT")
    print("================================================")

    print("Search Text:", search_text)
    print("Extracted Filters:", filters)

    print("================================================\n")

    return search_text, filters
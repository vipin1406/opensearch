from difflib import get_close_matches
from metaphone import doublemetaphone
from app.search.entity_loader import load_catalog_entities
import re
from app.search.config import PURITY_MAP, GENDER_MAP

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

    filters = {}
    search_terms = []

    query = query.lower()

    # ------------------------------------------------
    # PURITY DETECTION
    # ------------------------------------------------

    print("\n[STEP 1] PURITY DETECTION")

    purity_pattern = r"(22\s?k|22\s?kt|916|18\s?k|750|14\s?k|585)"

    match = re.search(purity_pattern, query)

    if match:

        purity_raw = match.group(0).replace(" ", "")
        purity = PURITY_MAP.get(purity_raw)

        if purity:
            filters["purity"] = purity
            print("✔ Matched PURITY →", purity)

        query = query.replace(match.group(0), "")

    else:
        print("No purity detected")

    # ------------------------------------------------
    # LAYER DETECTION
    # ------------------------------------------------

    print("\n[STEP 2] LAYER DETECTION")

    layer_pattern = r"(\d+)\s*layer"

    match = re.search(layer_pattern, query)

    if match:

        layer_value = int(match.group(1))

        if layer_value >= 4:
            filters["layers_range"] = layer_value
            print("✔ Multiple Layers ≥", layer_value)
        else:
            filters["layers"] = layer_value
            print("✔ Layers =", layer_value)

        query = query.replace(match.group(0), "")

    # ------------------------------------------------
    # WEIGHT DETECTION
    # ------------------------------------------------

    print("\n[STEP 3] WEIGHT DETECTION")

    sovereign_match = re.search(r'(under|below|above|over)?\s*(\d+)\s*sovereign', query)

    if sovereign_match:

        condition = sovereign_match.group(1)
        sovereign = int(sovereign_match.group(2))

        grams = sovereign * 8

        if condition in ["under", "below"]:
            filters["weight_range"] = {"lte": grams}
            print("✔ Weight ≤", grams)

        elif condition in ["above", "over"]:
            filters["weight_range"] = {"gte": grams}
            print("✔ Weight ≥", grams)

        else:
            filters["weight_value"] = grams
            print("✔ Target Weight", grams)

        query = query.replace(sovereign_match.group(0), "")

    elif re.search(r'(\d+)\s*(g|gram|grams)', query):

        gram_match = re.search(r'(\d+)\s*(g|gram|grams)', query)

        weight = int(gram_match.group(1))

        filters["weight_value"] = weight

        print("✔ Target Weight →", weight)

        query = query.replace(gram_match.group(0), "")

    # ------------------------------------------------
    # LOAD ENTITIES
    # ------------------------------------------------

    if CATALOG_ENTITIES is None:

        print("\n[STEP 4] Loading catalog entities")

        CATALOG_ENTITIES = load_catalog_entities()

    # ------------------------------------------------
    # TOKENIZATION
    # ------------------------------------------------

    STOP_WORDS = {"under","below","above","over","with","of","for","in","on","and"}

    tokens = [t for t in query.split() if t not in STOP_WORDS]

    print("\n[STEP 5] Tokens:", tokens)

    # ------------------------------------------------
    # TOKEN PROCESSING
    # ------------------------------------------------

    for token in tokens:

        print("\nProcessing:", token)

        matched = False

        # ------------------------------------------------
        # LAYER KEYWORD DETECTION
        # ------------------------------------------------

        if token in {"layer", "layers"}:

            if "layers" not in filters and "layers_range" not in filters:
                filters["layers_range"] = 2
                print("✔ Layer keyword detected → layers >= 2")

            continue

        if token in GENDER_MAP:
            filters["gender"] = GENDER_MAP[token]
            print("✔ Gender match", filters["gender"])
            continue

        for field, values in CATALOG_ENTITIES.items():

            if token in values:

                filters[field] = token
                print("✔ Exact match", field)
                matched = True
                break

            fuzzy = fuzzy_match(token, values)

            if fuzzy:

                filters[field] = fuzzy
                print("✔ Fuzzy match", field)
                matched = True
                break

            phonetic = phonetic_match(token, values)

            if phonetic:

                filters[field] = phonetic
                print("✔ Phonetic match", field)
                matched = True
                break

        if not matched:
            search_terms.append(token)

    search_text = " ".join(search_terms)

    print("\n================================================")
    print("INTENT RESULT")
    print("Search Text:", search_text)
    print("Filters:", filters)
    print("================================================")

    return search_text, filters
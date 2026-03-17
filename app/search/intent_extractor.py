from difflib import get_close_matches
from metaphone import doublemetaphone
from app.search.entity_loader import load_catalog_entities
import re
from app.search.config import PURITY_MAP, GENDER_MAP, USAGE_MAP,NUMERIC_FIELDS

CATALOG_ENTITIES = None


def phonetic_code(word):
    return doublemetaphone(word)[0]


def fuzzy_match(token, values):

    # ensure all values are strings
    values = [str(v) for v in values]

    match = get_close_matches(token, values, n=1, cutoff=0.7)

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
    product_type_locked = False

    mugappu_detected = False
    mugappu_count = None

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

    elif re.search(r'(\d+)\s*(grams|gram|gm|grms|grm|graam|g)', query):

        gram_match = re.search(r'(\d+)\s*(grams|gram|gm|grms|grm|graam|g)', query)

        weight = int(gram_match.group(1))

        filters["weight_value"] = weight

        print("✔ Target Weight →", weight)

        # 🔥 IMPORTANT FIX → remove safely using regex
        query = re.sub(r'(\d+)\s*(gm|g|gram|grams|graam|grm|grms)', '', query)

    # ------------------------------------------------
    # LOAD ENTITIES
    # ------------------------------------------------

    if CATALOG_ENTITIES is None:

        print("\n[STEP 4] Loading catalog entities")

        CATALOG_ENTITIES = load_catalog_entities()

    # ------------------------------------------------
    # STEP 4B — MUGAPPU DETECTION
    # ------------------------------------------------

    print("\n[STEP 4B] MUGAPPU DETECTION")

    mugappu_match = re.search(r'(\d+)\s*mugappu', query)

    if mugappu_match:

        mugappu_count = int(mugappu_match.group(1))

        print("✔ Mugappu count detected →", mugappu_count)

        query = query.replace(mugappu_match.group(0), "")

    elif "mugappu" in query:

        mugappu_detected = True

        print("✔ Mugappu keyword detected")

        query = query.replace("mugappu", "").strip()

    
    # ------------------------------------------------
    # PRODUCT TYPE PHRASE DETECTION
    # ------------------------------------------------

    print("\n[STEP X] PRODUCT TYPE PHRASE DETECTION")

    if CATALOG_ENTITIES and "product_type" in CATALOG_ENTITIES:

        product_types = sorted(
            CATALOG_ENTITIES["product_type"],
            key=len,
            reverse=True
        )

        for ptype in product_types:

            # detect multi-word product types
            if " " in ptype and ptype in query:

                filters["product_type"] = ptype
                product_type_locked = True
                print("✔ Product type phrase match →", ptype)

                query = query.replace(ptype, "")
                break

    # ------------------------------------------------
    # FUZZY PRODUCT TYPE PHRASE DETECTION
    # ------------------------------------------------

    print("\n[STEP X] FUZZY PRODUCT TYPE PHRASE DETECTION")

    if "product_type" in CATALOG_ENTITIES and "product_type" not in filters:

        product_types = CATALOG_ENTITIES["product_type"]

        words = query.split()

        phrases = []

        for i in range(len(words) - 1):
            phrases.append(words[i] + " " + words[i+1])

        for phrase in phrases:

            match = get_close_matches(phrase, product_types, n=1, cutoff=0.7)

            if match:

                filters["product_type"] = match[0]

                print("✔ Fuzzy product type match →", match[0])

                query = query.replace(phrase, "")

                break

    # ------------------------------------------------
    # TOKENIZATION
    # ------------------------------------------------

    STOP_WORDS = {"under","below","above","over","with","of","for","in","on","and"}

    tokens = [
    t for t in query.split()
    if t not in STOP_WORDS and (len(t) > 1 or t in {"cz", "ad"})
]

    print("\n[STEP 5] Tokens:", tokens)

    # ------------------------------------------------
    # TOKEN PROCESSING
    # ------------------------------------------------

    for token in tokens:

        print("\nProcessing:", token)

        matched = False
        

       
        # -----------------------------------------
        # USAGE HELPER WORD SKIP
        # -----------------------------------------

        USAGE_STOP_WORDS = {"usage", "use", "wear"}

        if token in USAGE_STOP_WORDS:
            print("Skipping usage helper word:", token)
            matched = True
            continue

      

        # -----------------------------------------
        # USAGE INTENT DETECTION
        # -----------------------------------------

        # Exact match
        if token in USAGE_MAP:

            filters["usages"] = USAGE_MAP[token]

            print("✔ Usage intent detected →", filters["usages"])

            continue


        # Fuzzy match for misspellings
        usage_fuzzy = fuzzy_match(token, list(USAGE_MAP.keys()))

        if usage_fuzzy:

            filters["usages"] = USAGE_MAP[usage_fuzzy]

            print("✔ Fuzzy usage match →", filters["usages"])

            continue

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

            # -----------------------------------------
            # SKIP NUMERIC FIELDS (CONFIG DRIVEN)
            # -----------------------------------------
            if field in NUMERIC_FIELDS:
                print(f"Skipping numeric field → {field}")
                continue

            # prevent overwriting phrase-detected product_type
            if field == "product_type" and product_type_locked:
                continue
                    # prevent overwriting phrase-detected product_type
            if field == "product_type" and product_type_locked:
                continue

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
    # ------------------------------------------------
    # FINAL MUGAPPU LOGIC
    # ------------------------------------------------

    if mugappu_count is not None:

        if "product_type" in filters:

            filters["no_of_mugappu"] = mugappu_count

            print("✔ Mugappu count filter applied →", mugappu_count)

        else:

            filters["product_type"] = "mugappu"

            print("✔ Mugappu treated as product type")


    elif mugappu_detected:

        if "product_type" in filters:

            search_terms.append("mugappu")

            print("✔ Mugappu treated as search text")

        else:

            filters["product_type"] = "mugappu"

            print("✔ Mugappu treated as product type")

    search_text = " ".join(search_terms)

    print("\n================================================")
    print("INTENT RESULT")
    print("Search Text:", search_text)
    print("Filters:", filters)
    print("================================================")

    return search_text, filters
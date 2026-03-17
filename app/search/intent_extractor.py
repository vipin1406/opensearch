from difflib import get_close_matches
from metaphone import doublemetaphone
from app.search.entity_loader import load_catalog_entities
import re
from app.search.config import PURITY_MAP, GENDER_MAP, USAGE_MAP, NUMERIC_FIELDS

CATALOG_ENTITIES = None


def phonetic_code(word):
    return doublemetaphone(word)[0]


def fuzzy_match(token, values):
    values = [str(v) for v in values]
    match = get_close_matches(token, values, n=1, cutoff=0.7)
    return match[0] if match else None


def phonetic_match(token, values):
    token_ph = phonetic_code(token)
    for value in values:
        if phonetic_code(str(value)) == token_ph:
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
    detected_product_types = []

    mugappu_detected = False
    mugappu_count = None

    query = query.lower()

    # ------------------------------------------------
    # STEP 1 — PURITY DETECTION
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
    # STEP 2 — LAYER DETECTION
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
    # STEP 3 — WEIGHT DETECTION
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

        query = re.sub(r'(\d+)\s*(gm|g|gram|grams|graam|grm|grms)', '', query)

    # ------------------------------------------------
    # STEP 4 — LOAD ENTITIES
    # ------------------------------------------------
    if CATALOG_ENTITIES is None:
        print("\n[STEP 4] Loading catalog entities")
        CATALOG_ENTITIES = load_catalog_entities()

    # ------------------------------------------------
    # STEP 4B — MUGAPPU DETECTION (FUZZY + PHONETIC)
    # ------------------------------------------------
    print("\n[STEP 4B] MUGAPPU DETECTION")

    words = query.split()

    for i, word in enumerate(words):

        # 🔹 CHECK COUNT (number before word)
        if i > 0 and words[i - 1].isdigit():

            fuzzy = fuzzy_match(word, ["mugappu"])
            phonetic = phonetic_match(word, ["mugappu"])

            if fuzzy or phonetic:
                mugappu_count = int(words[i - 1])
                mugappu_detected = True

                print(f"✔ Mugappu count detected (fuzzy/phonetic) → {mugappu_count}")

                # remove both number + word
                query = query.replace(words[i - 1], "")
                query = query.replace(word, "")
                continue

        # 🔹 NORMAL DETECTION
        fuzzy = fuzzy_match(word, ["mugappu"])
        phonetic = phonetic_match(word, ["mugappu"])

        if fuzzy or phonetic:
            mugappu_detected = True
            print(f"✔ Mugappu detected (fuzzy/phonetic) → {word}")

            query = query.replace(word, "")

    print("[DEBUG] Query after mugappu cleanup →", query.strip())

    # ------------------------------------------------
    # STEP 5 — TOKENIZATION
    # ------------------------------------------------
    STOP_WORDS = {"under","below","above","over","with","of","for","in","on","and"}

    tokens = [
        t for t in query.split()
        if t not in STOP_WORDS and (len(t) > 1 or t in {"cz", "ad"})
    ]

    print("\n[STEP 5] Tokens:", tokens)

    # ------------------------------------------------
    # STEP 6 — TOKEN PROCESSING
    # ------------------------------------------------
    for token in tokens:

        print("\nProcessing:", token)

        matched = False

        if token in {"usage", "use", "wear"}:
            print("Skipping usage helper word:", token)
            continue

        if token in USAGE_MAP:
            filters["usages"] = USAGE_MAP[token]
            print("✔ Usage intent →", filters["usages"])
            continue

        usage_fuzzy = fuzzy_match(token, list(USAGE_MAP.keys()))
        if usage_fuzzy:
            filters["usages"] = USAGE_MAP[usage_fuzzy]
            print("✔ Fuzzy usage →", filters["usages"])
            continue

        if token in {"layer", "layers"}:
            filters["layers_range"] = 2
            print("✔ Layer keyword detected")
            continue

        if token in GENDER_MAP:
            filters["gender"] = GENDER_MAP[token]
            print("✔ Gender match", filters["gender"])
            continue

        for field, values in CATALOG_ENTITIES.items():

            if field in NUMERIC_FIELDS:
                continue

            if field == "product_type" and product_type_locked:
                continue

            # EXACT
            if token in values:
                if field == "product_type":
                    detected_product_types.append(token)
                    print("✔ Detected product_type →", token)
                else:
                    filters[field] = token
                    print("✔ Exact match", field)

                matched = True
                break

            # FUZZY
            fuzzy = fuzzy_match(token, values)
            if fuzzy:
                if field == "product_type":
                    detected_product_types.append(fuzzy)
                    print("✔ Fuzzy product_type →", fuzzy)
                else:
                    filters[field] = fuzzy
                    print("✔ Fuzzy match", field)

                matched = True
                break

            # PHONETIC
            phonetic = phonetic_match(token, values)
            if phonetic:
                if field == "product_type":
                    detected_product_types.append(phonetic)
                    print("✔ Phonetic product_type →", phonetic)
                else:
                    filters[field] = phonetic
                    print("✔ Phonetic match", field)

                matched = True
                break

        if not matched:
            search_terms.append(token)

    # ------------------------------------------------
    # STEP 7 — FINAL MUGAPPU LOGIC
    # ------------------------------------------------
    print("\n[STEP 7] FINAL MUGAPPU LOGIC")

    if mugappu_count is not None:
        if detected_product_types:
            filters["no_of_mugappu"] = mugappu_count
            print("✔ Mugappu count filter →", mugappu_count)
        else:
            detected_product_types.append("mugappu")

    elif mugappu_detected:
        if detected_product_types:
            search_terms.append("mugappu")
            print("✔ Mugappu as search text")
        else:
            detected_product_types.append("mugappu")

    # ------------------------------------------------
    # STEP 8 — FINAL PRODUCT TYPE RESOLUTION
    # ------------------------------------------------
    print("\n[STEP 8] PRODUCT TYPE RESOLUTION")
    print("Detected product types →", detected_product_types)

    if detected_product_types:

        main_product = detected_product_types[-1]
        filters["product_type"] = main_product

        print("✔ Final product_type →", main_product)

        for p in detected_product_types[:-1]:
            search_terms.append(p)
            print("✔ Added to search_text →", p)

    else:
        print("No product type detected")

    search_text = " ".join(search_terms)

    print("\n================================================")
    print("INTENT RESULT")
    print("Search Text:", search_text)
    print("Filters:", filters)
    print("================================================")

    return search_text, filters
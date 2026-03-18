from difflib import get_close_matches,SequenceMatcher
from metaphone import doublemetaphone
from app.search.entity_loader import load_catalog_entities
import re
from app.search.config import PURITY_MAP, GENDER_MAP, USAGE_MAP, NUMERIC_FIELDS
from app.search.normalizer import (
    normalize_purity,
    normalize_weight,
    normalize_weight_range,
    clean_query
)

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


def smart_match(token, values):

    print(f"\n[SMART MATCH] Processing token → {token}")

    token = str(token)
    values = [str(v) for v in values]

    best_match = None
    best_score = 0

    # ---------------------------------------
    # 1. EXACT MATCH
    # ---------------------------------------
    if token in values:
        print(f"[SMART MATCH] ✔ EXACT → {token}")
        return token, 1.0

    # ---------------------------------------
    # 2. PREFIX MATCH
    # ---------------------------------------
    for v in values:
        if len(token) >= 4 and v.startswith(token[:4]):
            score = SequenceMatcher(None, token, v).ratio()
            print(f"[SMART MATCH] ✔ PREFIX → {token} → {v} (score={score:.2f})")
            return v, score

    # ---------------------------------------
    # 3. LENGTH FILTER
    # ---------------------------------------
    filtered = [
        v for v in values
        if abs(len(v) - len(token)) <= 2
    ]

    print(f"[SMART MATCH] Length-filtered candidates → {filtered[:5]}...")

    # ---------------------------------------
    # 4. CONTROLLED FUZZY
    # ---------------------------------------
    matches = get_close_matches(token, filtered, n=3, cutoff=0.78)

    for m in matches:
        score = SequenceMatcher(None, token, m).ratio()

        if score > best_score:
            best_match = m
            best_score = score

    if best_match:
        print(f"[SMART MATCH] ✔ FUZZY → {token} → {best_match} (score={best_score:.2f})")
        return best_match, best_score

    # ---------------------------------------
    # 5. PHONETIC MATCH
    # ---------------------------------------
    token_ph = phonetic_code(token)

    for v in values:
        if phonetic_code(v) == token_ph:
            score = 0.75  # fixed confidence
            print(f"[SMART MATCH] ✔ PHONETIC → {token} → {v} (score={score})")
            return v, score

    # ---------------------------------------
    # 6. NO MATCH
    # ---------------------------------------
    print(f"[SMART MATCH] ✘ NO MATCH → {token}")
    return None, 0



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
    used_attribute_filters = set()

    mugappu_detected = False
    mugappu_count = None

    query = query.lower()

    # ------------------------------------------------
    # STEP 1 — PURITY DETECTION
    # ------------------------------------------------
    print("\n[STEP 1] PURITY DETECTION")

    query, purity = normalize_purity(query)

    if purity:
        filters["purity"] = purity

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
    # FINAL QUERY CLEANUP
    # ------------------------------------------------
    query = clean_query(query)
    print("[DEBUG] Clean query →", query)


    # ------------------------------------------------
    # STEP 4C — PRODUCT TYPE PHRASE DETECTION (SMART)
    # ------------------------------------------------
    print("\n[STEP 4C] PRODUCT TYPE PHRASE DETECTION")

    if "product_type" in CATALOG_ENTITIES:

        words = query.split()

        for i in range(len(words) - 1):

            phrase = words[i] + " " + words[i + 1]

            print(f"[STEP 4C] Checking phrase → {phrase}")

            match, score = smart_match(phrase, CATALOG_ENTITIES["product_type"])

            if match and score >= 0.75:
                detected_product_types.append(match)

                print(f"✔ Phrase match → {phrase} → {match} (score={score:.2f})")

                # 🔥 REMOVE FULL PHRASE SAFELY
                query = re.sub(rf'\b{phrase}\b', '', query)

                break

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
    # STEP 5B — WITH/WITHOUT ATTRIBUTE DETECTION
    # ------------------------------------------------

    print("\n[STEP 5B] WITH/WITHOUT DETECTION")

    ATTRIBUTE_MAP = {
        "stone": "stone_type",
        "pendant": "pendant"
    }

    words = query.split()

    i = 0
    while i < len(words):

        word = words[i]

        # -------------------------------
        # CASE 1: with kemp stone
        # -------------------------------
        if word == "with" and i + 2 < len(words):

            mid_word = words[i + 1]
            next_word = words[i + 2]

            if fuzzy_match(next_word, ["stone"]):

                stone_match = fuzzy_match(mid_word, CATALOG_ENTITIES.get("stone_type", []))

                if stone_match:
                    filters["stone_type"] = stone_match
                    used_attribute_filters.add("stone_type")
                    print(f"✔ Specific stone detected → {stone_match}")

                    query = query.replace(word, "")
                    query = query.replace(mid_word, "")
                    query = query.replace(next_word, "")

                    i += 3
                    continue

        # -------------------------------
        # CASE 2: with stone / without stone
        # -------------------------------
        if word in {"with", "without"} and i + 1 < len(words):

            next_word = words[i + 1]

            attr = fuzzy_match(next_word, ATTRIBUTE_MAP.keys())

            if attr:

                field = ATTRIBUTE_MAP[attr]

                if word == "with":
                    filters[field] = {"exists": True}
                    used_attribute_filters.add(field)
                    print(f"✔ WITH detected → {field} exists")

                else:
                    filters[field] = {"exists": False}
                    print(f"✔ WITHOUT detected → {field} missing")

                query = query.replace(word, "")
                query = query.replace(next_word, "")

                i += 2
                continue

        i += 1

    print("[DEBUG] Query after attribute cleanup →", query.strip())
    # 🔥 RE-TOKENIZE AFTER CLEANUP
    tokens = [
        t for t in query.split()
        if t not in STOP_WORDS and (len(t) > 1 or t in {"cz", "ad"})
]

    print("[STEP 5B] Tokens after cleanup:", tokens)

    

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

            # 🔥 SMART MATCH (replaces fuzzy + phonetic)
            match ,score = smart_match(token, values)

            if match and score >=0.75:
                
                if field == "product_type":
                    detected_product_types.append(match)
                    print("✔ Smart product_type →", match)
                else:
                    filters[field] = match
                    print("✔ Smart match", field)

                matched = True
                break
        if not matched:

            # 🔥 skip ONLY if attribute already used as filter
            if (
                token == "stone" and "stone_type" in used_attribute_filters
            ) or (
                token == "pendant" and "pendant" in used_attribute_filters
            ):
                print(f"⛔ Skipping attribute token (already used as filter) → {token}")
                continue

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
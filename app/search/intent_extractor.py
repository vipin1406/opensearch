from difflib import get_close_matches, SequenceMatcher
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

def extract_attributes(query):

    tokens = query.lower().split()
    filters = {}
    cleaned_tokens = []

    i = 0

    while i < len(tokens):

        token = tokens[i]

        # ==========================================
        # 🔥 1. WEIGHT (HIGHEST PRIORITY)
        # ==========================================

        if token.endswith("g") or token.endswith("gm"):
            number = token.replace("gm", "").replace("g", "")

            if number.isdigit():
                weight = int(number)

                filters["weight_range"] = {
                    "gte": max(0, weight - 2),
                    "lte": weight + 2
                }

                print(f"✔ Weight detected → {weight}g")

                i += 1
                continue

                # ==========================================
        # 🔥 SMART WEIGHT OPERATORS
        # ==========================================
        if token in {"under", "below", "above", "over"}:

            next_token = tokens[i+1] if i+1 < len(tokens) else ""
            next_unit = tokens[i+2] if i+2 < len(tokens) else ""

            if next_token.isdigit() and next_unit in {"gram", "grams", "gm", "g"}:

                weight = int(next_token)

                if token in {"under", "below"}:
                    filters["weight_range"] = {
                        "lte": weight
                    }

                elif token in {"above", "over"}:
                    filters["weight_range"] = {
                        "gte": weight
                    }

                print(f"✔ Smart weight detected → {filters['weight_range']}")

                i += 3
                continue


        # ==========================================
        # 🔥 NORMAL WEIGHT
        # ==========================================
        if token.isdigit():
            next_word = tokens[i+1] if i+1 < len(tokens) else ""

            # sovereign handling
            if next_word in {"sovereign", "sovereigns", "pavan", "pavans"}:
                grams = int(token) * 8

                filters["weight_range"] = {
                    "gte": max(0, grams - 2),
                    "lte": grams + 2
                }

                print(f"✔ Sovereign detected → {grams}g")

                i += 2
                continue

            # normal gram handling
            if next_word in {"gram", "grams", "gm", "g"}:
                weight = int(token)

                filters["weight_range"] = {
                    "gte": max(0, weight - 2),
                    "lte": weight + 2
                }

                print(f"✔ Weight detected → {weight}g")

                i += 2
                continue

        # ==========================================
        # 🔥 2. PURITY
        # ==========================================

        if token.endswith("k") or token.endswith("kt"):
            number = token.replace("k", "").replace("t", "")

            if number in PURITY_MAP:
                filters["purity"] = PURITY_MAP[number]
                print(f"✔ Purity detected → {filters['purity']}")

                i += 1
                continue

        if token.isdigit() and token in PURITY_MAP:
            next_word = tokens[i+1] if i+1 < len(tokens) else ""

            if next_word in {"karat", "carat", "kt", "k", "purity"}:
                filters["purity"] = PURITY_MAP[token]
                print(f"✔ Purity detected → {filters['purity']}")

                i += 2
                continue

        # ==========================================
        # 🔥 3. CLEANUP
        # ==========================================

        if token in {
            "gram", "grams", "gm", "g",
            "sovereign", "sovereigns","savaran",
            "sevaran","pown","pavan","powen",
            "pavan", "pavans"
        }:
            i += 1
            continue

        cleaned_tokens.append(token)
        i += 1

    clean_query = " ".join(cleaned_tokens)

    return clean_query, filters

COMPOUND_MAP = None

def load_compound_map():
    global COMPOUND_MAP

    if COMPOUND_MAP is None:
        import json
        with open("app/config/compound_map.json") as f:
            COMPOUND_MAP = json.load(f)

    return COMPOUND_MAP


CATALOG_ENTITIES = None

import json

def load_rules():
    with open("app/config/rules.json") as f:
        return json.load(f)["rules"]

def apply_rules(tokens):

    rules = load_rules()

    # ==========================================
    # 🔥 FIX: APPLY LONGER RULES FIRST
    # ==========================================
    rules = sorted(rules, key=lambda r: len(r["conditions"]), reverse=True)

    filters = {}
    boost_terms = []

    for rule in rules:

        conditions = rule["conditions"]

        # check if all conditions match
        if all(c in tokens for c in conditions):

            print(f"[RULE ENGINE] Matched → {rule['name']}")

            actions = rule.get("actions", {})

            # apply filters
            if "filters" in actions:
                filters.update(actions["filters"])

            # apply boost
            if "boost_terms" in actions:
                boost_terms.extend(actions["boost_terms"])

            # remove tokens
            if "remove_tokens" in actions:
                tokens = [t for t in tokens if t not in actions["remove_tokens"]]

    return tokens, filters, boost_terms

def phonetic_code(word):
    return doublemetaphone(word)[0]


def fuzzy_match(token, values):
    values = [str(v) for v in values]
    match = get_close_matches(token, values, n=1, cutoff=0.8)
    return match[0] if match else None


def phonetic_match(token, values):
    token_ph = phonetic_code(token)
    for value in values:
        if phonetic_code(str(value)) == token_ph:
            return value
    return None


def smart_match(token, candidates):

    print(f"[SMART MATCH] Processing token → {token}")

    token_clean = token.strip().lower()

    # ==========================================
    # 🔥 FIX 1: GLOBAL ENTITY PROTECTION
    # ==========================================
    all_entities = []

    for values in CATALOG_ENTITIES.values():
        if values:
            all_entities.extend([str(v).strip().lower() for v in values])

    if token_clean in all_entities:
        print(f"[SMART MATCH] 🛑 GLOBAL EXACT MATCH → {token_clean}")
        return token_clean, 1.0

    # ==========================================
    # 🔄 NORMAL FLOW (FIELD-LEVEL MATCH)
    # ==========================================
    normalized_candidates = [str(c).strip().lower() for c in candidates]

    best_match = None
    best_score = 0

    for candidate in normalized_candidates:
        score = SequenceMatcher(None, token_clean, candidate).ratio()

        if score > best_score:
            best_score = score
            best_match = candidate

    if best_score >= 0.80:
        print(f"[SMART MATCH] ✔ FUZZY → {token_clean} → {best_match} (score={best_score:.2f})")
        return best_match, best_score

    print(f"[SMART MATCH] ✘ NO MATCH → {token_clean}")
    return token_clean, 0.0


def extract_numeric_filters(tokens, filters):
    """
    Extract numeric-based filters like mugappu, weight, layers
    """

    updated_tokens = []
    i = 0

    while i < len(tokens):
        token = tokens[i]

        # -------------------------------
        # HANDLE NUMBERS
        # -------------------------------
        if token.isdigit():
            value = int(token)

            # Look ahead
            if i + 1 < len(tokens):
                next_token = tokens[i + 1]

                # 🔥 MUGAPPU LOGIC
                if next_token == "mugappu":
                    filters["no_of_mugappu"] = {
                        "gte": value
                    }
                    print(f"✔ Extracted mugappu filter → >= {value}")
                    i += 2
                    continue

                # 🔥 WEIGHT LOGIC (future ready)
                elif next_token in ["gram", "g", "grams"]:
                    filters["weight_value"] = value
                    print(f"✔ Extracted weight filter → {value}g")
                    i += 2
                    continue

                # 🔥 LAYERS LOGIC (future)
                elif next_token in ["layer", "layers"]:
                    filters["layers_range"] = value
                    print(f"✔ Extracted layers filter → >= {value}")
                    i += 2
                    continue

        # keep token if not consumed
        updated_tokens.append(token)
        i += 1

    return updated_tokens, filters

def extract_purity(query, filters):

    tokens = query.lower().split()

    i = 0

    while i < len(tokens):

        token = tokens[i]

        # case: 22k / 22kt
        if token.endswith("k") or token.endswith("kt"):
            number = token.replace("k", "").replace("t", "")

            if number in PURITY_MAP:
                filters["purity"] = PURITY_MAP[number]
                print("✔ Purity detected →", filters["purity"])

                tokens.pop(i)
                continue

        # case: 22 karat / 22 kt / 22 purity
        if token.isdigit() and token in PURITY_MAP:

            next_word = tokens[i+1] if i+1 < len(tokens) else ""

            if next_word in ["karat", "carat", "kt", "k", "purity"]:
                filters["purity"] = PURITY_MAP[token]
                print("✔ Purity detected →", filters["purity"])

                tokens.pop(i)
                tokens.pop(i)
                continue

        i += 1

    query = " ".join(tokens)

    return query, filters

def extract_intent(query):

    global CATALOG_ENTITIES

    print("\n================================================")
    print("INTENT EXTRACTION STARTED")
    print("================================================")

    print("\nIncoming Query:", query)

    filters = {}
    search_terms = []
    used_attribute_filters = set()

    mugappu_detected = False
    mugappu_count = None
    # 🔥 FIX: handle purity BEFORE anything else
    query, filters = extract_purity(query, filters)
    query = query.lower()

    # STEP 1 — PURITY
    query, purity = normalize_purity(query)
    if purity:
        filters["purity"] = purity

    '''
    # STEP 1A — PURITY MAP BACKUP
    for word in query.split():
        if word in PURITY_MAP:
            filters["purity"] = PURITY_MAP[word]
            query = query.replace(word, "")
            print(f"✔ Purity detected (map) → {filters['purity']}")
            break
    '''
    '''
    # STEP 1B — METAL
    METALS = ["gold", "silver"]
    for word in query.split():
        if word in METALS:
            filters["metal"] = word
            #query = query.replace(word, "")
            break
    '''
    # STEP — GENDER
    for word in query.split():
        if word in GENDER_MAP:
            filters["gender"] = GENDER_MAP[word]
            query = query.replace(word, "")
            print(f"✔ Gender detected → {filters['gender']}")
            break
            

    # STEP 2 — LAYER
    match = re.search(r"(\d+)\s*layer", query)
    if match:
        val = int(match.group(1))
        if val >= 4:
            filters["layers_range"] = val
        else:
            filters["layers"] = val
        query = query.replace(match.group(0), "")
    
    # STEP — USAGE (daily wear, wedding, office etc.)
    for word in query.split():
        if word in USAGE_MAP:
            filters["usage"] = USAGE_MAP[word]
            query = query.replace(word, "")
            print(f"✔ Usage detected → {filters['usage']}")
            break

    # STEP 3 — WEIGHT
    sovereign_match = re.search(r'(under|below|above|over)?\s*(\d+)\s*sovereign', query)
    if sovereign_match:
        cond = sovereign_match.group(1)
        grams = int(sovereign_match.group(2)) * 8

        if cond in ["under", "below"]:
            filters["weight_range"] = {"lte": grams}
        elif cond in ["above", "over"]:
            filters["weight_range"] = {"gte": grams}
        else:
            filters["weight_value"] = grams

        query = query.replace(sovereign_match.group(0), "")

    # STEP 4 — LOAD ENTITIES
    if CATALOG_ENTITIES is None:
        CATALOG_ENTITIES = load_catalog_entities()

    # CLEAN
    query = clean_query(query)

    # STEP 5 — TOKENIZATION
    STOP_WORDS = {"under","below","above","over","with","of","for","in","on","and"}

    tokens = [
        t for t in query.split()
        if t not in STOP_WORDS and (len(t) > 1 or t.isdigit() or t in {"cz", "ad"})
    ]
    # ==========================================
    # 🔥 APPLY RULE ENGINE (ADD THIS BLOCK)
    # ==========================================
    tokens, rule_filters, boost_terms = apply_rules(tokens)

    # merge rule filters into main filters
    filters.update(rule_filters)

    print(f"[RULE ENGINE] Final tokens → {tokens}")
    print(f"[RULE ENGINE] Filters → {filters}")
    print(f"[RULE ENGINE] Boost → {boost_terms}")


    compound_map = load_compound_map()
    query_text = " ".join(tokens)

    # 🔥 check full phrase
    if query_text in compound_map:
        mapped_type = compound_map[query_text]

        print(f"🔥 COMPOUND DETECTED → {query_text} → {mapped_type}")

        # remove product_type filter if exists
        filters.pop("product_type", None)

        # instead use as boost
        boost_terms.append(mapped_type)

    tokens, filters = extract_numeric_filters(tokens, filters)

    # -------------------------
    # ML LOGGING
    # -------------------------
    original_tokens = tokens.copy()
    corrections = []

    # STEP 5D — NORMALIZATION
    normalized_tokens = []
    did_you_mean_tokens = []
    scores = []
    correction_applied = False

    for token in tokens:

        match, score = smart_match(token, CATALOG_ENTITIES.get("product_type", []))

        if match and score >= 0.80:

            normalized_tokens.append(match)
            did_you_mean_tokens.append(match)
            scores.append(score)

            if match != token:
                correction_applied = True

                corrections.append({
                    "from": token,
                    "to": match,
                    "score": round(score, 2)
                })

        else:
            normalized_tokens.append(token)
            did_you_mean_tokens.append(token)
            scores.append(0.3)

    # DO NOT overwrite tokens completely
    # tokens = normalized_tokens  ❌ REMOVE THIS

    tokens = [
        normalized_tokens[i] if not original_tokens[i].isdigit()
        else original_tokens[i]
        for i in range(len(normalized_tokens))
    ]

    # STEP 5F — CONFIDENCE
    token_confidence = sum(scores) / len(scores) if scores else 1.0

    if any(t in CATALOG_ENTITIES["product_type"] for t in tokens):
        structure_score = 1.0
    else:
        structure_score = 0.2

    base_confidence = (
        token_confidence * 0.7 +
        structure_score * 0.3
    )

    # ATTRIBUTE SCORE
    important_attributes = ["metal", "purity", "stone_type", "gender", "weight_range"]
    detected = sum(1 for k in filters if k in important_attributes)
    attribute_score = detected / len(important_attributes)
    
    # ==========================================
    # 🔥 INTELLIGENT DEFAULT BUSINESS BOOST
    # ==========================================
    search_preview = " ".join(tokens).strip()

    CATEGORY_DEFAULT_BOOST = {
        "earring": {"metal": "gold", "purity": "22k"},
        "earrings": {"metal": "gold", "purity": "22k"},
        "ring": {"metal": "gold", "purity": "22k"},
        "rings": {"metal": "gold", "purity": "22k"},
        "chain": {"metal": "gold", "purity": "22k"},
        "necklace": {"metal": "gold", "purity": "22k"},
        "metti": {"metal": "silver"}
    }

    if (
        search_preview in CATEGORY_DEFAULT_BOOST
        and "metal" not in filters
        and "purity" not in filters
    ):
        defaults = CATEGORY_DEFAULT_BOOST[search_preview]

        if "metal" in defaults:
            boost_terms.append(defaults["metal"])

        if "purity" in defaults:
            boost_terms.append(defaults["purity"])

        print(f"✔ Intelligent category boost → {defaults}")

    # FINAL TEXT
    search_text = " ".join(tokens)

    normalized_tokens = tokens.copy()

    did_you_mean = None
    if correction_applied:
        did_you_mean = " ".join(did_you_mean_tokens)

    print("\n================================================")
    print("INTENT RESULT")
    print("Search Text:", search_text)
    print("Filters:", filters)
    print("================================================")

    return {
        "search_text": search_text,
        "filters": filters,
        "boost_terms": boost_terms,
        "did_you_mean": did_you_mean,
        "base_confidence": base_confidence,
        "attribute_score": attribute_score,

        # ML DATA
        "original_tokens": original_tokens,
        "normalized_tokens": normalized_tokens,
        "corrections": corrections
    }
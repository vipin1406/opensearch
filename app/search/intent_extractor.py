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


CATALOG_ENTITIES = None


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


def smart_match(token, values):

    print(f"\n[SMART MATCH] Processing token → {token}")

    token = str(token)
    values = [str(v) for v in values]

    best_match = None
    best_score = 0

    if token in values:
        print(f"[SMART MATCH] ✔ EXACT → {token}")
        return token, 1.0

    for v in values:
        if len(token) >= 4 and v.startswith(token[:4]):
            score = SequenceMatcher(None, token, v).ratio()
            print(f"[SMART MATCH] ✔ PREFIX → {token} → {v} (score={score:.2f})")
            return v, score

    filtered = [
        v for v in values
        if abs(len(v) - len(token)) <= 2
    ]

    print(f"[SMART MATCH] Length-filtered candidates → {filtered[:5]}...")

    matches = get_close_matches(token, filtered, n=3, cutoff=0.80)

    for m in matches:
        score = SequenceMatcher(None, token, m).ratio()

        if score > best_score:
            best_match = m
            best_score = score

    if best_match:
        print(f"[SMART MATCH] ✔ FUZZY → {token} → {best_match} (score={best_score:.2f})")
        return best_match, best_score

    print(f"[SMART MATCH] ✘ NO MATCH → {token}")
    return None, 0



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

    query = query.lower()

    # STEP 1 — PURITY
    query, purity = normalize_purity(query)
    if purity:
        filters["purity"] = purity

    # STEP 1A — PURITY MAP BACKUP
    for word in query.split():
        if word in PURITY_MAP:
            filters["purity"] = PURITY_MAP[word]
            query = query.replace(word, "")
            print(f"✔ Purity detected (map) → {filters['purity']}")
            break

    # STEP 1B — METAL
    METALS = ["gold", "silver"]
    for word in query.split():
        if word in METALS:
            filters["metal"] = word
            query = query.replace(word, "")
            break
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

    # ---------------------------------------
    # 🔥 NUMERIC FILTER EXTRACTION (ADD HERE)
    # ---------------------------------------

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
        "did_you_mean": did_you_mean,
        "base_confidence": base_confidence,
        "attribute_score": attribute_score,

        # ML DATA
        "original_tokens": original_tokens,
        "normalized_tokens": normalized_tokens,
        "corrections": corrections
    }
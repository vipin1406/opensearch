from difflib import get_close_matches, SequenceMatcher
from app.search.entity_loader import load_catalog_entities

FIELD_PRIORITY = {
    "product_type": 4,
    "metal": 3,
    "stone_type": 2,
    "usages": 1
}


import json
import os

SPELL_MAP_PATH = "app/config/spell_map.json"


def load_spell_map():
    if not os.path.exists(SPELL_MAP_PATH):
        return {}

    with open(SPELL_MAP_PATH, "r") as f:
        return json.load(f)
    
def apply_spell_mapping(query, spell_map):

    print("\n========== SPELL MAP ==========")

    tokens = query.lower().split()
    corrected = []

    for t in tokens:
        if t in spell_map:
            print(f"[SPELL MAP] {t} → {spell_map[t]}")
            corrected.append(spell_map[t])
        else:
            corrected.append(t)

    final_query = " ".join(corrected)

    print("Mapped Query:", final_query)
    print("================================\n")

    return final_query
    

def get_edit_distance(a, b):
    return abs(len(a) - len(b))


def generate_candidates(token):
    print(f"\n[CORRECTION] Processing token → {token}")

    candidates = []
    entities = load_catalog_entities()
    for field, values in entities.items():
        # 🔥 SKIP NON-STRING FIELDS (FIX)
        if not values or not isinstance(values[0], str):
            continue

      
        print(f"→ Checking field: {field}")

        matches = get_close_matches(token, values, n=3, cutoff=0.7)

        for m in matches:
            sim = SequenceMatcher(None, token, m).ratio()

            if sim < 0.75:
                print(f"   ✘ Weak match → {m} (sim={sim:.2f})")
                continue

            candidate = {
                "value": m,
                "field": field,
                "similarity": sim,
                "field_priority": FIELD_PRIORITY.get(field, 1),
                "length": len(m),
                "prefix": m.startswith(token[:2]),
                "edit_distance": get_edit_distance(token, m)
            }

            # ==========================================
            # 🔥 NEW SCORING (BALANCED)
            # ==========================================

            # 1. EXACT MATCH BOOST (absolute priority)
            exact_match = 1 if token == m else 0

            # 2. SIMILARITY (main factor)
            similarity_score = sim * 5   # ↑ increased weight

            # 3. FIELD PRIORITY (reduced influence)
            field_score = candidate["field_priority"] * 0.5

            # 4. PREFIX BONUS
            prefix_score = 0.3 if candidate["prefix"] else 0

            # 5. EDIT DISTANCE PENALTY
            distance_penalty = candidate["edit_distance"] * 0.2

            candidate["score"] = (
                (exact_match * 100) +     # 🔥 dominates everything
                similarity_score +
                field_score +
                prefix_score -
                distance_penalty
            )
            print(
                f"   ✔ Candidate → {m} | field={field} | "
                f"sim={sim:.2f} | score={candidate['score']:.2f}"
            )

            candidates.append(candidate)

    return candidates


def pick_best_candidate(token):
    candidates = generate_candidates(token)

    if not candidates:
        print(f"[CORRECTION] ✘ No candidates → {token}")
        return token, None

    candidates.sort(
        key=lambda x: (
            x["score"],
            x["length"],
            x["prefix"],
            -x["edit_distance"],
            x["field_priority"]
        ),
        reverse=True
    )

    print("\n[CORRECTION] Sorted candidates:")
    for c in candidates[:3]:
        print(
            f"   {c['value']} ({c['field']}) "
            f"score={c['score']:.2f}"
        )

    best = candidates[0]

    # 🔥 SAFETY GUARD
    if best["similarity"] < 0.80:
        print(f"[CORRECTION] ✘ Rejected (low confidence) → {token}")
        return token, None

    print(
        f"[CORRECTION] ✅ Selected → {token} → "
        f"{best['value']} ({best['field']})"
    )

    return best["value"], best["field"]


def apply_correction(query):
    print("\n========== CORRECTION LAYER ==========")
    print(f"Original Query → {query}")

    tokens = query.lower().split()

    final_tokens = []

    for token in tokens:
        corrected, field = pick_best_candidate(token)
        final_tokens.append(corrected)

    final_query = " ".join(final_tokens)

    print(f"Final Corrected Query → {final_query}")
    print("======================================\n")

    return final_query
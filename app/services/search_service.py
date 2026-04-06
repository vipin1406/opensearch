from opensearchpy import OpenSearch
from app.search.intent_extractor import extract_intent
from app.search.query_builder import build_search_query
import json
from datetime import datetime

INDEX_NAME = "jewellery_products"

client = OpenSearch(
    hosts=[{"host": "opensearch", "port": 9200}]
)


def calculate_weight_tolerance(weight):
    if weight < 10:
        return 1
    elif weight < 30:
        return 2
    elif weight < 80:
        return 4
    else:
        return 6


def apply_weight_range(filters):
    filters = filters.copy()

    if "weight_value" not in filters:
        return filters

    weight = filters["weight_value"]
    tolerance = calculate_weight_tolerance(weight)

    filters["weight_range"] = {
        "gte": max(0, weight - tolerance),
        "lte": weight + tolerance
    }

    del filters["weight_value"]
    return filters


def search_products(query):

    print("\n================================================")
    print("SEARCH SERVICE STARTED")
    print("================================================")

    print("\n[INPUT] Query:", query)

    # 🔥 STEP 0 — CORRECTION
    from app.search.correction import apply_correction
    query = apply_correction(query)
    print("[CORRECTED QUERY]:", query)

    # ------------------------------------------------
    # STEP 1 — INTENT EXTRACTION
    # ------------------------------------------------
    intent_data = extract_intent(query)

    search_text = intent_data["search_text"]
    filters = intent_data["filters"]
    did_you_mean = intent_data["did_you_mean"]
    base_confidence = intent_data["base_confidence"]
    attribute_score = intent_data["attribute_score"]

    # ML fields
    original_tokens = intent_data["original_tokens"]
    normalized_tokens = intent_data["normalized_tokens"]
    corrections = intent_data["corrections"]

    # defaults
    final_confidence = base_confidence
    quality = "GOOD"
    boost_signals = {}

    # ------------------------------------------------
    # STEP 2 — APPLY WEIGHT RANGE
    # ------------------------------------------------
    filters = apply_weight_range(filters)

    # ------------------------------------------------
    # 🚫 STOP IF QUERY BECOMES EMPTY
    # ------------------------------------------------
    if not search_text.strip() and not filters:
        print("🚫 EMPTY QUERY → RETURNING NO RESULTS")

        return {
            "results": [],
            "did_you_mean": did_you_mean,
            "confidence": 0.0,
            "quality": "WORST",
            "mode": "manual"
        }

    # ------------------------------------------------
    # STEP 3 — BUILD QUERY
    # ------------------------------------------------
    query_body = build_search_query(search_text, filters, boost_signals)

    print("\n[SEARCH] Executing search")

    try:
        response = client.search(index=INDEX_NAME, body=query_body)
    except Exception as e:
        print("[ERROR] Search failed:", e)
        return []

    hits = response["hits"]["hits"]
    results_count = len(hits)

    # ------------------------------------------------
    # 🚫 STRICT: NO RESULTS → RETURN EMPTY
    # ------------------------------------------------
    if results_count == 0:
        print("🚫 NO RESULTS FOUND → RETURNING EMPTY")

        return {
            "results": [],
            "did_you_mean": did_you_mean,
            "confidence": 0.0,
            "quality": "WORST",
            "mode": "manual"
        }

    # ------------------------------------------------
    # STEP 4 — SCORING
    # ------------------------------------------------
    top_score = hits[0]["_score"]
    os_score = min(top_score / 100, 1.0)

    if results_count > 20:
        result_count_score = 1.0
    elif results_count > 5:
        result_count_score = 0.7
    else:
        result_count_score = 0.4

    final_confidence = (
        base_confidence * 0.4 +
        attribute_score * 0.2 +
        os_score * 0.25 +
        result_count_score * 0.15
    )

    # ------------------------------------------------
    # QUALITY
    # ------------------------------------------------
    if final_confidence >= 0.85:
        quality = "BEST"
    elif final_confidence >= 0.7:
        quality = "GOOD"
    else:
        quality = "WORST"

    # ------------------------------------------------
    # RESULTS
    # ------------------------------------------------
    results = [hit["_source"] for hit in hits]

    # ------------------------------------------------
    # 🔥 ML LOGGING
    # ------------------------------------------------
    ml_log = {
        "timestamp": datetime.utcnow().isoformat(),
        "query": query,
        "tokens": original_tokens,
        "corrections": corrections,
        "normalized_query": search_text,
        "normalized_tokens": normalized_tokens,
        "entities": filters,
        "features": {
            "token_confidence": round(base_confidence, 2),
            "attribute_score": round(attribute_score, 2),
            "os_score": round(os_score, 2),
            "result_count": results_count,
            "num_tokens": len(original_tokens),
            "num_entities": len(filters)
        },
        "result_info": {
            "top_score": top_score,
            "quality": quality,
            "mode": "manual"
        }
    }

    print("\n========== ML LOG ==========")
    print(json.dumps(ml_log, indent=2))
    print("============================\n")

    with open("ml_logs.jsonl", "a") as f:
        f.write(json.dumps(ml_log) + "\n")

    print("\n================================================")
    print("SEARCH SERVICE FINISHED")
    print("================================================\n")

    return {
        "results": results,
        "did_you_mean": did_you_mean,
        "confidence": round(final_confidence, 2),
        "quality": quality,
        "mode": "manual"
    }
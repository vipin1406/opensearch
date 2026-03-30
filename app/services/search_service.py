from opensearchpy import OpenSearch
from app.search.intent_extractor import extract_intent
from app.search.query_builder import build_search_query

INDEX_NAME = "jewellery_products"

client = OpenSearch(
    hosts=[{"host": "opensearch", "port": 9200}]
)


def calculate_weight_tolerance(weight):

    print("\n[WEIGHT] Calculating tolerance")

    if weight < 10:
        return 1
    elif weight < 30:
        return 2
    elif weight < 80:
        return 4
    else:
        return 6


def apply_weight_range(filters):

    print("\n[WEIGHT] Applying weight range logic")

    filters = filters.copy()

    if "weight_value" not in filters:
        print("[WEIGHT] No weight_value found")
        return filters

    weight = filters["weight_value"]

    tolerance = calculate_weight_tolerance(weight)

    filters["weight_range"] = {
        "gte": max(0, weight - tolerance),
        "lte": weight + tolerance
    }

    del filters["weight_value"]

    print("[WEIGHT] Weight Range:", filters["weight_range"])

    return filters


def detect_conflicting_filter(search_text, filters):

    print("\n[RELAXATION] Detecting conflicting filter")

    PROTECTED_FILTERS = {"product_type"}

    for key in list(filters.keys()):

        if key in PROTECTED_FILTERS:
            print(f"[RELAXATION] Skipping protected filter → {key}")
            continue

        test_filters = filters.copy()
        del test_filters[key]

        print(f"[RELAXATION] Testing without filter → {key}")

        query_body = build_search_query(search_text, test_filters)

        try:
            response = client.search(index=INDEX_NAME, body=query_body)
        except Exception as e:
            print("[RELAXATION] Search error:", e)
            continue

        hits = response["hits"]["hits"]

        print(f"[RELAXATION] Results without {key}: {len(hits)}")

        if hits:
            print(f"[RELAXATION] Conflicting filter detected → {key}")
            return key

    print("[RELAXATION] No removable conflicting filter found")

    return None


def search_products(query):

    print("\n================================================")
    print("SEARCH SERVICE STARTED")
    print("================================================")

    print("\n[INPUT] Query:", query)

    # ------------------------------------------------
    # STEP 1 — INTENT EXTRACTION
    # ------------------------------------------------

    search_text, filters = extract_intent(query)
    boost_signals = {}

    print("\n[INTENT RESULT]")
    print("Search Text:", search_text)
    print("Filters:", filters)

    # ------------------------------------------------
    # STEP 2 — APPLY WEIGHT RANGE
    # ------------------------------------------------

    filters = apply_weight_range(filters)

    print("\n[FILTERS AFTER WEIGHT LOGIC]")
    print(filters)

    # ------------------------------------------------
    # STEP 3 — BUILD QUERY
    # ------------------------------------------------

    query_body = build_search_query(search_text, filters, boost_signals)

    print("\n[SEARCH] Executing initial search")

    try:
        response = client.search(index=INDEX_NAME, body=query_body)
    except Exception as e:
        print("[ERROR] Search failed:", e)
        return []

    hits = response["hits"]["hits"]

    print("[SEARCH] Initial results:", len(hits))
    # ------------------------------------------------
    # DEBUG — PRINT SCORES (EXACT PLACE)
    # ------------------------------------------------

    print("\n========== SEARCH SCORES ==========")

    for i, hit in enumerate(hits[:10]):  # top 10 results

        source = hit["_source"]
        score = hit["_score"]

        print(f"{i+1}. Score: {score:.4f}")

        print("   Name:", source.get("product_name"))

        if "product_type" in source:
            print("   Type:", source.get("product_type"))

        if "metal" in source:
            print("   Metal:", source.get("metal"))

        if "purity" in source:
            print("   Purity:", source.get("purity"))

        print("----------------------------------")

    print("==================================\n")

    # ------------------------------------------------
    # STEP 4 — FILTER RELAXATION
    # ------------------------------------------------

    if len(hits) == 0 and filters:

        print("\n[RELAXATION] Zero results → detecting conflicting filter")

        conflicting_filter = detect_conflicting_filter(search_text, filters)

        if conflicting_filter:

            print("[RELAXATION] Removing filter:", conflicting_filter)

            # ---------------------------------------
            # 🔥 CONVERT FILTER → BOOST SIGNAL
            # ---------------------------------------

            value = filters.pop(conflicting_filter)

            boost_key = f"user_{conflicting_filter}"
            boost_signals[boost_key] = value

            print(f"🎯 Converted {conflicting_filter} → boost:", value)

            # ---------------------------------------
            # REBUILD QUERY WITH BOOST SIGNALS
            # ---------------------------------------

            query_body = build_search_query(search_text, filters, boost_signals)

            print("[RELAXATION] Re-running search after converting to boost")

            response = client.search(index=INDEX_NAME, body=query_body)

            hits = response["hits"]["hits"]

            print("[RELAXATION] Results after relaxation:", len(hits))

            print("[RELAXATION] Re-running search after removing filter")

            response = client.search(index=INDEX_NAME, body=query_body)

            hits = response["hits"]["hits"]

            print("[RELAXATION] Results after relaxation:", len(hits))

    # ------------------------------------------------
    # STEP 5 — PRODUCT TYPE FALLBACK
    # ------------------------------------------------

    if len(hits) == 0 and "product_type" in filters:

        print("\n[FALLBACK] Product type fallback activated")

        product_filter = {
            "product_type": filters["product_type"]
        }

        query_body = build_search_query("", product_filter)

        response = client.search(index=INDEX_NAME, body=query_body)

        hits = response["hits"]["hits"]

        print("[FALLBACK] Product type fallback results:", len(hits))

    # ------------------------------------------------
    # STEP 6 — POPULAR PRODUCTS FALLBACK
    # ------------------------------------------------

    if len(hits) == 0:

        print("\n[FALLBACK] Nothing matched → returning popular products")

        query_body = {
            "size": 20,
            "query": {
                "match_all": {}
            }
        }

        response = client.search(index=INDEX_NAME, body=query_body)

        hits = response["hits"]["hits"]

        print("[FALLBACK] Popular products returned:", len(hits))

    # ------------------------------------------------
    # STEP 7 — FINAL RESULTS
    # ------------------------------------------------

    results = [hit["_source"] for hit in hits]

    print("\n[FINAL RESULT COUNT]", len(results))

    print("\n================================================")
    print("SEARCH SERVICE FINISHED")
    print("================================================\n")

    return results
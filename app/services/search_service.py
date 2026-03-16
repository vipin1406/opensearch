from opensearchpy import OpenSearch
from app.search.intent_extractor import extract_intent
from app.search.query_builder import build_search_query

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

    print("Weight Range:", filters["weight_range"])

    return filters


def detect_conflicting_filter(search_text, filters):

    print("\nDetecting conflicting filter")

    PROTECTED_FILTERS = {"product_type"}

    for key in list(filters.keys()):

        # Do not remove protected filters
        if key in PROTECTED_FILTERS:
            print(f"Skipping protected filter → {key}")
            continue

        test_filters = filters.copy()
        del test_filters[key]

        print(f"Testing without filter → {key}")

        query_body = build_search_query(search_text, test_filters)

        try:
            response = client.search(index=INDEX_NAME, body=query_body)
        except Exception as e:
            print("Search error:", e)
            continue

        hits = response["hits"]["hits"]

        if hits:
            print(f"Conflicting filter detected → {key}")
            return key

    print("No removable conflicting filter found")

    return None


def search_products(query):

    print("\n================================================")
    print("SEARCH SERVICE STARTED")
    print("================================================")

    search_text, filters = extract_intent(query)

    filters = apply_weight_range(filters)

    query_body = build_search_query(search_text, filters)

    print("\nExecuting search")

    try:
        response = client.search(index=INDEX_NAME, body=query_body)
    except Exception as e:
        print("Search error:", e)
        return []

    hits = response["hits"]["hits"]

    print("Results:", len(hits))

    # -----------------------------------------
    # DETECT CONFLICTING FILTER
    # -----------------------------------------

    if len(hits) == 0 and filters:

        print("\nZero results → detecting conflicting filter")

        conflicting_filter = detect_conflicting_filter(search_text, filters)

        if conflicting_filter:

            print("Removing filter:", conflicting_filter)

            del filters[conflicting_filter]

            query_body = build_search_query(search_text, filters)

            response = client.search(index=INDEX_NAME, body=query_body)

            hits = response["hits"]["hits"]

            print("Results after relaxation:", len(hits))

    # -----------------------------------------
    # FINAL TEXT FALLBACK
    # -----------------------------------------

    if len(hits) == 0:

        print("\nFinal fallback → text search only")

        product_filter = {
        "product_type": filters["product_type"]
    }


        query_body = build_search_query("",product_filter)

        response = client.search(index=INDEX_NAME, body=query_body)

        hits = response["hits"]["hits"]

        print("Fallback results:", len(hits))

    # -----------------------------------------
    # NOTHING MATCHED FALLBACK
    # -----------------------------------------

    if len(hits) == 0:

        print("\nNothing matched → returning popular products")

        query_body = {
            "size": 20,
            "query": {
                "match_all": {}
            }
        }

        response = client.search(index=INDEX_NAME, body=query_body)

        hits = response["hits"]["hits"]

        print("Popular products returned:", len(hits))

    results = [hit["_source"] for hit in hits]

    print("\nSEARCH FINISHED\n")

    return results
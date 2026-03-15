from opensearchpy import OpenSearch
from app.search.intent_extractor import extract_intent
from app.search.query_builder import build_search_query

client = OpenSearch(
    hosts=[{"host": "opensearch", "port": 9200}]
)

def search_products(query):

    print("\n========== SEARCH SERVICE ==========")

    search_text, filters = extract_intent(query)

    body = build_search_query(search_text, filters)

    print("Generated Query:", body)

    response = client.search(
    index="jewellery_products",
    body=body
    )

    hits = response["hits"]["hits"]

    # ----------------------------------------
    # FALLBACK — filters only search
    # ----------------------------------------
    if len(hits) == 0 and filters:

        print("\n[FALLBACK] No text match. Running filter-only search")

        body = build_search_query("", filters)

        response = client.search(
            index="jewellery_products",
            body=body
        )

    return response
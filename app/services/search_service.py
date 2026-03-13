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

    print("\nTop Results:")

    for hit in hits[:5]:
        print(
            hit["_source"]["product_name"],
            "| score:", hit["_score"]
        )

    print("====================================\n")

    return [hit["_source"] for hit in hits]
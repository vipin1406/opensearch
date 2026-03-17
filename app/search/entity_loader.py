from opensearchpy import OpenSearch

client = OpenSearch(
    hosts=[{"host": "opensearch", "port": 9200}]
)

INDEX_NAME = "jewellery_products"


def load_catalog_entities():

    print("\n================================================")
    print("LOADING CATALOG ENTITIES FROM OPENSEARCH")
    print("================================================")

    response = client.search(
        index=INDEX_NAME,
        body={
            "size": 0,
            "aggs": {

                "metal": {
                    "terms": {
                        "field": "metal",
                        "size": 100
                    }
                },

                "product_type": {
                    "terms": {
                        "field": "product_type",
                        "size": 100
                    }
                },

                "stone_type": {
                    "terms": {
                        "field": "stone_type",
                        "size": 100
                    }
                },

                "metal_colour": {
                    "terms": {
                        "field": "metal_colour",
                        "size": 100
                    }
                },

                "pendant": {
                    "terms": {
                        "field": "pendant",
                        "size": 100
                    }
                },

                "usages": {
                    "terms": {
                        "field": "usages",
                        "size": 100
                    }
                },

                "no_of_mugappu": {
                    "terms": {
                        "field": "no_of_mugappu",
                        "size": 20
                    }
                }

            }
        }
    )

    entities = {

        "metal": [
            b["key"] for b in response["aggregations"]["metal"]["buckets"]
        ],

        "product_type": [
            b["key"] for b in response["aggregations"]["product_type"]["buckets"]
        ],

        "stone_type": [
            b["key"] for b in response["aggregations"]["stone_type"]["buckets"]
        ],

        "metal_colour": [
            b["key"] for b in response["aggregations"]["metal_colour"]["buckets"]
        ],

        "pendant": [
            b["key"] for b in response["aggregations"]["pendant"]["buckets"]
        ],

        "usages": [
            b["key"] for b in response["aggregations"]["usages"]["buckets"]
        ],

        "no_of_mugappu": [
            b["key"] for b in response["aggregations"]["no_of_mugappu"]["buckets"]
        ]

    }

    print("\n================ ENTITY VALUES ================")

    for field, values in entities.items():
        print(f"{field} → {values}")

    print("===============================================\n")

    return entities
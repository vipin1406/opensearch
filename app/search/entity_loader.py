from opensearchpy import OpenSearch

client = OpenSearch(
    hosts=[{"host": "opensearch", "port": 9200}]
)

def load_catalog_entities():

    print("\n====== LOADING ENTITIES FROM OPENSEARCH ======")

    response = client.search(
        index="jewellery_products",
        body={
            "size": 0,
            "aggs": {
                "layers": {"terms": {"field": "layers"}},
                "product_type": {"terms": {"field": "product_type"}},
                "metal": {"terms": {"field": "metal"}},
                "stone_type": {"terms": {"field": "stone_type"}},
          
            }
        }
    )

    entities = {
        "layers": [b["key"] for b in response["aggregations"]["layers"]["buckets"]],
        "product_type": [b["key"] for b in response["aggregations"]["product_type"]["buckets"]],
        "metal": [b["key"] for b in response["aggregations"]["metal"]["buckets"]],
        "stone_type": [b["key"] for b in response["aggregations"]["stone_type"]["buckets"]],
       
    }

    print("Loaded Entities:", entities)
    print("=============================================\n")

    return entities
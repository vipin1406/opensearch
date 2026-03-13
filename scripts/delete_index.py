from opensearchpy import OpenSearch

client = OpenSearch(
    hosts=[{"host": "opensearch", "port": 9200}]
)

index_name = "jewellery_products"

if client.indices.exists(index=index_name):
    client.indices.delete(index=index_name)
    print(f"{index_name} deleted successfully")
else:
    print("Index does not exist")
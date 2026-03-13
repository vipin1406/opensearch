from opensearchpy import OpenSearch

# Connect to OpenSearch
client = OpenSearch(
    hosts=[{"host": "opensearch", "port": 9200}]
)

index_name = "jewellery_products"

mapping = {
 "settings": {
  "analysis": {
   "filter": {
    "synonym_filter": {
     "type": "synonym_graph",
     "synonyms": [
      "chain, necklace",
      "bangle, bracelet",
      "stud, earring",
      "ring, band",
      "cz, cubic zirconia"
     ]
    },
    "edge_ngram_filter": {
     "type": "edge_ngram",
     "min_gram": 2,
     "max_gram": 20
    },
    "my_phonetic": {
     "type": "phonetic",
     "encoder": "double_metaphone",
     "replace": False
    }
   },
   "analyzer": {
    "autocomplete_analyzer": {
     "tokenizer": "standard",
     "filter": ["lowercase", "edge_ngram_filter"]
    },
    "synonym_analyzer": {
     "tokenizer": "standard",
     "filter": ["lowercase", "synonym_filter"]
    },
    "phonetic_analyzer": {
     "tokenizer": "standard",
     "filter": ["lowercase", "my_phonetic"]
    }
   }
  }
 },

 "mappings": {
  "dynamic": False,
  "properties": {

   "products_id": {"type": "keyword"},
   "tag_label": {"type": "keyword"},
   "url": {"type": "keyword"},

   "product_name": {
    "type": "text",
    "fields": {
     "autocomplete": {
      "type": "text",
      "analyzer": "autocomplete_analyzer",
      "search_analyzer": "standard"
     },
     "synonym": {
      "type": "text",
      "analyzer": "synonym_analyzer"
     },
     "phonetic": {
      "type": "text",
      "analyzer": "phonetic_analyzer"
     }
    }
   },

   "product_type": {"type": "keyword"},
   "metal": {"type": "keyword"},
   "purity": {"type": "keyword"},
   "gender": {"type": "keyword"},
   "stone_type": {"type": "keyword"},
   "metal_colour": {"type": "keyword"},
   "layers": {"type": "keyword"},
   "pendant": {"type": "keyword"},
   "religion": {"type": "keyword"},
   "no_of_mugappu": {"type": "keyword"},
   "usages": {"type": "keyword"},
   "weight": {"type": "float"},
    "motifs": {
    "type": "text",
    "analyzer": "synonym_analyzer"
   },
  }
 }
}

# Delete existing index
if client.indices.exists(index=index_name):
    client.indices.delete(index=index_name)

# Create the new index
client.indices.create(index=index_name, body=mapping)

print("Index with phonetic, ngrams, synonyms, and autocomplete created successfully!")
import json


def build_search_query(search_text, filters=None):

    print("\n================================================")
    print("QUERY BUILDER STARTED")
    print("================================================")

    if filters is None:
        filters = {}

    print("\nIncoming Search Text →", search_text)
    print("Incoming Filters →", filters)

    body = {
        "size": 100,
        "query": {
            "bool": {
                "must": [],
                "filter": []
            }
        }
    }

    # ------------------------------------------------
    # STEP 1 — TEXT SEARCH
    # ------------------------------------------------
    if search_text:

        print("\n[STEP 1] TEXT SEARCH")

        search_clause = {
            "dis_max": {
                "queries": [

                    # CROSS FIELD SEARCH
                    {
                        "multi_match": {
                            "query": search_text,
                            "type": "cross_fields",
                            "fields": [
                                "product_name^4",
                                "product_name.synonym^3",
                                "coated_with^2",
                                "motifs"
                            ],
                            "minimum_should_match": "75%"
                        }
                    },

                    # FUZZY SEARCH
                    {
                        "multi_match": {
                            "query": search_text,
                            "type": "best_fields",
                            "fields": [
                                "product_name^2",
                                "coated_with^2",
                                "motifs"
                            ],
                            "fuzziness": "AUTO"
                        }
                    },

                    # PHONETIC SEARCH
                    {
                        "match": {
                            "product_name.phonetic": {
                                "query": search_text,
                                "boost": 3
                            }
                        }
                    }

                ],
                "tie_breaker": 0.3
            }
        }

        body["query"]["bool"]["must"].append(search_clause)

        print("✔ Text search added")

    else:
        print("\n[STEP 1] No search text")

    # ------------------------------------------------
    # STEP 2 — APPLY FILTERS
    # ------------------------------------------------
    print("\n[STEP 2] APPLYING FILTERS")

    for key, value in filters.items():

        print(f"\nProcessing Filter → {key}: {value}")

        # WEIGHT RANGE FILTER
        if key == "weight_range":

            body["query"]["bool"]["filter"].append({
                "range": {
                    "weight": value
                }
            })

            print("✔ Weight range filter applied")

        # LAYERS RANGE FILTER
        elif key == "layers_range":

            body["query"]["bool"]["filter"].append({
                "range": {
                    "layers": {
                        "gte": value
                    }
                }
            })

            print("✔ Layers range filter applied")

        # WEIGHT TARGET SORTING
        elif key == "weight_value":

            print("✔ Weight target stored for ranking")

            body["sort"] = [
                {
                    "_script": {
                        "type": "number",
                        "script": {
                            "source": "Math.abs(doc['weight'].value - params.target)",
                            "params": {
                                "target": value
                            }
                        },
                        "order": "asc"
                    }
                }
            ]

        # NORMAL TERM FILTER
        else:

            body["query"]["bool"]["filter"].append({
                "term": {
                    key: value
                }
            })

            print(f"✔ Term filter → {key} = {value}")

    # ------------------------------------------------
    # STEP 3 — FINAL QUERY DEBUG
    # ------------------------------------------------
    print("\n================================================")
    print("FINAL OPENSEARCH QUERY")
    print("================================================")

    print(json.dumps(body, indent=2))

    print("\n================================================")
    print("QUERY BUILDER FINISHED")
    print("================================================\n")

    return body
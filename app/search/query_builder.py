import json


def build_search_query(search_text, filters=None):

    print("\n================================================")
    print("QUERY BUILDER STARTED")
    print("================================================")

    # -------- Initialize Filters --------
    if filters is None:
        filters = {}

    print("\nIncoming Search Text →", search_text)
    print("Incoming Filters →", filters)

    body = {
        "query": {
            "bool": {
                "must": [],
                "filter": []
            }
        }
    }

    # ------------------------------------------------
    # STEP 1 — BUILD TEXT SEARCH CLAUSES
    # ------------------------------------------------
    if search_text:

        print("\n[STEP 1] BUILDING SEARCH CLAUSES")
        print("Search strategy:")
        print(" 1️⃣ Exact phrase boost")
        print(" 2️⃣ Cross-field semantic match")
        print(" 3️⃣ Fuzzy fallback for typos")
        print(" 4️⃣ Phonetic fallback for sound similarity")

        search_clause = {
            "dis_max": {
                "queries": [

                    # -----------------------------------
                    # Exact phrase boost
                    # -----------------------------------
                    {
                        "match_phrase": {
                            "product_name": {
                                "query": search_text,
                                "boost": 6
                            }
                        }
                    },

                    # -----------------------------------
                    # Cross field match
                    # -----------------------------------
                    {
                        "multi_match": {
                            "query": search_text,
                            "type": "cross_fields",
                            "fields": [
                                "product_name^4",
                                "product_name.synonym^3",
                                "coated_with^3",
                                "motifs"
                            ],
                            "minimum_should_match": "75%"
                        }
                    },

                    # -----------------------------------
                    # Fuzzy fallback
                    # -----------------------------------
                    {
                        "multi_match": {
                            "query": search_text,
                            "fields": [
                                "product_name^2",
                                "coated_with^3",
                                "motifs"
                            ],
                            "fuzziness": "AUTO"
                        }
                    },

                    # -----------------------------------
                    # Phonetic fallback
                    # -----------------------------------
                    {
                        "match": {
                            "product_name.phonetic": {
                                "query": search_text,
                                "boost": 2
                            }
                        }
                    }

                ],

                # Helps combine scores from different queries
                "tie_breaker": 0.3
            }
        }

        body["query"]["bool"]["must"].append(search_clause)

        print("\nSearch clause successfully added.")

    else:

        print("\n[STEP 1] No search text provided.")
        print("Only filters will be applied.")

    # ------------------------------------------------
    # STEP 2 — APPLY FILTERS
    # ------------------------------------------------
    if filters:

        print("\n[STEP 2] APPLYING FILTERS")

        for key, value in filters.items():

            filter_clause = {"term": {key: value}}

            body["query"]["bool"]["filter"].append(filter_clause)

            print(f" ✔ Filter applied → {key} = {value}")

    else:

        print("\n[STEP 2] No filters detected.")

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
import json
from app.search.entity_loader import load_catalog_entities
CATALOG_ENTITIES = None

def build_search_query(search_text, filters=None, boost_terms=None, use_phonetic=False,boost_signals=None):
    global CATALOG_ENTITIES

    if CATALOG_ENTITIES is None:
        print("[QB] Loading catalog entities...")
        CATALOG_ENTITIES = load_catalog_entities()

    print("\n================================================")
    print("QUERY BUILDER STARTED")
    print("================================================")

    if filters is None:
        filters = {}

    if boost_signals is None:
        boost_signals = {}

    

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


    # ---------------------------------------
    # STEP 0 — PRODUCT TYPE DETECTION (NEW)
    # ---------------------------------------

    print("\n[STEP 0] PRODUCT TYPE DETECTION (QB)")

    tokens = search_text.split()

    detected_product_types = []

    for token in tokens:
        if token in CATALOG_ENTITIES["product_type"]:
            detected_product_types.append(token)
            print("✔ Detected product_type →", token)

  

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
                                "product_name^5",
                                "product_type^0",
                                "tags^3",                                "product_name.synonym^3",
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
                                "product_type^0",
                                "tags^5",
                                "coated_with^2",
                                "motifs"
                            ],
                            "fuzziness": "1",
                            "prefix_length":"2"
                        }
                    },

                    # PHONETIC SEARCH
                    {
                        "match": {
                            "product_name.phonetic": {
                                "query": search_text,
                                "boost": 0.5
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
        # NORMAL / RANGE / EXISTS FILTER
        else:

            # 🔹 EXISTS FILTER (with / without)
            if isinstance(value, dict) and "exists" in value:

                if value["exists"]:
                    body["query"]["bool"]["filter"].append({
                        "exists": {
                            "field": key
                        }
                    })
                else:
                    # must_not for "without"
                    body["query"]["bool"].setdefault("must_not", [])
                    body["query"]["bool"]["must_not"].append({
                        "exists": {
                            "field": key
                        }
                    })

                print(f"✔ Exists filter → {key} = {value['exists']}")

            # 🔹 RANGE FILTER (generic fallback)
            elif isinstance(value, dict):

                body["query"]["bool"]["filter"].append({
                    "range": {
                        key: value
                    }
                })

                print(f"✔ Range filter → {key} = {value}")

            # 🔹 NORMAL TERM FILTER
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

    # ---------------------------------------
    #STEP 4 PRODUCT TYPE APPLICATION
    # ---------------------------------------
   
    # ---------------------------------------
    # STEP 4 — PRODUCT TYPE LOGIC (FIXED)
    # ---------------------------------------
    if detected_product_types:

        tokens = search_text.split()
        product_types = list(set(detected_product_types))

        print(f"🎯 Product Types → {product_types}")
        print(f"🔍 Tokens → {tokens}")

        # ---------------------------------------
        # 🔥 CASE 1 — STRONG INTENT (SINGLE WORD)
        # ---------------------------------------
        if len(tokens) == 1:

            print("🔥 Strong intent → applying FILTER")

            for pt in product_types:
                body["query"]["bool"]["filter"].append({
                    "term": {
                        "product_type": pt
                    }
                })


        # ---------------------------------------
        # 🔥 CASE 2 — WEAK / MULTI INTENT
        # ---------------------------------------
        else:

            print("⚡ Weak intent → applying BOOST only")

            body["query"]["bool"].setdefault("should", [])

            for pt in product_types:

                # 🔥 soft boost
                body["query"]["bool"]["should"].append({
                    "term": {
                        "product_type": {
                            "value": pt,
                            "boost": 3   # reduced from 8
                        }
                    }
                })

                # 🔥 support via product_name
                body["query"]["bool"]["should"].append({
                    "match": {
                        "product_name": {
                            "query": pt,
                            "boost": 2
                        }
                    }
                })
        

    # ==========================================
    # 🔥 STEP 4.5 — RULE ENGINE BOOST TERMS
    # ==========================================
    print("\n[STEP 4.5] APPLYING BOOST TERMS")

    if boost_terms:
        print(f"🔥 Boost terms → {boost_terms}")

        body["query"]["bool"].setdefault("should", [])

        # -------------------------------
        # SINGLE TERM BOOST
        # -------------------------------
        for term in boost_terms:
            body["query"]["bool"]["should"].append({
                "term": {
                    "tags.keyword": {
                        "value": term,
                        "boost": 3
                    }
                }
            })

        # -------------------------------
        # COMBINATION BOOST (VERY IMPORTANT)
        # -------------------------------
        if len(boost_terms) >= 2:
            body["query"]["bool"]["should"].append({
                "bool": {
                    "must": [
                        {
                            "term": {
                                "tags.keyword": t
                            }
                        } for t in boost_terms
                    ],
                    "boost": 5
                }
            })
        
    # ---------------------------------------
    # STEP 5 — DEFAULT BOOSTING (FINAL)
    # ---------------------------------------

    print("\n[STEP 5] DEFAULT BOOSTING")

    body["query"]["bool"].setdefault("should", [])

    # -------------------------------
    # METAL LOGIC
    # -------------------------------
    if "metal" in filters:
        print("🔒 Metal filter already applied →", filters["metal"])
    else:
        body["query"]["bool"]["should"].append({
            "constant_score": {
                "filter": {
                    "term": {
                        "metal": "gold"
                    }
                },
                "boost": 8
            }
        })
        print("🎯 Gold boost applied")

    # -------------------------------
    # PURITY LOGIC
    # -------------------------------
    if "purity" in filters:
        print("🔒 Purity filter already applied →", filters["purity"])
    else:
        body["query"]["bool"]["should"].append({
            "constant_score": {
                "filter": {
                    "term": {
                        "purity": "22k"
                    }
                },
                "boost": 6
            }
        })
        print("🎯 22K boost applied")

    # IMPORTANT: allow should to act as boost only
    body["query"]["bool"]["minimum_should_match"] = 0


    

    return body
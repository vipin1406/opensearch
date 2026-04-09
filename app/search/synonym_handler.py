from app.search.config import SYNONYM_MAP

def apply_synonyms(query: str) -> str:

    print("\n========== SYNONYM EXPANSION ==========")

    tokens = query.lower().split()
    expanded_tokens = []

    i = 0

    while i < len(tokens):

        token = tokens[i]

        # 🔥 handle phrase (toe ring)
        if i < len(tokens) - 1:
            phrase = f"{tokens[i]} {tokens[i+1]}"

            if phrase in SYNONYM_MAP:
                expanded_tokens.append(phrase)
                expanded_tokens.extend(SYNONYM_MAP[phrase])

                print(f"[SYNONYM] {phrase} → {SYNONYM_MAP[phrase]}")

                i += 2
                continue

        # 🔥 handle single word
        expanded_tokens.append(token)

        if token in SYNONYM_MAP:
            expanded_tokens.extend(SYNONYM_MAP[token])
            print(f"[SYNONYM] {token} → {SYNONYM_MAP[token]}")

        i += 1

    final_query = " ".join(expanded_tokens)

    print("Expanded Query:", final_query)
    print("=======================================\n")

    return final_query
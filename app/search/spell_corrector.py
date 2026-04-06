from difflib import get_close_matches, SequenceMatcher
from metaphone import doublemetaphone


# -----------------------------------
# PHONETIC CODE
# -----------------------------------
def phonetic_code(word):
    return doublemetaphone(word)[0]


# -----------------------------------
# EDIT DISTANCE (Levenshtein)
# -----------------------------------
def edit_distance(s1, s2):

    if len(s1) < len(s2):
        return edit_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    prev_row = range(len(s2) + 1)

    for i, c1 in enumerate(s1):
        curr_row = [i + 1]

        for j, c2 in enumerate(s2):
            insertions = prev_row[j + 1] + 1
            deletions = curr_row[j] + 1
            substitutions = prev_row[j] + (c1 != c2)

            curr_row.append(min(insertions, deletions, substitutions))

        prev_row = curr_row

    return prev_row[-1]


# -----------------------------------
# WHITELIST CHECK
# -----------------------------------
def is_whitelisted(token, vocabulary):
    return token in vocabulary


# -----------------------------------
# CONTROLLED SPELL CORRECTION
# -----------------------------------
def correct_token(token, vocabulary):

    print("\n🔍 Processing token (fuzzy/phonetic stage):", token)

    token = token.lower()

    # -----------------------------------
    # 1. LENGTH RULE
    # -----------------------------------
    if len(token) < 3:
        print("⛔ Skip → length < 3")
        return token

    # -----------------------------------
    # 2. WHITELIST CHECK
    # -----------------------------------
    if is_whitelisted(token, vocabulary):
        print("✅ Whitelisted →", token)
        return token

    # -----------------------------------
    # 3. FUZZY MATCH
    # -----------------------------------
    print("➡️ Trying fuzzy match...")

    fuzzy = get_close_matches(token, vocabulary, n=1, cutoff=0.8)

    if fuzzy:

        candidate = fuzzy[0]
        print(f"🔎 Candidate → {candidate}")

        dist = edit_distance(token, candidate)
        print(f"📏 Edit Distance → {dist}")

        if len(token) == 4 and dist > 1:
            print("⛔ Rejected → 4-letter word, distance > 1")
            return token

        if dist > 2:
            print("⛔ Rejected → distance > 2")
            return token

        ratio = SequenceMatcher(None, token, candidate).ratio()
        print(f"📊 Confidence Ratio → {ratio:.2f}")

        if ratio < 0.85:
            print("⛔ Rejected → low confidence")
            return token

        if abs(len(token) - len(candidate)) > 1:
            print("⛔ Rejected → length difference too high")
            return token

        print(f"✅ Fuzzy corrected → {token} → {candidate}")
        return candidate

    print("❌ No fuzzy match found")

    # -----------------------------------
    # 4. PHONETIC MATCH
    # -----------------------------------
    print("➡️ Trying phonetic match...")

    token_ph = phonetic_code(token)

    for word in vocabulary:

        if phonetic_code(word) == token_ph:

            dist = edit_distance(token, word)
            print(f"🔎 Phonetic candidate → {word} (distance={dist})")

            if dist <= 2:
                print(f"✅ Phonetic corrected → {token} → {word}")
                return word
            else:
                print("⛔ Rejected phonetic → distance too high")

    print("❌ No correction applied →", token)
    return token


# -----------------------------------
# MAIN SPELL CORRECTION PIPELINE
# -----------------------------------
def spell_correct(tokens, vocabulary, entities):

    print("\n========== 🔤 SPELL CORRECTION START ==========")

    corrected_tokens = []

    # -----------------------------------
    # 🔥 BUILD PRIORITY ENTITY SETS
    # -----------------------------------
    tag_entities = set(str(v).strip().lower() for v in entities.get("tags", []))
    product_entities = set(str(v).strip().lower() for v in entities.get("product_type", []))

    # fallback (all entities)
    all_entities = set()
    for field_values in entities.values():
        for val in field_values:
            all_entities.add(str(val).strip().lower())

    print("\n📦 ENTITY SUMMARY")
    print("Tags count:", len(tag_entities))
    print("Product types count:", len(product_entities))
    print("Total entities:", len(all_entities))

    # -----------------------------------
    # 🔄 TOKEN LOOP
    # -----------------------------------
    for token in tokens:

        token_clean = token.strip().lower()

        print(f"\n[CORRECTION] Processing token → {token_clean}")

        # ==========================================
        # ✅ STEP 1: STRICT EXACT MATCH PRIORITY
        # ==========================================
        if token_clean in tag_entities:
            print(f"[CORRECTION] ✅ EXACT TAG MATCH → {token_clean}")
            corrected_tokens.append(token_clean)
            continue

        if token_clean in product_entities:
            print(f"[CORRECTION] ✅ EXACT PRODUCT TYPE MATCH → {token_clean}")
            corrected_tokens.append(token_clean)
            continue

        if token_clean in all_entities:
            print(f"[CORRECTION] ✅ EXACT MATCH (OTHER FIELD) → {token_clean}")
            corrected_tokens.append(token_clean)
            continue

        # ==========================================
        # 🔄 STEP 2: APPLY CONTROLLED CORRECTION
        # ==========================================
        corrected = correct_token(token_clean, vocabulary)

        # 🔥 DEBUG: SHOW FINAL DECISION
        if corrected != token_clean:
            print(f"[CORRECTION] 🔁 FINAL CORRECTION → {token_clean} → {corrected}")
        else:
            print(f"[CORRECTION] ➡️ NO CHANGE → {token_clean}")

        corrected_tokens.append(corrected)

    # -----------------------------------
    # 📊 FINAL OUTPUT
    # -----------------------------------
    print("\n🧾 FINAL TOKENS →", corrected_tokens)
    print("========== 🔤 SPELL CORRECTION END ==========\n")

    return corrected_tokens
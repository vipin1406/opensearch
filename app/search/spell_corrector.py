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

    print("\n🔍 Processing token:", token)

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
    # 3. FUZZY MATCH (CONTROLLED)
    # -----------------------------------
    print("➡️ Trying fuzzy match...")

    fuzzy = get_close_matches(token, vocabulary, n=1, cutoff=0.8)

    if fuzzy:

        candidate = fuzzy[0]
        print(f"🔎 Candidate → {candidate}")

        # EDIT DISTANCE
        dist = edit_distance(token, candidate)
        print(f"📏 Edit Distance → {dist}")

        # 🔒 RULE: 4-letter strict
        if len(token) == 4 and dist > 1:
            print("⛔ Rejected → 4-letter word, distance > 1")
            return token

        # 🔒 RULE: general limit
        if dist > 2:
            print("⛔ Rejected → distance > 2")
            return token

        # CONFIDENCE
        ratio = SequenceMatcher(None, token, candidate).ratio()
        print(f"📊 Confidence Ratio → {ratio:.2f}")

        if ratio < 0.85:
            print("⛔ Rejected → low confidence")
            return token

        # LENGTH DIFFERENCE
        if abs(len(token) - len(candidate)) > 1:
            print("⛔ Rejected → length difference too high")
            return token

        print(f"✅ Fuzzy corrected → {token} → {candidate}")
        return candidate

    print("❌ No fuzzy match found")

    # -----------------------------------
    # 4. PHONETIC MATCH (SAFE MODE)
    # -----------------------------------
    print("➡️ Trying phonetic match...")

    token_ph = phonetic_code(token)

    for word in vocabulary:

        if phonetic_code(word) == token_ph:

            dist = edit_distance(token, word)
            print(f"🔎 Phonetic candidate → {word} (distance={dist})")

            # STRICT CONTROL
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
def spell_correct(tokens, vocabulary):

    print("\n========== 🔤 SPELL CORRECTION START ==========")

    corrected_tokens = []

    for token in tokens:
        corrected = correct_token(token, vocabulary)
        corrected_tokens.append(corrected)

    print("\n🧾 FINAL TOKENS →", corrected_tokens)
    print("========== 🔤 SPELL CORRECTION END ==========\n")

    return corrected_tokens
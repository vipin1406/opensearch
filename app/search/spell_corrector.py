from difflib import get_close_matches
from metaphone import doublemetaphone


def phonetic_code(word):
    return doublemetaphone(word)[0]


def correct_token(token, vocabulary):

    print("\nProcessing token:", token)

    # -------- EXACT MATCH --------
    if token in vocabulary:
        print("Exact match →", token)
        return token

    # -------- FUZZY MATCH --------
    fuzzy = get_close_matches(token, vocabulary, n=1, cutoff=0.8)

    if fuzzy:
        print("Fuzzy corrected:", token, "→", fuzzy[0])
        return fuzzy[0]

    # -------- PHONETIC MATCH --------
    token_ph = phonetic_code(token)

    for word in vocabulary:

        if phonetic_code(word) == token_ph:
            print("Phonetic corrected:", token, "→", word)
            return word

    print("No correction applied")
    return token


def spell_correct(tokens, vocabulary):

    print("\n========== SPELL CORRECTION ==========")

    corrected_tokens = []

    for token in tokens:
        corrected_tokens.append(correct_token(token, vocabulary))

    print("\nCorrected Tokens:", corrected_tokens)

    print("======================================\n")

    return corrected_tokens
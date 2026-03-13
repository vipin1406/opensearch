
def generate_phrases(tokens, max_size=3):

    phrases = []

    for size in range(1, max_size + 1):
        for i in range(len(tokens) - size + 1):

            phrase = " ".join(tokens[i:i+size])
            phrases.append(phrase)

    return phrases
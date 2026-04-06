import re


def normalize_layers(value):

    print("\n------------------------------------")
    print("NORMALIZING LAYERS VALUE")
    print("------------------------------------")
    print("Raw value:", value)

    if not value:
        print("No layer value found → returning None")
        return None

    value = str(value).lower().strip()

    print("Normalized text:", value)

    # -----------------------------------
    # Handle multiple / multi layer
    # -----------------------------------
    if "multiple" in value or "multi" in value:
        print("Detected MULTIPLE layer → mapped to 4")
        return 4

    # -----------------------------------
    # Extract numeric layers
    # -----------------------------------
    match = re.search(r"\d+", value)

    if match:

        layer_number = int(match.group())

        print("Detected numeric layer →", layer_number)

        return layer_number

    # -----------------------------------
    # Handle text numbers
    # -----------------------------------
    text_layers = {
        "single": 1,
        "double": 2,
        "triple": 3
    }

    for word, number in text_layers.items():

        if word in value:

            print(f"Detected text layer '{word}' → mapped to {number}")

            return number

    print("No layer pattern detected → returning None")

    return None


import re

# -----------------------------------
# CONFIG
# -----------------------------------

TAG_COLUMNS = [
    "product_name",
    "product_type",
    "coated_with",
    "metal_colour",
    "stone_type",
    "motifs",
    "usages"
]

STOP_WORDS = {
    "the", "and", "with", "for", "of", "in", "on",
    "a", "an", "to"
}


# -----------------------------------
# CLEAN TEXT
# -----------------------------------

def clean_text(text):
    text = str(text).lower()

    # remove special characters
    text = re.sub(r"[^a-z0-9\s]", " ", text)

    # normalize spaces
    text = " ".join(text.split())

    return text


# -----------------------------------
# EXTRACT WORDS
# -----------------------------------

def extract_words(value):
    value = clean_text(value)

    words = value.split()

    # filter noise
    words = [
        w for w in words
        if w not in STOP_WORDS
           # avoid junk like "a", "x"
    ]

    return words


# -----------------------------------
# GENERATE TAGS
# -----------------------------------

def generate_tags(product):
    tags = set()

    # -----------------------------------
    # ADD "earring" FOR STUD
    # -----------------------------------

    pt = product.get("product_type")

    if pt:
        pt = pt.lower()

        if pt == "stud":
            tags.add("earring")
    for column in TAG_COLUMNS:

        value = product.get(column)

        if not value:
            continue

        # handle list values (if any)
        if isinstance(value, list):
            for v in value:
                tags.update(extract_words(v))

        else:
            tags.update(extract_words(value))

    return list(tags)
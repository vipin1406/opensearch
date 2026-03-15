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
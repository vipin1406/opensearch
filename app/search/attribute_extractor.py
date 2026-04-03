import re

def extract_attributes(query):
    filters = {}

    # 🔥 UNIVERSAL PURITY PATTERN
    match = re.search(
        r"\b(22|18|24)\s*(k|kt|karat|carat)?\b",
        query
    )

    if match:
        value = match.group(1)
        filters["purity"] = f"{value}k"

        # remove full match (handles 22k, 22 karat, etc.)
        query = query.replace(match.group(0), "")

    # 🔥 REMOVE LEFTOVER WORDS
    query = re.sub(r"\b(k|kt|karat|carat)\b", "", query)

    # 🔥 CLEAN SPACES
    query = " ".join(query.split())

    return query, filters
METAL_SYNONYMS = {
    "gld": "gold",
    "gol": "gold",
    "glod": "gold",
    "silvr": "silver"
}

PURITY_MAP = {
    "22k": "22k",
    "22kt": "22k",
    "22": "22k",
    "22 carat": "22k",
    "22k gold": "22k",
    "916": "22k",
    "22carat": "22k",
    "22 karat": "22k",
    "22karat": "22k",

    "18k": "18k",
    "18kt": "18k",
    "18": "18k",
    "18 carat": "18k",
    "750": "18k",
    "18 karat": "18k",
    "18carat": "18k",
    "18karat": "18k"

  
}

GENDER_MAP = {
    "mans": "man",
    "mens": "man",
    "male": "man",
    "gents": "man",
    "boys": "man",
    "men":"man",
    "man":"man",

    "womens": "woman",
    "women": "woman",
    "female": "woman",
    "ladies": "woman",
    "girls": "woman",
    "ladies": "woman",
    "womans":"woman",
    "ladis":"woman",
    "woman":"woman",

    "unisex":"unisex",

    "kid": "baby",
    "kids": "baby",
    "baby": "baby",
    "child": "baby",
    "children": "baby",
}

USAGE_MAP = {

    "daily": "daily wear",
    "office": "daily wear",
    "lightweight": "daily wear",

    "party": "cocktail and party wear",
    "cocktail": "cocktail and party wear",

    "festival": "festive wear",
    "festive": "festive wear",

    "wedding": "bridal wear",
    "bridal": "bridal wear"

}

NUMERIC_FIELDS = {
    "no_of_mugappu",
    "weight",
    "layers"
}


SYNONYM_MAP = {

    # product synonyms
    "metti": ["toe ring"],
    "toe ring": ["metti"],
    "anklet":['golusu'],
    "golusu":['anklet'],
    "pendant":['dollar'],
    "dollar":['pendant'],
    "earring":['stud'],
    "jhumka":['jimikki'],
    "jimikki":['jhumka'],
    "mangalyam":['tali'],
    "mangalsutra":['tali']


}

WEIGHT_OPERATORS = {
    "under": "lt",
    "below": "lt",
    "less": "lt",

    "above": "gt",
    "over": "gt",
    "more": "gt"
}

SOVEREIGN_UNITS = {
    "sovereign",
    "sovereigns",
    "pavan",        # common in Tamil
    "pavans",
    "powan",
    "powen",
    "povun",
    "savaran"
}


# ==========================================
# 🔥 SMART WEIGHT PARSING CONFIG
# ==========================================

WEIGHT_PATTERNS = [
    {
        "type": "upper_bound",
        "operators": {"under", "below", "less"}
    },
    {
        "type": "lower_bound",
        "operators": {"above", "over", "more"}
    }
]

NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10
}

WEIGHT_INTENT = {
    "light": {"lte": 5},
    "lightweight": {"lte": 5},
    "heavy": {"gte": 15}
}

SOVEREIGN_TO_GRAM = 8


CATEGORY_DEFAULT_BOOST = {
    "earring": {
        "metal": "gold",
        "purity": "22k"
    },
    "ring": {
        "metal": "gold",
        "purity": "22k"
    },
    "metti": {
        "metal": "silver"
    }
}
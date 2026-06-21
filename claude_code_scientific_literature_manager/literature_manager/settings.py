import json
from copy import deepcopy
from pathlib import Path


DEFAULT_CONFIG = {
    "identifier_prefix": "CB",
    "start_number": 1,
    "identifier_digits": 3,
    "numbering_mode": "global",
    "category_identifiers": {
        "Micelles": {"prefix": "M"},
        "Chiral": {"prefix": "C"},
        "Soup": {"prefix": "S"},
        "Astro": {"prefix": "A"},
        "Light": {"prefix": "L"},
        "OrganBactr": {"prefix": "O"},
        "General": {"prefix": ""},
    },
    "title_words": 8,
    "text_pages": 3,
    "filename_template": "{identifier} {last_author}, {title}, {journal_abbrev} {year_short}.pdf",
    "categories": {
        "Micelles": [
            "micelle",
            "micelles",
            "micellar",
            "amphiphile",
            "amphiphiles",
            "vesicle",
            "vesicles",
            "composome",
            "composomes",
            "gard",
        ],
        "Chiral": [
            "chiral",
            "chirality",
            "enantiomer",
            "enantiomers",
            "homochirality",
        ],
        "Soup": [
            "origin of life",
            "prebiotic",
            "primordial soup",
            "autocatalysis",
            "replication",
        ],
        "Astro": [
            "astrobiology",
            "biosignature",
            "enceladus",
            "europa",
            "icy moon",
            "mars",
            "ocean world",
        ],
        "Light": [
            "light",
            "photochemical",
            "photochemistry",
            "photolysis",
            "photosynthesis",
            "irradiation",
            "ultraviolet",
        ],
        "OrganBactr": [
            "bacteria",
            "bacterial",
            "microbe",
            "microbes",
            "microbial",
            "microorganism",
            "microorganisms",
            "organotroph",
            "organotrophs",
        ],
        "General": [],
    },
    "sort_only_categories": {
        "Mutual Catalysis": [
            "mutual catalysis",
            "non enzymatic catalysis",
            "peptide catalysis",
            "catalytic amphiphiles",
            "micellar catalysis",
            "catalytic micelles",
        ],
        "Lipid World": [
            "Lipid World",
            "lipid catalysis",
            "lipid catalyst",
            "Origin of life",
            "prebiotic evolution",
            "mutually catalytic networks",
            "autocatalytic sets",
            "reflexively catalytic sets",
        ],
        "Extra": [],
    },
    "priority_rules": {
        "authors": ["Lancet"],
        "journals": [],
        "keywords": [
            "Doron Lancet",
            "GARD",
            "composome",
            "origin of life",
        ],
    },
}


def deep_merge(base, updates):
    merged = deepcopy(base)
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(config_path):
    if not config_path:
        return deepcopy(DEFAULT_CONFIG)

    path = Path(config_path)
    with path.open("r", encoding="utf-8") as handle:
        user_config = json.load(handle)

    return deep_merge(DEFAULT_CONFIG, user_config)

import re


def split_keyword_text(value):
    keywords = [
        keyword.strip().strip("\"'[] ")
        for keyword in re.split(r"\s+OR\s+|[;\n]", value or "", flags=re.IGNORECASE)
    ]
    return [keyword for keyword in keywords if keyword]


def category_names(config):
    names = list(config.get("categories", {}).keys())
    return names or ["General"]


def category_prefix_lines(config):
    category_settings = config.get("category_identifiers", {})
    lines = []

    for category in config.get("categories", {}):
        prefix = category_settings.get(category, {}).get("prefix")
        if prefix is None:
            prefix = category[:2].upper()
        lines.append(f"{category}={prefix}")

    return "\n".join(lines)


def default_sort_rules(config, minimum=3):
    rules = list(config.get("sort_only_categories", {}).items())
    while len(rules) < minimum:
        rules.append((f"Extra {len(rules) + 1}", []))
    return rules[:minimum]


def positive_int(value, default):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return number if number > 0 else default


def parse_category_prefixes(text, default_start_number):
    category_identifiers = {}

    for line in (text or "").splitlines():
        line = line.strip()
        if not line or "=" not in line:
            continue

        category, value = line.split("=", 1)
        category = category.strip()
        parts = [part.strip() for part in value.split(",", 1)]
        prefix = parts[0]

        if not category:
            continue

        category_identifiers[category] = {"prefix": prefix}
        if len(parts) > 1 and parts[1]:
            category_identifiers[category]["start_number"] = positive_int(
                parts[1],
                default_start_number,
            )

    return category_identifiers


def merge_sort_rules_with_base(sort_rules, base_categories):
    categories = {}

    for category, keywords in sort_rules:
        category = category.strip()
        if category:
            categories[category] = list(keywords)

    for category, keywords in base_categories.items():
        if category.lower() == "general":
            continue
        categories.setdefault(category, keywords)

    categories.setdefault("General", [])
    return categories

import re


def metadata_haystack(metadata, text):
    return " ".join(
        [
            metadata.title,
            metadata.journal,
            metadata.last_author,
            text or "",
        ]
    ).lower()


def keyword_matches(keyword, haystack):
    keyword = keyword.strip().lower()
    haystack = (haystack or "").lower()
    if not keyword:
        return False

    parts = [re.escape(part) for part in keyword.split()]
    pattern = r"[\s-]+".join(parts)
    return re.search(rf"(?<![a-z0-9]){pattern}(?![a-z0-9])", haystack) is not None


def classify_paper(metadata, text, categories):
    haystack = metadata_haystack(metadata, text)

    for category, keywords in categories.items():
        if category.lower() == "general":
            continue

        matches = [keyword for keyword in keywords if keyword_matches(keyword, haystack)]
        if matches:
            return category, matches

    return "General", []


def prioritize_paper(metadata, text, priority_rules):
    haystack = metadata_haystack(metadata, text)

    for author in priority_rules.get("authors", []):
        if author.lower() in metadata.last_author.lower():
            return "high"

    for journal in priority_rules.get("journals", []):
        if journal.lower() in metadata.journal.lower():
            return "high"

    for keyword in priority_rules.get("keywords", []):
        if keyword_matches(keyword, haystack):
            return "high"

    return "normal"

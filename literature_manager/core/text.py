import html
import re


LOWER_TITLE_WORDS = {
    "a",
    "an",
    "and",
    "at",
    "by",
    "for",
    "from",
    "in",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}

JOURNAL_STOP_WORDS = {
    "a",
    "and",
    "for",
    "in",
    "international",
    "journal",
    "of",
    "on",
    "the",
}


def clean_text(text):
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def sanitize_filename(text):
    text = clean_text(text)
    text = re.sub(r'[\\/*?:"<>|]', "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" .")


def title_case_smart(title):
    words = clean_text(title).lower().split()
    if not words:
        return "Unknown Title"

    result = []
    for index, word in enumerate(words):
        if index == 0 or word not in LOWER_TITLE_WORDS:
            result.append(word.capitalize())
        else:
            result.append(word)
    return " ".join(result)


def shorten_title(title, max_words):
    words = clean_text(title).split()
    if not words:
        return "Unknown Title"
    return " ".join(words[:max_words])


def abbreviate_journal(journal):
    journal = sanitize_filename(journal)
    if not journal:
        return "Unknown"

    journal = re.sub(r"[^\w\s]", " ", journal)
    words = [
        re.sub(r"[^A-Za-z0-9]", "", word)
        for word in journal.split()
        if word.lower() not in JOURNAL_STOP_WORDS
    ]
    words = [word for word in words if len(word) >= 3]

    if not words:
        return "Unknown"

    parts = []
    for word in words[:4]:
        if word.isupper() and len(word) <= 4:
            parts.append(word)
        else:
            parts.append(word[:4].title())
    return " ".join(parts)

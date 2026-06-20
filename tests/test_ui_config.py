from literature_manager.ui_config import (
    category_prefix_lines,
    default_sort_rules,
    merge_sort_rules_with_base,
    parse_category_prefixes,
    positive_int,
    split_keyword_text,
)


def test_split_keyword_text_accepts_semicolon_newline_and_or():
    assert split_keyword_text("micelle; vesicle\norigin OR ocean world") == [
        "micelle",
        "vesicle",
        "origin",
        "ocean world",
    ]


def test_parse_category_prefixes_supports_start_number():
    parsed = parse_category_prefixes("Micelles=M,100\nGeneral=", 1)

    assert parsed == {
        "Micelles": {"prefix": "M", "start_number": 100},
        "General": {"prefix": ""},
    }


def test_positive_int_falls_back_for_invalid_values():
    assert positive_int("5", 1) == 5
    assert positive_int("0", 1) == 1
    assert positive_int("bad", 3) == 3


def test_default_sort_rules_pads_to_three_rules():
    config = {"sort_only_categories": {"A": ["one"]}}

    assert default_sort_rules(config) == [
        ("A", ["one"]),
        ("Extra 2", []),
        ("Extra 3", []),
    ]


def test_category_prefix_lines_uses_config_or_category_name():
    config = {
        "categories": {"Micelles": [], "NewCategory": []},
        "category_identifiers": {"Micelles": {"prefix": "M"}},
    }

    assert category_prefix_lines(config) == "Micelles=M\nNewCategory=NE"


def test_merge_sort_rules_with_base_keeps_general_last_fallback():
    categories = merge_sort_rules_with_base(
        [("Custom", ["keyword"])],
        {"Micelles": ["micelle"], "General": []},
    )

    assert categories == {
        "Custom": ["keyword"],
        "Micelles": ["micelle"],
        "General": [],
    }

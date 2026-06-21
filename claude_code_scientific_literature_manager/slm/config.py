"""Typed configuration dataclasses for slm.

The original project used a plain dict merged with deep_merge().
Here I use proper dataclasses with sub-configs, so each section
is independently typed and editable without magic string keys.
"""
from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_CATEGORIES: dict[str, list[str]] = {
    "Micelles": [
        "micelle", "micellar", "amphiphile", "amphiphiles",
        "vesicle", "vesicles", "composome", "gard",
    ],
    "Chiral": ["chiral", "chirality", "enantiomer", "enantiomers", "homochirality"],
    "Soup": ["origin of life", "prebiotic", "primordial soup", "autocatalysis", "replication"],
    "Astro": ["astrobiology", "biosignature", "enceladus", "europa", "icy moon", "mars", "ocean world"],
    "Light": ["light", "photochemical", "photochemistry", "photolysis", "photosynthesis", "irradiation", "ultraviolet"],
    "OrganBactr": [
        "bacteria", "bacterial", "microbe", "microbes", "microbial",
        "microorganism", "microorganisms", "organotroph", "organotrophs",
    ],
    "General": [],
}

DEFAULT_SORT_CATEGORIES: dict[str, list[str]] = {
    "Mutual Catalysis": [
        "mutual catalysis", "non enzymatic catalysis", "peptide catalysis",
        "catalytic amphiphiles", "micellar catalysis", "catalytic micelles",
    ],
    "Lipid World": [
        "lipid world", "lipid catalysis", "lipid catalyst", "origin of life",
        "prebiotic evolution", "mutually catalytic networks", "autocatalytic sets",
    ],
    "Extra": [],
}


@dataclass
class NamingConfig:
    prefix: str = "CB"
    start: int = 1
    digits: int = 3
    per_category: bool = False
    category_prefixes: dict[str, str] = field(default_factory=lambda: {
        "Micelles": "M", "Chiral": "C", "Soup": "S",
        "Astro": "A", "Light": "L", "OrganBactr": "O", "General": "",
    })
    template: str = "{id} {author}, {title}, {journal} {year}.pdf"
    title_words: int = 8


@dataclass
class ScanConfig:
    pages: int = 3


@dataclass
class PriorityConfig:
    authors: list[str] = field(default_factory=lambda: ["Lancet"])
    journals: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=lambda: [
        "Doron Lancet", "GARD", "composome", "origin of life",
    ])


@dataclass
class Config:
    naming: NamingConfig = field(default_factory=NamingConfig)
    scan: ScanConfig = field(default_factory=ScanConfig)
    priority: PriorityConfig = field(default_factory=PriorityConfig)
    categories: dict[str, list[str]] = field(
        default_factory=lambda: deepcopy(DEFAULT_CATEGORIES)
    )
    sort_categories: dict[str, list[str]] = field(
        default_factory=lambda: deepcopy(DEFAULT_SORT_CATEGORIES)
    )

    @classmethod
    def from_file(cls, path: Path) -> Config:
        """Load a JSON config file and overlay it on the defaults."""
        data = json.loads(path.read_text(encoding="utf-8"))
        cfg = cls()
        for sub, sub_cfg in [("naming", cfg.naming), ("scan", cfg.scan), ("priority", cfg.priority)]:
            for key, value in data.get(sub, {}).items():
                if hasattr(sub_cfg, key):
                    setattr(sub_cfg, key, value)
        cfg.categories.update(data.get("categories", {}))
        cfg.sort_categories.update(data.get("sort_categories", {}))
        return cfg

    def effective_prefix(self, category: str) -> str:
        if self.naming.per_category:
            return self.naming.category_prefixes.get(category, self.naming.prefix)
        return self.naming.prefix

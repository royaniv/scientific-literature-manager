from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PaperMetadata:
    source_path: Path
    doi: str = ""
    title: str = "Unknown Title"
    journal: str = "Unknown Journal"
    journal_abbrev: str = "Unknown"
    year: str = "0000"
    last_author: str = "Unknown"
    category: str = "General"
    priority: str = "normal"
    matched_keywords: list[str] = field(default_factory=list)
    new_filename: str = ""
    destination_path: Path | None = None
    action: str = "pending"

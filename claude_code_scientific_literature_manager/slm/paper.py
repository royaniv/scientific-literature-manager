"""Paper dataclass with a proper state enum.

The original used string literals ("preview", "copied", "moved") for state.
I use an enum so state transitions are explicit and exhaustive.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path


class PaperState(Enum):
    PENDING = auto()
    PLANNED = auto()
    DONE = auto()
    FAILED = auto()


@dataclass
class Paper:
    source: Path
    doi: str = ""
    title: str = "Unknown Title"
    journal: str = "Unknown Journal"
    journal_short: str = "Unknown"
    year: str = "0000"
    author: str = "Unknown"
    category: str = "General"
    priority: str = "normal"
    keywords: list[str] = field(default_factory=list)
    new_name: str = ""
    destination: Path | None = None
    state: PaperState = PaperState.PENDING
    error: str = ""

    @property
    def year_short(self) -> str:
        return self.year[-2:] if len(self.year) >= 2 else "00"

    @property
    def is_high_priority(self) -> bool:
        return self.priority == "high"

    @property
    def state_label(self) -> str:
        labels = {
            PaperState.PENDING: "Pending",
            PaperState.PLANNED: "Preview",
            PaperState.DONE: "Done",
            PaperState.FAILED: f"Failed: {self.error}",
        }
        return labels[self.state]

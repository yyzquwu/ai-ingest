from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class SourceSpec:
    id: str
    label: str
    kind: str
    limit: int
    url: str | None = None
    query: str | None = None


@dataclass(slots=True)
class RawItem:
    id: str
    source: str
    source_label: str
    title: str
    url: str
    summary: str
    published: str = ""

    def compact(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["summary"] = self.summary[:1400]
        return payload


@dataclass(slots=True)
class RankedItem(RawItem):
    relevance_score: int = 0
    one_line: str = ""
    key_takeaway: str = ""
    skills: list[str] = field(default_factory=list)
    category: str = "other"

    def compact(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class DigestResult:
    summary: str
    articles: list[RankedItem]

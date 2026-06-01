from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class PerceptionProviderDiagnostics:
    provider_name: str
    asset_root: Path | None = None
    details: dict[str, str] = field(default_factory=dict)
    missing_items: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.missing_items

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, cast

from munk.config.load import profile_config_path
from munk.storage_mode import current_home_resolution
from munk.user_data import assets_home, cache_home, config_home, munkai_home, operations_home, runs_home


@dataclass(frozen=True)
class UserDataPaths:
    home: Path
    assets: Path
    runs: Path
    operations: Path
    cache: Path
    config: Path
    profile_config: Path
    mode: str | None
    home_source: str | None

    def to_json(self) -> dict[str, str | None]:
        payload = asdict(self)
        return {
            key: (str(value) if isinstance(value, Path) else value)
            for key, value in cast(dict[str, Any], payload).items()
        }


def describe_user_data_paths() -> UserDataPaths:
    resolution = current_home_resolution()
    return UserDataPaths(
        home=munkai_home(),
        assets=assets_home(),
        runs=runs_home(),
        operations=operations_home(),
        cache=cache_home(),
        config=config_home(),
        profile_config=profile_config_path(),
        mode=resolution.mode.value if resolution is not None else None,
        home_source=resolution.source.value if resolution is not None else None,
    )

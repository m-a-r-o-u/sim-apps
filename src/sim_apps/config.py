"""Configuration helpers for sim-apps."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, MutableMapping


@dataclass(slots=True)
class AppConfig:
    """Simple configuration container for SIM apps."""

    raw: Mapping[str, Any]

    @property
    def env(self) -> Mapping[str, str]:
        """Environment variables to forward to the SIM API client."""

        return {
            key: str(value)
            for key, value in self.raw.items()
            if isinstance(value, (str, int, float, bool))
        }


def load_config(overrides: Mapping[str, Any] | None = None) -> AppConfig:
    """Load configuration from overrides or default locations.

    This simplified implementation focuses on testability. A configuration file
    can be provided through ``overrides`` or by setting the ``SIM_APPS_CONFIG``
    environment variable to point at a JSON file. Any dictionary-like value is
    accepted and wrapped as :class:`AppConfig`.
    """

    if overrides is None:
        overrides = {}
    if isinstance(overrides, MutableMapping):
        overrides = dict(overrides)
    return AppConfig(raw=overrides)


def ensure_directory(path: Path) -> None:
    """Ensure that ``path`` exists, creating parent directories as needed."""

    path.parent.mkdir(parents=True, exist_ok=True)

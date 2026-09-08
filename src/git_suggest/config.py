"""Frozen configuration model with defaults, merged with an optional TOML file.

Every tunable default in git-suggest lives on `Config` so it is always
overridable via `~/.config/git-suggest/config.toml` (ADR 0006, ADR 0008).
"""

from __future__ import annotations

import functools
import tomllib
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class Config(BaseModel):
    """Immutable, fully-defaulted git-suggest configuration."""

    model_config = ConfigDict(frozen=True)

    backend_order: tuple[str, ...] = ("claude", "copilot", "opencode")
    backend_commands: dict[str, str] = {
        "claude": "claude",
        "copilot": "copilot",
        "opencode": "opencode",
    }
    context_include_readme: bool = True
    context_include_file_listing: bool = True
    context_log_line_count: int = 20
    output_style: str = "auto"  # one of: auto, always, never


def default_config_path() -> Path:
    """Return the default config file path, ~/.config/git-suggest/config.toml."""
    return Path.home() / ".config" / "git-suggest" / "config.toml"


def read_overrides(path: Path) -> dict:
    """Read a TOML config file into a dict, or return {} if it doesn't exist."""
    if not path.is_file():
        return {}
    return tomllib.loads(path.read_text())


def merge_overrides(base: Config, overrides: dict) -> Config:
    """Return a new Config with override keys applied on top of base."""
    return base.model_copy(update=overrides)


def load_config(path: Path | None = None) -> Config:
    """Build the effective Config from defaults merged with an optional TOML file."""
    overrides = read_overrides(path or default_config_path())
    return merge_overrides(Config(), overrides)


@functools.cache
def get_config() -> Config:
    """Return the process-wide Config, loaded and merged from disk once."""
    return load_config()

"""Tests for config loading and override merging."""

from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from git_suggest.config import Config, load_config, merge_overrides, read_overrides


def test_read_overrides_missing_file_returns_empty(tmp_path: Path) -> None:
    """A missing config file yields no overrides."""
    assert read_overrides(tmp_path / "absent.toml") == {}


def test_read_overrides_parses_toml(tmp_path: Path) -> None:
    """An existing config file is parsed into a dict of overrides."""
    path = tmp_path / "config.toml"
    path.write_text('context_log_line_count = 5\noutput_style = "always"\n')
    assert read_overrides(path) == {"context_log_line_count": 5, "output_style": "always"}


def test_load_config_applies_file_overrides(tmp_path: Path) -> None:
    """load_config merges TOML overrides on top of the built-in defaults."""
    path = tmp_path / "config.toml"
    path.write_text("context_include_readme = false\n")
    config = load_config(path)
    assert config.context_include_readme is False
    assert config.backend_order == ("claude", "copilot", "opencode")  # untouched default


def test_load_config_with_no_file_returns_defaults(tmp_path: Path) -> None:
    """load_config falls back to defaults when the config file doesn't exist."""
    config = load_config(tmp_path / "absent.toml")
    assert config == Config()


# Only fields with simple, independently-generatable values are exercised here;
# backend_commands is a dict and covered separately if needed.
_OVERRIDABLE_FIELDS = st.fixed_dictionaries(
    {},
    optional={
        "context_include_readme": st.booleans(),
        "context_include_file_listing": st.booleans(),
        "context_log_line_count": st.integers(min_value=0, max_value=1000),
        "output_style": st.sampled_from(["auto", "always", "never"]),
    },
)


@given(overrides=_OVERRIDABLE_FIELDS)
def test_merge_overrides_property_every_override_wins(overrides: dict) -> None:
    """Every key present in overrides is reflected verbatim on the merged Config."""
    merged = merge_overrides(Config(), overrides)
    for key, value in overrides.items():
        assert getattr(merged, key) == value

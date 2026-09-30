"""Tests for computing and writing this project's CalVer version (ADR 0021)."""

import subprocess
from datetime import date
from pathlib import Path

import pytest

from git_suggest.config import Config
from git_suggest.version import (
    bump_version,
    compute_next_version,
    format_version,
    read_version,
    write_version,
)


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


@pytest.fixture
def repo_with_pyproject(tmp_path: Path) -> Path:
    """A git repo with a pyproject.toml at version 26.09.0."""
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test")
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "example"\nversion = "26.09.0"\n')
    _git(tmp_path, "add", "pyproject.toml")
    _git(tmp_path, "commit", "-q", "-m", "initial")
    return tmp_path


def test_read_version_parses_calver_line(repo_with_pyproject: Path) -> None:
    """read_version extracts (year, month, patch) from the version line."""
    assert read_version(repo_with_pyproject / "pyproject.toml") == (26, 9, 0)


def test_read_version_raises_without_a_calver_line(tmp_path: Path) -> None:
    """read_version raises ValueError when no CalVer version line is present."""
    path = tmp_path / "pyproject.toml"
    path.write_text('[project]\nversion = "0.1.0"\n')
    with pytest.raises(ValueError, match="CalVer"):
        read_version(path)


def test_format_version_zero_pads_year_and_month() -> None:
    """format_version renders two-digit year and month."""
    assert format_version(6, 3, 12) == "06.03.12"


def test_compute_next_version_increments_patch_within_same_month() -> None:
    """Same (year, month) as current: patch increments by 1."""
    assert compute_next_version((26, 9, 0), date(2026, 9, 15)) == "26.09.1"


def test_compute_next_version_resets_patch_on_month_change() -> None:
    """A new (year, month): patch resets to 0."""
    assert compute_next_version((26, 9, 5), date(2026, 10, 1)) == "26.10.0"


def test_compute_next_version_resets_patch_on_year_change() -> None:
    """A new year (even with the same numeric month) resets patch to 0."""
    assert compute_next_version((26, 9, 5), date(2027, 9, 1)) == "27.09.0"


def test_write_version_rewrites_only_the_version_line(repo_with_pyproject: Path) -> None:
    """write_version replaces the version line, leaving the rest of the file intact."""
    path = repo_with_pyproject / "pyproject.toml"
    write_version(path, "26.09.1")
    text = path.read_text()
    assert 'version = "26.09.1"' in text
    assert 'name = "example"' in text


def test_write_version_raises_without_a_calver_line(tmp_path: Path) -> None:
    """write_version raises ValueError when there's no version line to replace."""
    path = tmp_path / "pyproject.toml"
    path.write_text('[project]\nname = "x"\n')
    with pytest.raises(ValueError, match="CalVer"):
        write_version(path, "26.09.1")


def test_bump_version_writes_and_commits(repo_with_pyproject: Path) -> None:
    """bump_version computes, writes, and commits the next version."""
    path = repo_with_pyproject / "pyproject.toml"
    new_version = bump_version(path, Config(), today=date(2026, 9, 20), cwd=repo_with_pyproject)
    assert new_version == "26.09.1"
    assert 'version = "26.09.1"' in path.read_text()
    log = subprocess.run(
        ["git", "log", "-1", "--pretty=%s"],
        cwd=repo_with_pyproject,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert log == "chore(release): bump version to 26.09.1"


def test_bump_version_uses_configured_commit_message_template(repo_with_pyproject: Path) -> None:
    """bump_version formats config.release_commit_message_template with the new version."""
    path = repo_with_pyproject / "pyproject.toml"
    config = Config(release_commit_message_template="release: v{version}")
    bump_version(path, config, today=date(2026, 9, 20), cwd=repo_with_pyproject)
    log = subprocess.run(
        ["git", "log", "-1", "--pretty=%s"],
        cwd=repo_with_pyproject,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert log == "release: v26.09.1"

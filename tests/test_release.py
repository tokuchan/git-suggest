"""Tests for stamping CHANGELOG.md's Unreleased section as a dated release (ADR 0023)."""

import subprocess
from datetime import date
from pathlib import Path

import pytest

from git_suggest.config import Config
from git_suggest.release import (
    derive_repo_url,
    existing_release_versions,
    split_footer,
    stamp_release,
    stamp_unreleased_as_release,
    update_footer_links,
)

_BOOTSTRAP = (
    "# Changelog\n\n## [Unreleased]\n\n## [26.09.0] - 2026-09-30\n\nInitial CalVer release.\n"
)

_FRESH = "# Changelog\n\n## [Unreleased]\n"


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A git repo with CHANGELOG.md already dated at 26.09.0, pyproject.toml bumped to 26.10.0.

    Models the realistic common case: a release already happened for
    26.09.0, a later push bumped the version again, and `release` is now
    being run for the first time to stamp that newer version.
    """
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test")
    _git(tmp_path, "remote", "add", "origin", "git@github.com:tokuchan/git-suggest.git")
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\nversion = "26.09.0"\n')
    (tmp_path / "CHANGELOG.md").write_text(_BOOTSTRAP)
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "initial")
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\nversion = "26.10.0"\n')
    _git(tmp_path, "add", "pyproject.toml")
    _git(tmp_path, "commit", "-q", "-m", "chore(release): bump version to 26.10.0")
    return tmp_path


@pytest.fixture
def fresh_repo(tmp_path: Path) -> Path:
    """A git repo whose CHANGELOG.md has never been released yet (truly first release)."""
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test")
    _git(tmp_path, "remote", "add", "origin", "git@github.com:tokuchan/git-suggest.git")
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\nversion = "26.09.0"\n')
    (tmp_path / "CHANGELOG.md").write_text(_FRESH)
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "initial")
    return tmp_path


def test_stamp_unreleased_as_release_renames_header_and_inserts_fresh_unreleased() -> None:
    """Unreleased's body becomes the new version's body; Unreleased itself stays, now empty."""
    result = stamp_unreleased_as_release(_BOOTSTRAP, "26.10.0", date(2026, 10, 1))
    assert "## [Unreleased]\n\n## [26.10.0] - 2026-10-01\n\n## [26.09.0]" in result


def test_existing_release_versions_in_order() -> None:
    """existing_release_versions lists dated versions, newest-first as they appear."""
    text = "## [Unreleased]\n\n## [26.10.0] - 2026-10-01\n\n## [26.09.0] - 2026-09-30\n"
    assert existing_release_versions(text) == ["26.10.0", "26.09.0"]


def test_existing_release_versions_empty_before_any_release() -> None:
    """An Unreleased-only changelog has no dated release versions yet."""
    assert existing_release_versions("## [Unreleased]\n") == []


def test_derive_repo_url_converts_ssh_remote_to_https(repo: Path) -> None:
    """An ssh-form origin remote is converted to its browsable https URL."""
    assert derive_repo_url(cwd=repo) == "https://github.com/tokuchan/git-suggest"


def test_split_footer_with_no_existing_links() -> None:
    """split_footer returns no footer lines when the changelog has none yet."""
    body, lines = split_footer(_BOOTSTRAP)
    assert lines == []
    assert body == _BOOTSTRAP.rstrip("\n")


def test_split_footer_extracts_existing_link_lines() -> None:
    """split_footer separates the body from trailing compare-link lines."""
    text = _BOOTSTRAP + "\n[Unreleased]: https://example.com/compare/a...HEAD\n"
    body, lines = split_footer(text)
    assert lines == ["[Unreleased]: https://example.com/compare/a...HEAD"]
    assert body == _BOOTSTRAP.rstrip("\n")


def test_update_footer_links_adds_unreleased_and_version_links() -> None:
    """update_footer_links adds both an Unreleased link and a new version's compare link."""
    result = update_footer_links(
        body="# Changelog",
        footer_lines=[],
        new_version="26.10.0",
        prev_version="26.09.0",
        new_endpoint="sha-new",
        prev_endpoint="sha-prev",
        repo_url="https://github.com/tokuchan/git-suggest",
    )
    assert "[Unreleased]: https://github.com/tokuchan/git-suggest/compare/sha-new...HEAD" in result
    assert "[26.10.0]: https://github.com/tokuchan/git-suggest/compare/sha-prev...sha-new" in result


def test_update_footer_links_omits_version_link_for_the_first_ever_release() -> None:
    """With no prior version, only the Unreleased link is added -- no compare link for it."""
    result = update_footer_links(
        body="# Changelog",
        footer_lines=[],
        new_version="26.09.0",
        prev_version=None,
        new_endpoint="sha-new",
        prev_endpoint=None,
        repo_url="https://example.com/x",
    )
    assert "[Unreleased]: https://example.com/x/compare/sha-new...HEAD" in result
    assert "[26.09.0]:" not in result


def test_stamp_release_first_ever_release_gets_no_compare_link(fresh_repo: Path) -> None:
    """The first-ever release stamps a dated header but no compare link for itself."""
    new_version = stamp_release(
        fresh_repo / "CHANGELOG.md",
        fresh_repo / "pyproject.toml",
        Config(),
        cwd=fresh_repo,
        today=date(2026, 9, 30),
    )
    assert new_version == "26.09.0"
    text = (fresh_repo / "CHANGELOG.md").read_text()
    assert "## [26.09.0] - 2026-09-30" in text
    assert "[26.09.0]:" not in text  # first-ever release: no compare link
    assert "[Unreleased]: https://github.com/tokuchan/git-suggest/compare/" in text

    log = subprocess.run(
        ["git", "log", "-1", "--pretty=%s"],
        cwd=fresh_repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert log == "docs(changelog): release 26.09.0"


def test_stamp_release_links_back_to_the_previous_release(repo: Path) -> None:
    """A release's compare link spans from the previous release's endpoint to its own."""
    stamp_release(
        repo / "CHANGELOG.md", repo / "pyproject.toml", Config(), cwd=repo, today=date(2026, 10, 1)
    )
    text = (repo / "CHANGELOG.md").read_text()
    assert "## [26.10.0] - 2026-10-01" in text
    link_line = next(line for line in text.splitlines() if line.startswith("[26.10.0]:"))
    assert "..." in link_line
    first_endpoint, _, second_endpoint = link_line.partition("compare/")[2].partition("...")
    assert first_endpoint != second_endpoint

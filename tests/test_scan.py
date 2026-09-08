"""Tests for the scan report builder, using a real temporary git repository."""

import subprocess
from pathlib import Path

import pytest

from git_suggest.scan import (
    build_scan_report,
    format_binary_entry,
    has_staged_changes,
    parse_numstat_line,
    staged_files,
)


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A git repo with one committed file, ready for staged changes."""
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test")
    (tmp_path / "existing.txt").write_text("line one\n")
    _git(tmp_path, "add", "existing.txt")
    _git(tmp_path, "commit", "-q", "-m", "initial")
    return tmp_path


def test_parse_numstat_line_text_file() -> None:
    """A text-file numstat line reports added/deleted counts and is not binary."""
    assert parse_numstat_line("1\t0\tfoo.py") == ("foo.py", False)


def test_parse_numstat_line_binary_file() -> None:
    """A binary-file numstat line uses '-' counts and is flagged binary."""
    assert parse_numstat_line("-\t-\timage.png") == ("image.png", True)


def test_staged_files_lists_modified_text_file(repo: Path) -> None:
    """A staged text-file modification is reported as non-binary."""
    (repo / "existing.txt").write_text("line one\nline two\n")
    _git(repo, "add", "existing.txt")
    assert staged_files(cwd=repo) == [("existing.txt", False)]


def test_staged_files_lists_binary_file(repo: Path) -> None:
    """A staged binary file (containing a NUL byte) is reported as binary."""
    (repo / "blob.bin").write_bytes(b"\x00\x01\x02")
    _git(repo, "add", "blob.bin")
    assert staged_files(cwd=repo) == [("blob.bin", True)]


def test_build_scan_report_includes_full_text_diff(repo: Path) -> None:
    """The report includes the full diff hunk for a staged text-file change."""
    (repo / "existing.txt").write_text("line one\nline two\n")
    _git(repo, "add", "existing.txt")
    report = build_scan_report(cwd=repo)
    assert "existing.txt" in report
    assert "+line two" in report


def test_build_scan_report_omits_binary_content(repo: Path) -> None:
    """The report lists a binary file by name only, without its content."""
    (repo / "blob.bin").write_bytes(b"\x00\x01\x02\x03")
    _git(repo, "add", "blob.bin")
    assert build_scan_report(cwd=repo) == format_binary_entry("blob.bin")


def test_has_staged_changes_false_with_nothing_staged(repo: Path) -> None:
    """has_staged_changes is False right after a clean commit."""
    assert has_staged_changes(cwd=repo) is False


def test_has_staged_changes_true_with_a_staged_change(repo: Path) -> None:
    """has_staged_changes is True once a change is staged."""
    (repo / "existing.txt").write_text("line one\nline two\n")
    _git(repo, "add", "existing.txt")
    assert has_staged_changes(cwd=repo) is True


def test_build_scan_report_is_empty_with_nothing_staged(repo: Path) -> None:
    """build_scan_report short-circuits to an empty string with nothing staged."""
    assert build_scan_report(cwd=repo) == ""

"""Tests for the scan report builder, using a real temporary git repository."""

import subprocess
from pathlib import Path

import pytest

from git_suggest.config import Config
from git_suggest.scan import (
    build_scan_report,
    current_branch,
    format_binary_entry,
    format_subject_budget_line,
    has_staged_changes,
    parse_numstat_line,
    staged_files,
    subject_budget,
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
    report = build_scan_report(cwd=repo)
    assert report.startswith("# subject-budget: max=72 preferred=50\n\n")
    assert report.endswith(format_binary_entry("blob.bin"))


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


def test_subject_budget_with_no_reference_uses_config_defaults() -> None:
    """With no reference, the budget is exactly the configured max/preferred."""
    assert subject_budget(None, Config()) == (72, 50)


def test_subject_budget_reduced_by_reference_prefix_length() -> None:
    """A reference prefix's length (plus ': ') is subtracted from both budgets."""
    # "AMCC-12202: " is 12 characters.
    assert subject_budget("AMCC-12202", Config()) == (72 - 12, 50 - 12)


def test_subject_budget_preferred_floors_at_zero_for_a_long_reference() -> None:
    """preferred never goes negative even if the reference alone exceeds it."""
    long_reference = "X" * 60
    max_len, preferred_len = subject_budget(long_reference, Config())
    assert preferred_len == 0
    assert max_len == 72 - len(long_reference) - 2


def test_format_subject_budget_line() -> None:
    """The budget line has the expected machine-readable shape."""
    assert format_subject_budget_line(65, 43) == "# subject-budget: max=65 preferred=43"


def test_build_scan_report_embeds_subject_budget_line(repo: Path) -> None:
    """The report always starts with a subject-budget line, reference or not."""
    (repo / "existing.txt").write_text("line one\nline two\n")
    _git(repo, "add", "existing.txt")
    report = build_scan_report(cwd=repo, reference="AMCC-12202")
    assert report.startswith("# subject-budget: max=60 preferred=38\n\n")


def test_current_branch_returns_branch_name(repo: Path) -> None:
    """current_branch reports the checked-out branch name verbatim."""
    _git(repo, "checkout", "-q", "-b", "feature/AMCC-12202")
    assert current_branch(cwd=repo) == "feature/AMCC-12202"

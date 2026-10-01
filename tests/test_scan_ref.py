"""Tests for scan-ref's refspec handling and report building (ADR 0024)."""

import subprocess
from pathlib import Path

import pytest

from git_suggest.scan_ref import build_ref_scan_report, diff_args_for_refspec, is_range


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A git repo with two commits, the second modifying the first's file."""
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test")
    (tmp_path / "existing.txt").write_text("line one\n")
    _git(tmp_path, "add", "existing.txt")
    _git(tmp_path, "commit", "-q", "-m", "initial")
    (tmp_path / "existing.txt").write_text("line one\nline two\n")
    _git(tmp_path, "add", "existing.txt")
    _git(tmp_path, "commit", "-q", "-m", "second")
    return tmp_path


def test_is_range_detects_two_dot_range() -> None:
    """A refspec containing '..' is a range."""
    assert is_range("HEAD~3..HEAD") is True


def test_is_range_detects_three_dot_range() -> None:
    """A refspec containing '...' is also a range."""
    assert is_range("main...feature") is True


def test_is_range_false_for_a_bare_single_ref() -> None:
    """A bare ref with no '..' is not a range."""
    assert is_range("HEAD~2") is False


def test_diff_args_for_refspec_passes_a_range_straight_through() -> None:
    """A range refspec is passed to `git diff` unchanged."""
    assert diff_args_for_refspec("HEAD~3..HEAD") == ["HEAD~3..HEAD"]


def test_diff_args_for_refspec_a_single_ref_means_vs_its_parent() -> None:
    """A single ref becomes `<ref>^..<ref>`, not a literal `git diff <ref>`."""
    assert diff_args_for_refspec("HEAD~2") == ["HEAD~2^..HEAD~2"]


def test_build_ref_scan_report_single_ref_is_that_commits_own_diff(repo: Path) -> None:
    """A single ref's report shows what that commit itself changed, not working-tree diff."""
    report = build_ref_scan_report("HEAD", cwd=repo)
    assert "existing.txt" in report
    assert "+line two" in report


def test_build_ref_scan_report_range_flattens_the_whole_range(repo: Path) -> None:
    """A range's report is one flattened diff across every commit in it."""
    report = build_ref_scan_report("HEAD~1..HEAD", cwd=repo)
    assert "existing.txt" in report
    assert "+line two" in report


def test_build_ref_scan_report_embeds_subject_budget_line(repo: Path) -> None:
    """scan-ref's report starts with the same subject-budget line as staged scan."""
    report = build_ref_scan_report("HEAD", cwd=repo)
    assert report.startswith("# subject-budget: max=72 preferred=50\n\n")

"""Tests confirming step-by-step progress is logged at INFO level."""

import logging
import subprocess
from pathlib import Path

import pytest

from git_suggest.backends import get_backend_runner
from git_suggest.config import Config
from git_suggest.draft import gather_context
from git_suggest.model import ChangelogEntry, ChangelogSections, CommitType, DraftDocument
from git_suggest.render import render_commit_message
from git_suggest.scan import build_scan_report


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A git repo with one staged text-file change."""
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test")
    (tmp_path / "existing.txt").write_text("line one\n")
    _git(tmp_path, "add", "existing.txt")
    _git(tmp_path, "commit", "-q", "-m", "initial")
    (tmp_path / "existing.txt").write_text("line one\nline two\n")
    _git(tmp_path, "add", "existing.txt")
    return tmp_path


def test_build_scan_report_logs_progress(repo: Path, caplog: pytest.LogCaptureFixture) -> None:
    """build_scan_report emits an INFO message describing the scan step."""
    with caplog.at_level(logging.INFO, logger="git_suggest.scan"):
        build_scan_report(cwd=repo)
    assert any("Scanning staged changes" in message for message in caplog.messages)


def test_gather_context_logs_progress(repo: Path, caplog: pytest.LogCaptureFixture) -> None:
    """gather_context emits an INFO message describing the context-gathering step."""
    with caplog.at_level(logging.INFO, logger="git_suggest.draft"):
        gather_context(Config(), cwd=repo)
    assert any("Gathering project context" in message for message in caplog.messages)


def test_render_commit_message_logs_progress(caplog: pytest.LogCaptureFixture) -> None:
    """render_commit_message emits an INFO message describing the render step."""
    doc = DraftDocument(
        type=CommitType.FEAT,
        description="demo",
        changelog=ChangelogSections(
            added=[
                ChangelogEntry(affected_file="a.py", project_context="c", change_statement="Add a.")
            ]
        ),
    )
    with caplog.at_level(logging.INFO, logger="git_suggest.render"):
        render_commit_message(doc)
    assert any("Rendering commit message" in message for message in caplog.messages)


def test_get_backend_runner_logs_warning_when_none_available(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """resolve_backend logs a warning when no configured backend is available."""
    monkeypatch.setattr("git_suggest.backends.is_available", lambda command: False)
    with caplog.at_level(logging.WARNING, logger="git_suggest.backends"):
        get_backend_runner(Config())
    assert any("No configured AI backend found" in message for message in caplog.messages)

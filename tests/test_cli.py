"""Tests for the CLI wiring: scan/draft/render subcommands and the bare chain."""

import json
import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from git_suggest.cli import commit_with_message, main
from git_suggest.model import ChangelogSections, CommitType, DraftDocument


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


@pytest.fixture
def staged_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A git repo, made cwd, with one staged text-file change."""
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test")
    (tmp_path / "existing.txt").write_text("line one\n")
    _git(tmp_path, "add", "existing.txt")
    _git(tmp_path, "commit", "-q", "-m", "initial")
    (tmp_path / "existing.txt").write_text("line one\nline two\n")
    _git(tmp_path, "add", "existing.txt")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _sample_draft_json() -> str:
    doc = DraftDocument(
        type=CommitType.FEAT,
        scope="cli",
        description="wire up subcommands",
        changelog=ChangelogSections(added=[]),
    )
    return doc.model_dump_json()


def test_scan_command_reports_staged_diff(staged_repo: Path) -> None:
    """`git-suggest scan` prints a report including the staged diff."""
    result = CliRunner().invoke(main, ["scan"])
    assert result.exit_code == 0
    assert "existing.txt" in result.output
    assert "+line two" in result.output


def test_render_command_prints_commit_message() -> None:
    """`git-suggest render` turns draft JSON on stdin into a commit message."""
    result = CliRunner().invoke(main, ["render"], input=_sample_draft_json())
    assert result.exit_code == 0
    assert result.output.strip() == "feat(cli): wire up subcommands"


def test_render_command_changelog_only(staged_repo: Path) -> None:
    """`git-suggest render --changelog-only` omits the commit header."""
    doc = DraftDocument(
        type=CommitType.FIX,
        description="fix bug",
        changelog=ChangelogSections(
            fixed=[
                {
                    "affected_file": "a.py",
                    "project_context": "x",
                    "change_statement": "Fix the bug.",
                }
            ]
        ),
    )
    result = CliRunner().invoke(main, ["render", "--changelog-only"], input=doc.model_dump_json())
    assert result.exit_code == 0
    assert "fix:" not in result.output
    assert "Fix the bug." in result.output


def test_draft_command_uses_backend_runner(monkeypatch: pytest.MonkeyPatch) -> None:
    """`git-suggest draft` calls the resolved backend runner and prints valid JSON."""
    monkeypatch.setattr(
        "git_suggest.cli.require_backend_runner", lambda config: lambda prompt: _sample_draft_json()
    )
    result = CliRunner().invoke(main, ["draft"], input="## a.py\n+x")
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["type"] == "feat"


def test_bare_command_prints_message_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bare `git-suggest` chains scan/draft/render and prints plain text (piped)."""
    monkeypatch.setattr("git_suggest.cli.build_scan_report", lambda: "## a.py\n+x")
    monkeypatch.setattr(
        "git_suggest.cli.require_backend_runner", lambda config: lambda prompt: _sample_draft_json()
    )
    result = CliRunner().invoke(main, [])
    assert result.exit_code == 0
    assert result.output.strip() == "feat(cli): wire up subcommands"


def test_commit_with_message_builds_expected_args(monkeypatch: pytest.MonkeyPatch) -> None:
    """commit_with_message runs `git commit -F -` (or with -e) fed the message via stdin."""
    captured = {}

    def fake_run(args: list[str], **kwargs: object) -> None:
        captured["args"] = args
        captured["input"] = kwargs.get("input")

    monkeypatch.setattr("git_suggest.cli.subprocess.run", fake_run)
    commit_with_message("feat: x", edit=True)
    assert captured["args"] == ["git", "commit", "-e", "-F", "-"]
    assert captured["input"] == "feat: x"


def test_bare_command_commit_flag_invokes_git_commit(
    staged_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--commit runs `git commit -F -` fed with the rendered message."""
    monkeypatch.setattr(
        "git_suggest.cli.require_backend_runner", lambda config: lambda prompt: _sample_draft_json()
    )
    captured = {}

    def fake_commit_with_message(message: str, edit: bool) -> None:
        captured["message"] = message
        captured["edit"] = edit

    monkeypatch.setattr("git_suggest.cli.commit_with_message", fake_commit_with_message)
    result = CliRunner().invoke(main, ["--commit"])
    assert result.exit_code == 0
    assert captured["edit"] is False
    assert captured["message"] == "feat(cli): wire up subcommands"

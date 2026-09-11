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


def test_scan_command_writes_to_output_path(staged_repo: Path) -> None:
    """`-o/--output-path` writes the report to a file instead of stdout."""
    out_file = staged_repo / "out.txt"
    result = CliRunner().invoke(main, ["scan", "-o", str(out_file)])
    assert result.exit_code == 0
    assert "existing.txt" not in result.output
    assert "existing.txt" in out_file.read_text()


def test_scan_command_output_path_dash_means_stdout(staged_repo: Path) -> None:
    """Passing '-' to --output-path prints to stdout, same as omitting the flag."""
    result = CliRunner().invoke(main, ["scan", "--output-path", "-"])
    assert result.exit_code == 0
    assert "existing.txt" in result.output


def test_scan_command_append_adds_to_existing_file(staged_repo: Path) -> None:
    """-a/--append appends to the target file instead of truncating it."""
    out_file = staged_repo / "out.txt"
    out_file.write_text("PRIOR\n")
    result = CliRunner().invoke(main, ["scan", "-o", str(out_file), "-a"])
    assert result.exit_code == 0
    content = out_file.read_text()
    assert content.startswith("PRIOR\n")
    assert "existing.txt" in content


def test_scan_command_append_without_output_path_is_ignored(staged_repo: Path) -> None:
    """-a/--append with no --output-path (stdout target) is silently ignored, not an error."""
    result = CliRunner().invoke(main, ["scan", "-a"])
    assert result.exit_code == 0
    assert "existing.txt" in result.output


def test_render_command_input_dash_means_stdin() -> None:
    """Passing '-' to --input reads from stdin explicitly, same as omitting the flag."""
    result = CliRunner().invoke(main, ["render", "--input", "-"], input=_sample_draft_json())
    assert result.exit_code == 0
    assert result.stdout.strip() == "feat(cli): wire up subcommands"


def test_scan_command_reference_reduces_embedded_budget(staged_repo: Path) -> None:
    """-r/--reference embeds a subject-budget line reduced by the reference's length."""
    result = CliRunner().invoke(main, ["scan", "-r", "AMCC-12202"])
    assert result.exit_code == 0
    assert "# subject-budget: max=60 preferred=38" in result.output


def test_scan_command_branch_reference_uses_current_branch(staged_repo: Path) -> None:
    """-b/--branch-reference reduces the budget using the current branch name's length."""
    subprocess.run(["git", "checkout", "-q", "-b", "feature-x"], cwd=staged_repo, check=True)
    result = CliRunner().invoke(main, ["scan", "-b"])
    assert result.exit_code == 0
    # "feature-x: " is 11 characters.
    assert "# subject-budget: max=61 preferred=39" in result.output


def test_scan_command_reference_and_branch_reference_conflict(staged_repo: Path) -> None:
    """Passing both -r and -b is a hard error (mutually exclusive)."""
    result = CliRunner().invoke(main, ["scan", "-r", "AMCC-12202", "-b"])
    assert result.exit_code != 0
    assert "mutually exclusive" in result.output


def test_render_command_prints_commit_message() -> None:
    """`git-suggest render` turns draft JSON on stdin into a commit message."""
    result = CliRunner().invoke(main, ["render"], input=_sample_draft_json())
    assert result.exit_code == 0
    assert result.stdout.strip() == "feat(cli): wire up subcommands"


def test_render_command_reference_prefixes_the_header() -> None:
    """`git-suggest render -r AMCC-12202` prefixes the subject line."""
    result = CliRunner().invoke(main, ["render", "-r", "AMCC-12202"], input=_sample_draft_json())
    assert result.exit_code == 0
    assert result.stdout.strip() == "AMCC-12202: feat(cli): wire up subcommands"


def test_render_command_reference_and_branch_reference_conflict() -> None:
    """Passing both -r and -b to render is a hard error."""
    result = CliRunner().invoke(
        main, ["render", "-r", "AMCC-12202", "-b"], input=_sample_draft_json()
    )
    assert result.exit_code != 0
    assert "mutually exclusive" in result.output


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
    parsed = json.loads(result.stdout)
    assert parsed["type"] == "feat"


def test_bare_command_prints_message_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bare `git-suggest` chains scan/draft/render and prints plain text (piped)."""
    monkeypatch.setattr("git_suggest.cli.build_scan_report", lambda **kwargs: "## a.py\n+x")
    monkeypatch.setattr(
        "git_suggest.cli.require_backend_runner", lambda config: lambda prompt: _sample_draft_json()
    )
    result = CliRunner().invoke(main, [])
    assert result.exit_code == 0
    assert result.stdout.strip() == "feat(cli): wire up subcommands"


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


def test_bare_command_uses_spinner_when_forced_on(
    staged_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When select_output_mode is forced to spinner mode, the chain still works."""
    monkeypatch.setattr(
        "git_suggest.cli.select_output_mode", lambda is_tty, want_log, level: "spinner"
    )
    monkeypatch.setattr(
        "git_suggest.cli.require_backend_runner", lambda config: lambda prompt: _sample_draft_json()
    )
    result = CliRunner().invoke(main, [])
    assert result.exit_code == 0
    assert "feat(cli): wire up subcommands" in result.output


def test_bare_command_uses_log_mode_when_requested(
    staged_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--log forces log mode, and the chain still produces the right message."""
    monkeypatch.setattr(
        "git_suggest.cli.require_backend_runner", lambda config: lambda prompt: _sample_draft_json()
    )
    result = CliRunner().invoke(main, ["--log"])
    assert result.exit_code == 0
    assert "feat(cli): wire up subcommands" in result.output


def test_bare_command_short_circuits_with_no_staged_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bare `git-suggest` exits without calling the backend when nothing is staged."""
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test")
    (tmp_path / "a.txt").write_text("hello\n")
    _git(tmp_path, "add", "a.txt")
    _git(tmp_path, "commit", "-q", "-m", "initial")
    monkeypatch.chdir(tmp_path)

    called = {"backend": False}

    def fake_require_backend_runner(config: object) -> object:
        called["backend"] = True
        raise AssertionError("backend should not be invoked with nothing staged")

    monkeypatch.setattr("git_suggest.cli.require_backend_runner", fake_require_backend_runner)
    result = CliRunner().invoke(main, [])
    assert result.exit_code == 0
    assert called["backend"] is False
    assert "No staged changes" in result.output


def test_draft_command_short_circuits_with_empty_input(monkeypatch: pytest.MonkeyPatch) -> None:
    """`git-suggest draft` exits without calling the backend when stdin is empty."""
    called = {"backend": False}

    def fake_require_backend_runner(config: object) -> object:
        called["backend"] = True
        raise AssertionError("backend should not be invoked with empty input")

    monkeypatch.setattr("git_suggest.cli.require_backend_runner", fake_require_backend_runner)
    result = CliRunner().invoke(main, ["draft"], input="   \n")
    assert result.exit_code == 0
    assert called["backend"] is False
    assert "No staged changes" in result.output

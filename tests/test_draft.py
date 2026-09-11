"""Tests for the draft subcommand's context gathering, prompting, and parsing."""

import json
import subprocess
from pathlib import Path

import pytest

from git_suggest.config import Config
from git_suggest.draft import (
    build_length_retry_prompt,
    build_prompt,
    enforce_subject_length,
    extract_json_object,
    find_readme,
    gather_context,
    parse_draft_response,
    parse_length_retry_response,
    parse_subject_budget,
    run_draft,
)
from git_suggest.model import CommitType, DraftDocument


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A git repo with a README and one commit."""
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test")
    (tmp_path / "README.md").write_text("# Example project\n")
    (tmp_path / "existing.txt").write_text("line one\n")
    _git(tmp_path, "add", "README.md", "existing.txt")
    _git(tmp_path, "commit", "-q", "-m", "initial commit")
    return tmp_path


def test_find_readme_reads_first_match(repo: Path) -> None:
    """find_readme returns the content of a top-level README file."""
    assert find_readme(cwd=repo) == "# Example project\n"


def test_find_readme_returns_empty_when_absent(tmp_path: Path) -> None:
    """find_readme returns "" when no README exists."""
    assert find_readme(cwd=tmp_path) == ""


def test_gather_context_includes_configured_sections(repo: Path) -> None:
    """gather_context includes file listing, README, and recent log per config."""
    context = gather_context(Config(), cwd=repo)
    assert "# Tracked files" in context
    assert "existing.txt" in context
    assert "# README" in context
    assert "# Recent commits" in context
    assert "initial commit" in context


def test_gather_context_omits_disabled_sections(repo: Path) -> None:
    """gather_context skips a section when its config flag is off."""
    config = Config(context_include_readme=False, context_include_file_listing=False)
    context = gather_context(config, cwd=repo)
    assert "# README" not in context
    assert "# Tracked files" not in context
    assert "# Recent commits" in context


def test_build_prompt_includes_schema_context_and_scan_report() -> None:
    """build_prompt embeds the JSON schema, context, and scan report."""
    prompt = build_prompt(scan_report="## file.py\n+added", context="# Tracked files\nfile.py")
    assert '"DraftDocument"' in prompt or "properties" in prompt
    assert "## file.py" in prompt
    assert "# Tracked files" in prompt


def test_extract_json_object_strips_surrounding_commentary() -> None:
    """extract_json_object pulls out the JSON object even with text around it."""
    raw = 'Sure, here you go:\n{"type": "fix"}\nHope that helps!'
    assert extract_json_object(raw) == '{"type": "fix"}'


def test_extract_json_object_raises_when_no_object_present() -> None:
    """extract_json_object raises ValueError when no braces are found."""
    with pytest.raises(ValueError, match="No JSON object"):
        extract_json_object("no json here")


def _draft_json() -> str:
    return json.dumps(
        {
            "type": "fix",
            "scope": None,
            "description": "correct off-by-one error",
            "changelog": {
                "fixed": [
                    {
                        "affected_file": "src/app.py",
                        "project_context": "loop bounds",
                        "change_statement": "Fix off-by-one error in loop.",
                    }
                ]
            },
        }
    )


def test_parse_draft_response_validates_into_draft_document() -> None:
    """parse_draft_response turns raw AI text into a validated DraftDocument."""
    doc = parse_draft_response(f"```json\n{_draft_json()}\n```")
    assert doc.type == CommitType.FIX
    assert doc.changelog.fixed[0].affected_file == "src/app.py"


def test_run_draft_composes_context_prompt_and_runner(repo: Path) -> None:
    """run_draft calls the runner with a built prompt and parses its response."""
    captured_prompts = []

    def fake_runner(prompt: str) -> str:
        captured_prompts.append(prompt)
        return _draft_json()

    doc = run_draft("## existing.txt\n+line two", fake_runner, Config(), cwd=repo)
    assert isinstance(doc, DraftDocument)
    assert doc.type == CommitType.FIX
    assert "## existing.txt" in captured_prompts[0]


def test_parse_subject_budget_reads_embedded_line() -> None:
    """parse_subject_budget extracts max/preferred from scan's leading budget line."""
    scan_report = "# subject-budget: max=60 preferred=38\n\n## file.py\n+x"
    assert parse_subject_budget(scan_report, Config()) == (60, 38)


def test_parse_subject_budget_falls_back_to_config_defaults() -> None:
    """Without a budget line, parse_subject_budget falls back to config defaults."""
    assert parse_subject_budget("## file.py\n+x", Config()) == (72, 50)


def test_build_prompt_includes_budget_instructions() -> None:
    """build_prompt tells the AI the max/preferred subject-length budget."""
    prompt = build_prompt("## file.py\n+x", "context", max_len=60, preferred_len=38)
    assert "60 characters" in prompt
    assert "38 characters" in prompt


def test_build_length_retry_prompt_reports_actual_and_target_lengths() -> None:
    """The retry prompt states the current header, its length, and both budgets."""
    doc = DraftDocument(type=CommitType.FEAT, scope="cli", description="a very long description")
    prompt = build_length_retry_prompt(doc, max_len=20, preferred_len=10)
    assert "feat(cli): a very long description" in prompt
    assert "20-character" in prompt
    assert '"description"' in prompt


def test_parse_length_retry_response_extracts_description() -> None:
    """parse_length_retry_response pulls the description field out of the reply."""
    assert parse_length_retry_response('{"description": "shorter"}') == "shorter"


def test_enforce_subject_length_returns_doc_unchanged_when_already_within_budget() -> None:
    """No retry happens if the initial subject already fits."""
    doc = DraftDocument(type=CommitType.FIX, description="fix bug")

    def fail_runner(prompt: str) -> str:
        raise AssertionError("runner should not be called when already within budget")

    result = enforce_subject_length(doc, fail_runner, max_len=72, preferred_len=50, attempts=3)
    assert result is doc


def test_enforce_subject_length_retries_until_it_fits() -> None:
    """A too-long description is retried until a shorter one fits."""
    doc = DraftDocument(type=CommitType.FEAT, description="x" * 60)
    responses = iter(
        ['{"description": "still too long xxxxxxxxxxxxxxxxxxxx"}', '{"description": "short"}']
    )

    def runner(prompt: str) -> str:
        return next(responses)

    result = enforce_subject_length(doc, runner, max_len=20, preferred_len=10, attempts=3)
    assert result.description == "short"


def test_enforce_subject_length_falls_back_to_shortest_after_exhausting_attempts() -> None:
    """After exhausting attempts, the shortest attempt is used and a warning logged."""
    doc = DraftDocument(type=CommitType.FEAT, description="x" * 60)
    responses = iter(
        [
            '{"description": "aaaaaaaaaaaaaaaaaaaa"}',
            '{"description": "bbbbbbbbbb"}',
            '{"description": "ccccccccccccccccccccccccccc"}',
        ]
    )

    def runner(prompt: str) -> str:
        return next(responses)

    result = enforce_subject_length(doc, runner, max_len=5, preferred_len=1, attempts=3)
    assert result.description == "bbbbbbbbbb"

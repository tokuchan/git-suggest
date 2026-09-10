"""Tests for AI backend detection and invocation."""

import subprocess

import pytest

from git_suggest.backends import (
    bare_stdin_args,
    claude_args,
    get_backend_runner,
    invoke_backend,
    resolve_backend,
    run_subcommand_args,
)
from git_suggest.config import Config


def test_claude_args_shape() -> None:
    """claude_args builds `<command> -p <fixed query>`, with the real prompt fed via stdin."""
    args = claude_args("claude")
    assert args[:2] == ["claude", "-p"]
    assert len(args) == 3 and args[2]


def test_bare_stdin_args_shape() -> None:
    """bare_stdin_args builds `<command>` alone, with the prompt fed via stdin."""
    assert bare_stdin_args("copilot") == ["copilot"]


def test_run_subcommand_args_shape() -> None:
    """run_subcommand_args builds `<command> run`, with the prompt fed via stdin."""
    assert run_subcommand_args("opencode") == ["opencode", "run"]


def test_resolve_backend_picks_first_available(monkeypatch: pytest.MonkeyPatch) -> None:
    """resolve_backend returns the first name in order whose command is on PATH."""
    available = {"copilot"}
    monkeypatch.setattr("git_suggest.backends.is_available", lambda command: command in available)
    commands = {"claude": "claude", "copilot": "copilot", "opencode": "opencode"}
    assert resolve_backend(("claude", "copilot", "opencode"), commands) == "copilot"


def test_resolve_backend_returns_none_when_nothing_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """resolve_backend returns None if no configured backend is available."""
    monkeypatch.setattr("git_suggest.backends.is_available", lambda command: False)
    commands = {"claude": "claude"}
    assert resolve_backend(("claude",), commands) is None


def test_invoke_backend_runs_subprocess_and_returns_stdout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """invoke_backend's returned run() invokes the built args, feeding prompt via stdin."""
    captured = {}

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        captured["args"] = args
        captured["input"] = kwargs.get("input")
        return subprocess.CompletedProcess(args, 0, stdout="{}", stderr="")

    monkeypatch.setattr("git_suggest.backends.subprocess.run", fake_run)
    run = invoke_backend("copilot", "copilot")
    assert run("write a commit message") == "{}"
    assert captured["args"] == ["copilot"]
    assert captured["input"] == "write a commit message"


def test_get_backend_runner_returns_none_when_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """get_backend_runner returns None when no configured backend resolves."""
    monkeypatch.setattr("git_suggest.backends.is_available", lambda command: False)
    assert get_backend_runner(Config()) is None

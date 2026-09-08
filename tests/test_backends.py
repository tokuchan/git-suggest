"""Tests for AI backend detection and invocation."""

import subprocess

import pytest

from git_suggest.backends import (
    get_backend_runner,
    invoke_backend,
    print_flag_args,
    resolve_backend,
    run_subcommand_args,
)
from git_suggest.config import Config


def test_print_flag_args_shape() -> None:
    """print_flag_args builds `<command> -p <prompt>`."""
    assert print_flag_args("claude", "hello") == ["claude", "-p", "hello"]


def test_run_subcommand_args_shape() -> None:
    """run_subcommand_args builds `<command> run <prompt>`."""
    assert run_subcommand_args("opencode", "hello") == ["opencode", "run", "hello"]


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
    """invoke_backend's returned run() invokes the built args and returns stdout."""
    captured = {}

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        captured["args"] = args
        return subprocess.CompletedProcess(args, 0, stdout="{}", stderr="")

    monkeypatch.setattr("git_suggest.backends.subprocess.run", fake_run)
    run = invoke_backend("claude", "claude")
    assert run("write a commit message") == "{}"
    assert captured["args"] == ["claude", "-p", "write a commit message"]


def test_get_backend_runner_returns_none_when_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """get_backend_runner returns None when no configured backend resolves."""
    monkeypatch.setattr("git_suggest.backends.is_available", lambda command: False)
    assert get_backend_runner(Config()) is None

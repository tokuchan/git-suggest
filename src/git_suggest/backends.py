"""Detect and invoke the first working AI backend CLI (ADR 0002, ADR 0007).

Invocation is exposed as curried functions (`invoke_backend` returns a
`run(prompt) -> str` function) rather than a stateful "backend manager"
object.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from collections.abc import Callable

from git_suggest.config import Config

logger = logging.getLogger(__name__)


def is_available(command: str) -> bool:
    """Return True if command resolves to an executable on PATH."""
    return shutil.which(command) is not None


def resolve_backend(order: tuple[str, ...], commands: dict[str, str]) -> str | None:
    """Return the first backend name in order whose command is available on PATH."""
    for name in order:
        command = commands.get(name, name)
        logger.debug("Checking AI backend %r (command=%r)", name, command)
        if is_available(command):
            logger.info("Using AI backend: %s", name)
            return name
    logger.warning("No configured AI backend found on PATH (tried: %s)", ", ".join(order))
    return None


#: Fixed, short instruction passed as claude's `-p` argument; the actual
#: (potentially huge) prompt travels via stdin instead, which claude folds
#: into context automatically (documented `cat file | claude -p "query"`
#: pattern). Keeping this argument short means it never risks the OS
#: per-argument length limit, no matter how large the real prompt gets.
_CLAUDE_STDIN_QUERY = "Follow the instructions in the piped stdin input and respond accordingly."


def claude_args(command: str) -> list[str]:
    """Build args for claude: `<command> -p "<fixed query>"`, prompt piped via stdin."""
    return [command, "-p", _CLAUDE_STDIN_QUERY]


def bare_stdin_args(command: str) -> list[str]:
    """Build args for CLIs that read a one-shot prompt from stdin with no flag (copilot)."""
    return [command]


def run_subcommand_args(command: str) -> list[str]:
    """Build args for CLIs invoked as `<command> run`, prompt piped via stdin (opencode)."""
    return [command, "run"]


#: Per-backend argument builders, keyed by backend name.
ARG_BUILDERS: dict[str, Callable[[str], list[str]]] = {
    "claude": claude_args,
    "copilot": bare_stdin_args,
    "opencode": run_subcommand_args,
}


def invoke_backend(name: str, command: str) -> Callable[[str], str]:
    """Return a curried run(prompt) -> stdout function for the given backend.

    The prompt is fed via stdin rather than as a command-line argument.
    Passing large prompts as argv risks the OS per-argument length limit
    (Linux's ~128KiB MAX_ARG_STRLEN), which large repos with lots of
    gathered context can easily exceed; each backend has its own way of
    accepting a stdin-fed prompt (see the ARG_BUILDERS above).
    """
    build_args = ARG_BUILDERS.get(name, bare_stdin_args)

    def run(prompt: str) -> str:
        """Invoke the backend, feeding prompt via stdin, and return its stdout."""
        logger.info("Sending prompt to backend %r (%d chars)", name, len(prompt))
        result = subprocess.run(
            build_args(command), input=prompt, capture_output=True, text=True, check=True
        )
        logger.info("Received response from backend %r (%d chars)", name, len(result.stdout))
        return result.stdout

    return run


def get_backend_runner(config: Config) -> Callable[[str], str] | None:
    """Return a curried run(prompt) -> str for the first available configured backend."""
    name = resolve_backend(config.backend_order, config.backend_commands)
    if name is None:
        return None
    return invoke_backend(name, config.backend_commands[name])

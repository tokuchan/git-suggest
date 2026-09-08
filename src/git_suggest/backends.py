"""Detect and invoke the first working AI backend CLI (ADR 0002, ADR 0007).

Invocation is exposed as curried functions (`invoke_backend` returns a
`run(prompt) -> str` function) rather than a stateful "backend manager"
object.
"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable

from git_suggest.config import Config


def is_available(command: str) -> bool:
    """Return True if command resolves to an executable on PATH."""
    return shutil.which(command) is not None


def resolve_backend(order: tuple[str, ...], commands: dict[str, str]) -> str | None:
    """Return the first backend name in order whose command is available on PATH."""
    return next((name for name in order if is_available(commands.get(name, name))), None)


def print_flag_args(command: str, prompt: str) -> list[str]:
    """Build args for CLIs invoked as `<command> -p <prompt>` (claude, copilot)."""
    return [command, "-p", prompt]


def run_subcommand_args(command: str, prompt: str) -> list[str]:
    """Build args for CLIs invoked as `<command> run <prompt>` (opencode)."""
    return [command, "run", prompt]


#: Per-backend argument builders, keyed by backend name.
ARG_BUILDERS: dict[str, Callable[[str, str], list[str]]] = {
    "claude": print_flag_args,
    "copilot": print_flag_args,
    "opencode": run_subcommand_args,
}


def invoke_backend(name: str, command: str) -> Callable[[str], str]:
    """Return a curried run(prompt) -> stdout function for the given backend."""
    build_args = ARG_BUILDERS.get(name, print_flag_args)

    def run(prompt: str) -> str:
        """Invoke the backend with prompt and return its stdout."""
        result = subprocess.run(
            build_args(command, prompt), capture_output=True, text=True, check=True
        )
        return result.stdout

    return run


def get_backend_runner(config: Config) -> Callable[[str], str] | None:
    """Return a curried run(prompt) -> str for the first available configured backend."""
    name = resolve_backend(config.backend_order, config.backend_commands)
    if name is None:
        return None
    return invoke_backend(name, config.backend_commands[name])

"""Map -v/-q counts to a logging level, and drive progress output from logging.

Small pure functions (verbosity_to_level, select_output_mode) compose with
log_output_context, which attaches either a Rich log handler or a spinner
handler to the root logger for the duration of a command.
"""

from __future__ import annotations

import contextlib
import logging
from collections.abc import Iterator

from rich.console import Console
from rich.logging import RichHandler
from rich.status import Status

#: Logging levels ordered from quietest to loudest, centered on INFO.
_LEVELS: tuple[int, ...] = (
    logging.CRITICAL,
    logging.ERROR,
    logging.WARNING,
    logging.INFO,
    logging.DEBUG,
)
_DEFAULT_INDEX = _LEVELS.index(logging.INFO)


def verbosity_to_level(verbose: int, quiet: int) -> int:
    """Map -v/-q repetition counts to a logging level, centered on INFO.

    Each -v moves one step louder (toward DEBUG), each -q moves one step
    quieter (toward CRITICAL); they cancel out and the result is clamped to
    the available levels.
    """
    index = _DEFAULT_INDEX + verbose - quiet
    clamped = max(0, min(len(_LEVELS) - 1, index))
    return _LEVELS[clamped]


def set_level(level: int) -> None:
    """Set the root logger's level, clearing any handlers left from before."""
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)


def select_output_mode(is_tty: bool, want_log: bool, level: int) -> str:
    """Return "log" or "spinner": the output mode a command should use.

    "log" is chosen when explicitly requested (--log), when stdout isn't a
    real terminal, or when verbosity has been pushed away from the default
    INFO level (either -v or -q); otherwise "spinner".
    """
    if want_log or not is_tty or level != logging.INFO:
        return "log"
    return "spinner"


class SpinnerLogHandler(logging.Handler):
    """A logging handler that updates a Rich spinner's text instead of printing lines."""

    def __init__(self, status: Status) -> None:
        """Store the Status whose text this handler will keep updating."""
        super().__init__()
        self.status = status

    def emit(self, record: logging.LogRecord) -> None:
        """Update the spinner's text to the formatted log message."""
        self.status.update(self.format(record))


@contextlib.contextmanager
def log_output_context(mode: str) -> Iterator[Status | None]:
    """Attach a mode-appropriate logging handler to the root logger for a command.

    In "log" mode, installs a RichHandler and yields None. In "spinner"
    mode, opens a Rich status spinner and installs a SpinnerLogHandler so
    existing logger.info/debug calls drive the spinner text; yields the
    Status. Removes the handler (and stops the spinner) on exit.
    """
    root = logging.getLogger()
    if mode == "log":
        console = Console(stderr=True)
        handler: logging.Handler = RichHandler(console=console, show_time=False, show_path=False)
        root.addHandler(handler)
        try:
            yield None
        finally:
            root.removeHandler(handler)
        return
    console = Console(stderr=True)
    with console.status("Starting...") as status:
        handler = SpinnerLogHandler(status)
        root.addHandler(handler)
        try:
            yield status
        finally:
            root.removeHandler(handler)

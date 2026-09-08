"""Map -v/-q counts to a logging level and configure Rich-formatted logging.

Small pure functions (verbosity_to_level, should_show_spinner) compose with
one side-effecting setup function (configure_logging).
"""

from __future__ import annotations

import logging

from rich.logging import RichHandler

#: Logging levels ordered from quietest to loudest, centered on WARNING.
_LEVELS: tuple[int, ...] = (
    logging.CRITICAL,
    logging.ERROR,
    logging.WARNING,
    logging.INFO,
    logging.DEBUG,
)
_DEFAULT_INDEX = _LEVELS.index(logging.WARNING)


def verbosity_to_level(verbose: int, quiet: int) -> int:
    """Map -v/-q repetition counts to a logging level, centered on WARNING.

    Each -v moves one step louder (toward DEBUG), each -q moves one step
    quieter (toward CRITICAL); they cancel out and the result is clamped to
    the available levels.
    """
    index = _DEFAULT_INDEX + verbose - quiet
    clamped = max(0, min(len(_LEVELS) - 1, index))
    return _LEVELS[clamped]


def configure_logging(level: int) -> None:
    """Configure root logging to use a single Rich-formatted handler."""
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(RichHandler(show_time=False, show_path=False))
    root.setLevel(level)


def should_show_spinner(is_tty: bool, level: int) -> bool:
    """Return True when a spinner should replace step-by-step log lines.

    Only makes sense on a real terminal, and only when INFO-level logging
    (which would otherwise print the same progress as text) is disabled.
    """
    return is_tty and level > logging.INFO

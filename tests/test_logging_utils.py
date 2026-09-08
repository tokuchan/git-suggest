"""Tests for verbosity-to-level mapping, output-mode selection, and the
spinner log handler."""

import logging

from hypothesis import given
from hypothesis import strategies as st

from git_suggest.logging_utils import (
    _LEVELS,
    SpinnerLogHandler,
    select_output_mode,
    verbosity_to_level,
)


def test_default_verbosity_is_info() -> None:
    """With no -v/-q, the level is INFO."""
    assert verbosity_to_level(0, 0) == logging.INFO


def test_single_verbose_is_debug() -> None:
    """-v raises verbosity to DEBUG."""
    assert verbosity_to_level(1, 0) == logging.DEBUG


def test_verbose_clamps_at_debug() -> None:
    """Extra -v beyond DEBUG has no further effect."""
    assert verbosity_to_level(5, 0) == logging.DEBUG


def test_single_quiet_is_warning() -> None:
    """-q lowers verbosity to WARNING."""
    assert verbosity_to_level(0, 1) == logging.WARNING


def test_double_quiet_is_error() -> None:
    """-qq lowers verbosity to ERROR."""
    assert verbosity_to_level(0, 2) == logging.ERROR


def test_triple_quiet_is_critical() -> None:
    """-qqq lowers verbosity to CRITICAL."""
    assert verbosity_to_level(0, 3) == logging.CRITICAL


def test_quiet_clamps_at_critical() -> None:
    """Extra -q beyond CRITICAL has no further effect."""
    assert verbosity_to_level(0, 5) == logging.CRITICAL


def test_verbose_and_quiet_cancel_out() -> None:
    """One -v and one -q cancel back to the default INFO."""
    assert verbosity_to_level(1, 1) == logging.INFO
    assert verbosity_to_level(3, 3) == logging.INFO


@given(verbose=st.integers(min_value=0, max_value=20), quiet=st.integers(min_value=0, max_value=20))
def test_verbosity_to_level_always_returns_a_known_level(verbose: int, quiet: int) -> None:
    """The result is always one of the five defined levels."""
    assert verbosity_to_level(verbose, quiet) in _LEVELS


@given(verbose=st.integers(min_value=0, max_value=20), quiet=st.integers(min_value=0, max_value=20))
def test_more_verbose_never_increases_level_number(verbose: int, quiet: int) -> None:
    """Adding one more -v never makes the effective level number go up."""
    assert verbosity_to_level(verbose + 1, quiet) <= verbosity_to_level(verbose, quiet)


@given(verbose=st.integers(min_value=0, max_value=20), quiet=st.integers(min_value=0, max_value=20))
def test_more_quiet_never_decreases_level_number(verbose: int, quiet: int) -> None:
    """Adding one more -q never makes the effective level number go down."""
    assert verbosity_to_level(verbose, quiet + 1) >= verbosity_to_level(verbose, quiet)


def test_select_output_mode_spinner_on_tty_with_default_level() -> None:
    """A TTY at the default INFO level with no --log gets the spinner."""
    assert select_output_mode(is_tty=True, want_log=False, level=logging.INFO) == "spinner"


def test_select_output_mode_log_when_not_a_tty() -> None:
    """A non-TTY (piped) output always uses log mode."""
    assert select_output_mode(is_tty=False, want_log=False, level=logging.INFO) == "log"


def test_select_output_mode_log_when_verbosity_deviates() -> None:
    """Any -v/-q away from the default INFO level switches to log mode."""
    assert select_output_mode(is_tty=True, want_log=False, level=logging.DEBUG) == "log"
    assert select_output_mode(is_tty=True, want_log=False, level=logging.WARNING) == "log"


def test_select_output_mode_log_when_explicitly_requested() -> None:
    """--log forces log mode even on a TTY at the default level."""
    assert select_output_mode(is_tty=True, want_log=True, level=logging.INFO) == "log"


def test_spinner_log_handler_updates_status_text() -> None:
    """Emitting a record updates the handler's Status with the formatted message."""

    class FakeStatus:
        def __init__(self) -> None:
            self.text = None

        def update(self, text: str) -> None:
            self.text = text

    status = FakeStatus()
    handler = SpinnerLogHandler(status)
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0, msg="hello", args=(), exc_info=None
    )
    handler.emit(record)
    assert status.text == "hello"

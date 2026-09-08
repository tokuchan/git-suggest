"""Tests for verbosity-to-level mapping and spinner/logging decisions."""

import logging

from hypothesis import given
from hypothesis import strategies as st

from git_suggest.logging_utils import (
    _LEVELS,
    should_show_spinner,
    verbosity_to_level,
)


def test_default_verbosity_is_warning() -> None:
    """With no -v/-q, the level is WARNING."""
    assert verbosity_to_level(0, 0) == logging.WARNING


def test_single_verbose_is_info() -> None:
    """-v raises verbosity to INFO."""
    assert verbosity_to_level(1, 0) == logging.INFO


def test_double_verbose_is_debug() -> None:
    """-vv raises verbosity to DEBUG."""
    assert verbosity_to_level(2, 0) == logging.DEBUG


def test_verbose_clamps_at_debug() -> None:
    """Extra -v beyond DEBUG has no further effect."""
    assert verbosity_to_level(5, 0) == logging.DEBUG


def test_single_quiet_is_error() -> None:
    """-q lowers verbosity to ERROR."""
    assert verbosity_to_level(0, 1) == logging.ERROR


def test_double_quiet_is_critical() -> None:
    """-qq lowers verbosity to CRITICAL."""
    assert verbosity_to_level(0, 2) == logging.CRITICAL


def test_quiet_clamps_at_critical() -> None:
    """Extra -q beyond CRITICAL has no further effect."""
    assert verbosity_to_level(0, 5) == logging.CRITICAL


def test_verbose_and_quiet_cancel_out() -> None:
    """One -v and one -q cancel back to the default WARNING."""
    assert verbosity_to_level(1, 1) == logging.WARNING
    assert verbosity_to_level(3, 3) == logging.WARNING


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


def test_should_show_spinner_true_on_tty_with_default_level() -> None:
    """A TTY with the default WARNING level should show a spinner."""
    assert should_show_spinner(is_tty=True, level=logging.WARNING) is True


def test_should_show_spinner_false_when_not_a_tty() -> None:
    """A non-TTY (piped) output never shows a spinner."""
    assert should_show_spinner(is_tty=False, level=logging.WARNING) is False


def test_should_show_spinner_false_when_info_logging_enabled() -> None:
    """When INFO logging is enabled, log lines replace the spinner."""
    assert should_show_spinner(is_tty=True, level=logging.INFO) is False

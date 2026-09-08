"""Smoke test confirming the package imports and installs correctly."""

import git_suggest


def test_package_imports() -> None:
    """The git_suggest package imports without error."""
    assert git_suggest.__doc__

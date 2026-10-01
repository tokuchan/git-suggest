"""Produce a scan report from a git ref or range instead of staged changes (ADR 0024).

Reuses `scan.py`'s existing per-file formatting against a different diff
source entirely: `draft`/`render` need no changes at all, since a scan
report is already opaque plain text to them regardless of where it came
from.
"""

from __future__ import annotations

import logging
from pathlib import Path

from git_suggest.config import Config
from git_suggest.scan import build_report

logger = logging.getLogger(__name__)


def is_range(refspec: str) -> bool:
    """Return True if `refspec` is a range (contains '..' or '...'), not a bare single ref."""
    return ".." in refspec


def diff_args_for_refspec(refspec: str) -> list[str]:
    """Translate a refspec into `git diff` arguments (ADR 0024).

    A range (`A..B`/`A...B`) is passed straight through to `git diff`
    unchanged. A bare single ref means "what that commit changed relative
    to its parent" (`<ref>^..<ref>`) -- deliberately not `git diff <ref>`
    alone, which git itself defines as comparing that ref against the
    *working tree*, not against its own parent commit.
    """
    if is_range(refspec):
        return [refspec]
    return [f"{refspec}^..{refspec}"]


def build_ref_scan_report(
    refspec: str,
    cwd: Path | None = None,
    reference: str | None = None,
    config: Config | None = None,
) -> str:
    """Build a scan report for `refspec` (a single ref, or a range) instead of staged changes."""
    logger.info("Scanning ref/range %r", refspec)
    diff_args = diff_args_for_refspec(refspec)
    return build_report(diff_args, cwd=cwd, reference=reference, config=config)

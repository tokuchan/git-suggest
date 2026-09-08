"""Build a concise scan report from staged git changes (ADR 0004).

Full diff hunks are kept for text files; binary files are listed by
filename only. Small functions compose to build the report.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def run_git(*args: str, cwd: Path | None = None) -> str:
    """Run a git command and return its stdout, raising on failure."""
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def staged_numstat(cwd: Path | None = None) -> str:
    """Return raw `git diff --cached --numstat` output."""
    return run_git("diff", "--cached", "--numstat", cwd=cwd)


def parse_numstat_line(line: str) -> tuple[str, bool]:
    """Parse one numstat line into (path, is_binary)."""
    added, _deleted, path = line.split("\t", 2)
    return path, added == "-"


def staged_files(cwd: Path | None = None) -> list[tuple[str, bool]]:
    """Return (path, is_binary) for every staged file, in git's reported order."""
    lines = [line for line in staged_numstat(cwd=cwd).splitlines() if line]
    return [parse_numstat_line(line) for line in lines]


def file_diff(path: str, cwd: Path | None = None) -> str:
    """Return the full staged diff for a single text file."""
    return run_git("diff", "--cached", "--", path, cwd=cwd)


def format_binary_entry(path: str) -> str:
    """Render a binary file as a filename-only report entry."""
    return f"## {path} (binary file, content omitted)"


def format_text_entry(path: str, cwd: Path | None = None) -> str:
    """Render a text file as a report entry containing its full diff."""
    return f"## {path}\n\n{file_diff(path, cwd=cwd)}"


def format_entry(path: str, is_binary: bool, cwd: Path | None = None) -> str:
    """Render one staged file as a report entry, dispatching on binary/text."""
    if is_binary:
        return format_binary_entry(path)
    return format_text_entry(path, cwd=cwd)


def build_scan_report(cwd: Path | None = None) -> str:
    """Build the full scan report text for all currently staged changes."""
    entries = [format_entry(path, is_binary, cwd=cwd) for path, is_binary in staged_files(cwd=cwd)]
    return "\n\n".join(entries)

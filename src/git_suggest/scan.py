"""Build a concise scan report from staged git changes (ADR 0004).

Full diff hunks are kept for text files; binary files are listed by
filename only. Small functions compose to build the report. A leading
"subject-budget" line is embedded so `draft` can size the AI's subject
line correctly without needing the reference prefix's literal text
(ADR 0014). The diff source defaults to staged changes (`--cached`) but
is parameterized throughout (`diff_args`) so `scan_ref.py` (ADR 0024) can
reuse every bit of this formatting logic against an arbitrary git
ref/range instead.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from git_suggest.config import Config, get_config

logger = logging.getLogger(__name__)

_STAGED_DIFF_ARGS = ["--cached"]


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


def has_staged_changes(cwd: Path | None = None) -> bool:
    """Cheaply check for any staged change via `git diff --cached --quiet`.

    This runs before anything else in `build_scan_report` so an empty
    changeset is detected immediately, letting callers skip the (slow) AI
    backend round trip entirely instead of drafting from nothing.
    """
    result = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=cwd, capture_output=True)
    return result.returncode != 0


def diff_numstat(diff_args: list[str], cwd: Path | None = None) -> str:
    """Return raw `git diff <diff_args> --numstat` output."""
    return run_git("diff", *diff_args, "--numstat", cwd=cwd)


def parse_numstat_line(line: str) -> tuple[str, bool]:
    """Parse one numstat line into (path, is_binary)."""
    added, _deleted, path = line.split("\t", 2)
    return path, added == "-"


def diff_files(diff_args: list[str], cwd: Path | None = None) -> list[tuple[str, bool]]:
    """Return (path, is_binary) for every file in the given diff, in git's reported order."""
    lines = [line for line in diff_numstat(diff_args, cwd=cwd).splitlines() if line]
    return [parse_numstat_line(line) for line in lines]


def file_diff(diff_args: list[str], path: str, cwd: Path | None = None) -> str:
    """Return the full diff for a single text file, under the given diff source."""
    return run_git("diff", *diff_args, "--", path, cwd=cwd)


def format_binary_entry(path: str) -> str:
    """Render a binary file as a filename-only report entry."""
    return f"## {path} (binary file, content omitted)"


def format_text_entry(diff_args: list[str], path: str, cwd: Path | None = None) -> str:
    """Render a text file as a report entry containing its full diff."""
    return f"## {path}\n\n{file_diff(diff_args, path, cwd=cwd)}"


def format_entry(diff_args: list[str], path: str, is_binary: bool, cwd: Path | None = None) -> str:
    """Render one file as a report entry, dispatching on binary/text."""
    logger.debug("Formatting scan entry for %s (binary=%s)", path, is_binary)
    if is_binary:
        return format_binary_entry(path)
    return format_text_entry(diff_args, path, cwd=cwd)


def current_branch(cwd: Path | None = None) -> str:
    """Return the current branch name verbatim (`git rev-parse --abbrev-ref HEAD`)."""
    return run_git("rev-parse", "--abbrev-ref", "HEAD", cwd=cwd).strip()


def absolute_git_dir(cwd: Path | None = None) -> Path:
    """Return the absolute path to the current repo's git directory.

    Uses `git rev-parse --absolute-git-dir` rather than assuming ".git/",
    since that resolves correctly for plain repos (.git/), submodules
    (.git/modules/<name>/), and worktrees (.git/worktrees/<name>/) alike
    (ADR 0019).
    """
    return Path(run_git("rev-parse", "--absolute-git-dir", cwd=cwd).strip())


def subject_budget(reference: str | None, config: Config) -> tuple[int, int]:
    """Return (max, preferred) subject-length budget, reduced by the reference prefix's length.

    Both of config's subject_max_length/subject_preferred_length count the
    full subject line end-to-end; a reference prefix (e.g. from -r/-b)
    consumes some of that budget before the AI-chosen `type(scope): `
    even begins, so its length (plus the ": " separator) is subtracted
    here. `type`/`scope` lengths are deliberately not accounted for, since
    the AI hasn't chosen them yet (see ADR 0014/0015).
    """
    prefix_len = len(f"{reference}: ") if reference else 0
    max_len = config.subject_max_length - prefix_len
    preferred_len = max(0, config.subject_preferred_length - prefix_len)
    return max_len, preferred_len


def format_subject_budget_line(max_len: int, preferred_len: int) -> str:
    """Render the leading machine-readable subject-budget line for the scan report."""
    return f"# subject-budget: max={max_len} preferred={preferred_len}"


def build_report(
    diff_args: list[str],
    cwd: Path | None = None,
    reference: str | None = None,
    config: Config | None = None,
) -> str:
    """Build a scan report for the given diff source (`diff_args`, e.g. `["--cached"]`).

    A leading subject-budget line (ADR 0014) is always included ahead of
    the diff entries, sized down by `reference`'s length when given.
    Shared by `scan` (staged changes) and `scan_ref.py` (ADR 0024, an
    arbitrary git ref/range) alike.
    """
    files = diff_files(diff_args, cwd=cwd)
    logger.info("Found %d file(s)", len(files))
    entries = [format_entry(diff_args, path, is_binary, cwd=cwd) for path, is_binary in files]
    max_len, preferred_len = subject_budget(reference, config or get_config())
    budget_line = format_subject_budget_line(max_len, preferred_len)
    return "\n\n".join([budget_line, *entries])


def build_scan_report(
    cwd: Path | None = None,
    reference: str | None = None,
    config: Config | None = None,
) -> str:
    """Build the full scan report text for all currently staged changes.

    Returns "" immediately (without ever running the fuller diff) when
    there's nothing staged, so callers can skip the AI backend round trip
    entirely.
    """
    logger.info("Scanning staged changes (git diff --cached)")
    if not has_staged_changes(cwd=cwd):
        logger.info("No staged changes found")
        return ""
    return build_report(_STAGED_DIFF_ARGS, cwd=cwd, reference=reference, config=config)

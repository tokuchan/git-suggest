"""Compute and write this project's next CalVer version (ADR 0021).

Plain and reusable: reads the current `pyproject.toml` version, computes
the next one from today's date, rewrites the file, and commits the
change. Knows nothing about git push, branches, or remotes — that policy
lives in the pre-push hook that calls this (see `.githooks/pre-push`).
"""

from __future__ import annotations

import logging
import re
import subprocess
from datetime import date
from pathlib import Path

from git_suggest.config import Config

logger = logging.getLogger(__name__)

_VERSION_LINE_PATTERN = re.compile(r'^version\s*=\s*"(\d{2})\.(\d{2})\.(\d+)"\s*$', re.MULTILINE)


def read_version(pyproject_path: Path) -> tuple[int, int, int]:
    """Parse `version = "YY.MM.patch"` out of a pyproject.toml, as (year, month, patch).

    Raises ValueError if no such line is found, or it isn't in CalVer form.
    """
    match = _VERSION_LINE_PATTERN.search(pyproject_path.read_text())
    if not match:
        raise ValueError(f'No CalVer `version = "YY.MM.patch"` line found in {pyproject_path}')
    year, month, patch = match.groups()
    return int(year), int(month), int(patch)


def format_version(year: int, month: int, patch: int) -> str:
    """Render (year, month, patch) as the `YY.MM.patch` string form."""
    return f"{year:02d}.{month:02d}.{patch}"


def compute_next_version(current: tuple[int, int, int], today: date) -> str:
    """Compute the next CalVer version from the current one and today's date.

    Patch resets to 0 when today's (year, month) differs from the
    current version's; otherwise it increments by 1.
    """
    year, month = today.year % 100, today.month
    current_year, current_month, current_patch = current
    patch = current_patch + 1 if (year, month) == (current_year, current_month) else 0
    return format_version(year, month, patch)


def write_version(pyproject_path: Path, new_version: str) -> None:
    """Rewrite pyproject.toml's `version = "..."` line in place to `new_version`."""
    text = pyproject_path.read_text()
    updated, count = _VERSION_LINE_PATTERN.subn(f'version = "{new_version}"', text, count=1)
    if count != 1:
        raise ValueError(f'No CalVer `version = "YY.MM.patch"` line found in {pyproject_path}')
    pyproject_path.write_text(updated)


def commit_version_bump(
    pyproject_path: Path, new_version: str, config: Config, cwd: Path | None = None
) -> None:
    """Stage pyproject.toml and commit the version bump with the configured message.

    `git add`/`git commit`'s own stdout is captured and discarded rather
    than inherited: `bump`'s only stdout output is the new version
    string, since callers (e.g. the pre-push hook) capture it via shell
    command substitution and would otherwise get git's own noise mixed
    into that value.
    """
    message = config.bump_commit_message_template.format(version=new_version)
    subprocess.run(["git", "add", str(pyproject_path)], cwd=cwd, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", message], cwd=cwd, check=True, capture_output=True)


def bump_version(
    pyproject_path: Path, config: Config, today: date | None = None, cwd: Path | None = None
) -> str:
    """Compute, write, and commit this project's next CalVer version.

    Returns the new version string. `today` defaults to the real current
    date; overridable for tests.
    """
    current = read_version(pyproject_path)
    new_version = compute_next_version(current, today or date.today())
    logger.info("Bumping version from %s to %s", format_version(*current), new_version)
    write_version(pyproject_path, new_version)
    commit_version_bump(pyproject_path, new_version, config, cwd=cwd)
    return new_version


def tag_name_for_version(version: str) -> str:
    """Return the tag name a release would use for `version` (ADR 0023): `v<version>`."""
    return f"v{version}"


def find_tag_for_version(version: str, cwd: Path | None = None) -> str | None:
    """Return the release tag for `version` if one exists, else None (ADR 0023)."""
    tag = tag_name_for_version(version)
    result = subprocess.run(
        ["git", "tag", "-l", tag], cwd=cwd, capture_output=True, text=True, check=True
    )
    return tag if result.stdout.strip() == tag else None


def find_commit_for_version(
    version: str, pyproject_path: Path, cwd: Path | None = None
) -> str | None:
    """Find the commit that introduced `version` in pyproject.toml, via a pickaxe search.

    Works uniformly whether that commit was a normal `bump` commit or a
    hand-edited one (e.g. ADR 0021's initial CalVer switchover), neither
    of which is assumed to match any particular commit-message pattern
    (ADR 0023). git's `-S` pickaxe matches any commit whose occurrence
    count of that exact string changed -- both the commit that *added*
    the version line, and (for all but the current version) a later
    commit that *removed* it again when replaced by the next bump. Since
    `git log`'s default order is newest-first, the introducing commit is
    always the *oldest* (last) match, not the newest (first) one.
    Returns None if no commit ever introduced that exact version line.
    """
    result = subprocess.run(
        [
            "git",
            "log",
            "--format=%H",
            f'-Sversion = "{version}"',
            "--",
            str(pyproject_path),
        ],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    shas = [line for line in result.stdout.splitlines() if line]
    return shas[-1] if shas else None


def resolve_version_endpoint(
    version: str, pyproject_path: Path, cwd: Path | None = None
) -> str | None:
    """Return the best compare-link endpoint for `version`: a tag, else a commit SHA, else None.

    Prefers a release tag (`v<version>`) when one exists; falls back to
    the commit that introduced the version line in pyproject.toml,
    resolved via `find_commit_for_version` (ADR 0023).
    """
    return find_tag_for_version(version, cwd=cwd) or find_commit_for_version(
        version, pyproject_path, cwd=cwd
    )

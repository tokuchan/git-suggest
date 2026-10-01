"""Stamp CHANGELOG.md's Unreleased section as a dated release entry (ADR 0023).

Reads the current (already-bumped) pyproject.toml version, renames the
Unreleased header into a dated version header, inserts a fresh empty
Unreleased above it, and rewrites the footer's compare links -- preferring
a release tag when one exists, falling back to a commit SHA otherwise.
Deliberately decoupled from `bump` (ADR 0021): this only runs when
explicitly invoked.
"""

from __future__ import annotations

import logging
import re
import subprocess
from datetime import date
from pathlib import Path

from git_suggest.changelog import split_unreleased_section
from git_suggest.config import Config
from git_suggest.version import format_version, read_version, resolve_version_endpoint

logger = logging.getLogger(__name__)

_RELEASE_HEADER_PATTERN = re.compile(
    r"^## \[(\d{2}\.\d{2}\.\d+)\] - \d{4}-\d{2}-\d{2}\s*$", re.MULTILINE
)
_FOOTER_LINE_PATTERN = re.compile(r"^\[[^\]]+\]: .+$", re.MULTILINE)


def existing_release_versions(changelog_text: str) -> list[str]:
    """Return every already-dated release version in `changelog_text`, newest first."""
    return _RELEASE_HEADER_PATTERN.findall(changelog_text)


def stamp_unreleased_as_release(changelog_text: str, version: str, today: date) -> str:
    """Rename Unreleased's header into a dated `## [version] - date` header.

    The Unreleased header itself is left in place (now with an empty
    body above the new dated header), per ADR 0023.
    """
    prefix, body, suffix = split_unreleased_section(changelog_text)
    return f"{prefix}\n## [{version}] - {today.isoformat()}\n{body}{suffix}"


def derive_repo_url(cwd: Path | None = None) -> str:
    """Return this repo's browsable HTTPS URL, derived from its `origin` remote."""
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"], cwd=cwd, capture_output=True, text=True, check=True
    )
    url = result.stdout.strip().removesuffix(".git")
    if url.startswith("git@"):
        host, _, path = url.removeprefix("git@").partition(":")
        return f"https://{host}/{path}"
    return url


def split_footer(changelog_text: str) -> tuple[str, list[str]]:
    """Split changelog text into (body, existing footer compare-link lines)."""
    matches = list(_FOOTER_LINE_PATTERN.finditer(changelog_text))
    if not matches:
        return changelog_text.rstrip("\n"), []
    first_start = matches[0].start()
    body = changelog_text[:first_start].rstrip("\n")
    lines = changelog_text[first_start:].strip("\n").splitlines()
    return body, lines


def update_footer_links(
    body: str,
    footer_lines: list[str],
    new_version: str,
    prev_version: str | None,
    new_endpoint: str | None,
    prev_endpoint: str | None,
    repo_url: str,
) -> str:
    """Rebuild the footer's compare links for the newly-stamped version (ADR 0023)."""
    if new_endpoint is None:
        logger.warning(
            "Could not resolve an endpoint for %s; leaving compare links untouched", new_version
        )
        return body + "\n\n" + "\n".join(footer_lines) + "\n" if footer_lines else body + "\n"
    filtered = [
        line
        for line in footer_lines
        if not line.startswith("[Unreleased]: ") and not line.startswith(f"[{new_version}]: ")
    ]
    new_lines = [f"[Unreleased]: {repo_url}/compare/{new_endpoint}...HEAD"]
    if prev_version is not None and prev_endpoint is not None:
        new_lines.append(f"[{new_version}]: {repo_url}/compare/{prev_endpoint}...{new_endpoint}")
    return body + "\n\n" + "\n".join([*new_lines, *filtered]) + "\n"


def commit_release(
    changelog_path: Path, version: str, config: Config, cwd: Path | None = None
) -> None:
    """Stage and commit the release-stamped changelog."""
    message = config.release_commit_message_template.format(version=version)
    subprocess.run(["git", "add", str(changelog_path)], cwd=cwd, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", message], cwd=cwd, check=True, capture_output=True)


def stamp_release(
    changelog_path: Path,
    pyproject_path: Path,
    config: Config,
    cwd: Path | None = None,
    today: date | None = None,
) -> str:
    """Stamp CHANGELOG.md's Unreleased section as a dated release, commit it, return the version."""
    today = today or date.today()
    version = format_version(*read_version(pyproject_path))
    text = changelog_path.read_text()
    prev_versions = existing_release_versions(text)
    prev_version = prev_versions[0] if prev_versions else None

    stamped = stamp_unreleased_as_release(text, version, today)
    body, footer_lines = split_footer(stamped)
    repo_url = derive_repo_url(cwd=cwd)
    new_endpoint = resolve_version_endpoint(version, pyproject_path, cwd=cwd)
    prev_endpoint = (
        resolve_version_endpoint(prev_version, pyproject_path, cwd=cwd) if prev_version else None
    )
    final_text = update_footer_links(
        body, footer_lines, version, prev_version, new_endpoint, prev_endpoint, repo_url
    )

    changelog_path.write_text(final_text)
    commit_release(changelog_path, version, config, cwd=cwd)
    return version

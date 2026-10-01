"""Append a DraftDocument's changelog entries into CHANGELOG.md's Unreleased section (ADR 0022).

Reuses `render.py`'s own `format_entry_line` and `model.py`'s category
ordering, so an appended entry renders identically to how it would in a
commit message. Existing Unreleased content is never reparsed back into
`ChangelogEntry` objects (lossy); instead, each category's raw rendered
bullet text is located by its `### <Category>` heading and new entries
are appended to the end of it, or a new heading is inserted in canonical
order if that category has no existing entries yet.
"""

from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path

from git_suggest.config import Config
from git_suggest.model import CHANGELOG_CATEGORIES, DraftDocument, sections_of
from git_suggest.render import format_entry_line

logger = logging.getLogger(__name__)

_UNRELEASED_HEADER = "## [Unreleased]"
_CATEGORY_HEADER_PATTERN = re.compile(r"^### (\w+)\s*$", re.MULTILINE)
_NEXT_VERSION_HEADER_PATTERN = re.compile(r"^## \[", re.MULTILINE)


def split_unreleased_section(changelog_text: str) -> tuple[str, str, str]:
    """Split changelog text into (prefix, unreleased_body, suffix).

    `prefix` ends right after the "## [Unreleased]" header line (and its
    newline); `suffix` starts at the next "## [" version header, or at
    end of file if this is the only section so far. Raises ValueError if
    no "## [Unreleased]" header is found.
    """
    header_index = changelog_text.find(_UNRELEASED_HEADER)
    if header_index == -1:
        raise ValueError(f"No {_UNRELEASED_HEADER!r} header found in changelog")
    header_end = header_index + len(_UNRELEASED_HEADER)
    newline_index = changelog_text.find("\n", header_end)
    body_start = newline_index + 1 if newline_index != -1 else header_end
    match = _NEXT_VERSION_HEADER_PATTERN.search(changelog_text, body_start)
    body_end = match.start() if match else len(changelog_text)
    return (
        changelog_text[:body_start],
        changelog_text[body_start:body_end],
        changelog_text[body_end:],
    )


def parse_category_sections(body: str) -> dict[str, str]:
    """Return {lowercase_category_name: raw_bullet_text} for each existing `### ` section."""
    matches = list(_CATEGORY_HEADER_PATTERN.finditer(body))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        name = match.group(1).lower()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        sections[name] = body[start:end].strip("\n")
    return sections


def merge_entries_into_sections(
    existing: dict[str, str], doc: DraftDocument, width: int, indent: int
) -> dict[str, str]:
    """Merge a draft document's changelog entries into existing raw per-category bullet text."""
    merged = dict(existing)
    for name, entries in sections_of(doc.changelog):
        if not entries:
            continue
        rendered = "\n".join(format_entry_line(entry, width, indent) for entry in entries)
        merged[name] = f"{merged[name]}\n{rendered}" if merged.get(name) else rendered
    return merged


def render_unreleased_body(sections: dict[str, str]) -> str:
    """Render merged per-category sections back into the Unreleased body text."""
    blocks = [
        f"### {name.capitalize()}\n{sections[name]}"
        for name in CHANGELOG_CATEGORIES
        if sections.get(name)
    ]
    if not blocks:
        return "\n"
    return "\n" + "\n\n".join(blocks) + "\n\n"


def append_draft_to_changelog(
    changelog_text: str, doc: DraftDocument, width: int, indent: int
) -> str:
    """Append `doc`'s changelog entries into `changelog_text`'s Unreleased section."""
    prefix, body, suffix = split_unreleased_section(changelog_text)
    existing = parse_category_sections(body)
    merged = merge_entries_into_sections(existing, doc, width, indent)
    return prefix + render_unreleased_body(merged) + suffix


def commit_changelog(
    changelog_path: Path, doc: DraftDocument, config: Config, cwd: Path | None = None
) -> None:
    """Stage and commit the changelog update, in its own dedicated commit."""
    message = config.changelog_commit_message_template.format(description=doc.description)
    subprocess.run(["git", "add", str(changelog_path)], cwd=cwd, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", message], cwd=cwd, check=True, capture_output=True)


def update_changelog(
    changelog_path: Path,
    doc: DraftDocument,
    config: Config,
    cwd: Path | None = None,
) -> None:
    """Append `doc`'s changelog entries into `changelog_path`'s Unreleased section and commit it."""
    text = changelog_path.read_text()
    updated = append_draft_to_changelog(
        text, doc, config.body_wrap_width, config.changelog_entry_indent
    )
    changelog_path.write_text(updated)
    commit_changelog(changelog_path, doc, config, cwd=cwd)

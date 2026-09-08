"""Render a DraftDocument into a conventional-commit message (ADR 0006 render mode).

Small functions compose: header, one line per changelog entry, one section
per non-empty category, and the full message or changelog-only fragment.
"""

from __future__ import annotations

from git_suggest.model import ChangelogEntry, ChangelogSections, DraftDocument, sections_of


def format_header(doc: DraftDocument) -> str:
    """Render the conventional-commit header line: `type(scope): description`."""
    subject = f"{doc.type.value}({doc.scope})" if doc.scope else doc.type.value
    return f"{subject}: {doc.description}"


def format_entry_line(entry: ChangelogEntry) -> str:
    """Render one changelog entry as a single markdown bullet line."""
    return f"- **{entry.affected_file}**: {entry.change_statement}"


def format_section(name: str, entries: list[ChangelogEntry]) -> str | None:
    """Render one Keep a Changelog section, or None if it has no entries."""
    if not entries:
        return None
    lines = "\n".join(format_entry_line(entry) for entry in entries)
    return f"### {name.capitalize()}\n{lines}"


def format_changelog_body(changelog: ChangelogSections) -> str:
    """Render every non-empty changelog category, in canonical order."""
    sections = [format_section(name, entries) for name, entries in sections_of(changelog)]
    return "\n\n".join(section for section in sections if section is not None)


def render_commit_message(doc: DraftDocument) -> str:
    """Render the full conventional-commit message: header + changelog body."""
    header = format_header(doc)
    body = format_changelog_body(doc.changelog)
    return f"{header}\n\n{body}" if body else header


def render_changelog_only(doc: DraftDocument) -> str:
    """Render just the Keep a Changelog body fragment, without the commit header."""
    return format_changelog_body(doc.changelog)

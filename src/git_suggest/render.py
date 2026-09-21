"""Render a DraftDocument into a conventional-commit message (ADR 0006 render mode).

Small functions compose: header, one line per changelog entry, one section
per non-empty category, and the full message or changelog-only fragment.
Each changelog entry's statement wraps at a configurable column width
with a fixed indent under its own bullet label line (ADR 0016); a
reference prefix (-r/-b, ADR 0013) is stitched onto the header here,
never carried on the draft document itself.
"""

from __future__ import annotations

import logging
import textwrap

from git_suggest.model import ChangelogEntry, ChangelogSections, DraftDocument, sections_of

logger = logging.getLogger(__name__)


def wrap_body_text(
    text: str, width: int, initial_indent: str = "", subsequent_indent: str = ""
) -> str:
    """Wrap arbitrary body text to `width` columns, indenting first/later lines.

    General-purpose (ADR 0016): usable for any body text, not just
    changelog bullets. `initial_indent` is prepended to the first line and
    `subsequent_indent` to every continuation line after it; both count
    toward `width`.
    """
    wrapped = textwrap.wrap(
        text,
        width=width,
        initial_indent=initial_indent,
        subsequent_indent=subsequent_indent,
        break_long_words=False,
        break_on_hyphens=False,
    )
    return "\n".join(wrapped) if wrapped else text


def format_header(doc: DraftDocument) -> str:
    """Render the conventional-commit header line: `type(scope): description`."""
    subject = f"{doc.type.value}({doc.scope})" if doc.scope else doc.type.value
    return f"{subject}: {doc.description}"


def apply_reference_prefix(header: str, reference: str | None) -> str:
    """Prepend `"<reference>: "` to a rendered header, or return it unchanged."""
    return f"{reference}: {header}" if reference else header


def format_entry_line(entry: ChangelogEntry, width: int, indent: int = 4) -> str:
    """Render one changelog entry as a bullet label line, statement indented below it.

    The bullet + bolded filename form their own short label line; the
    change statement wraps beneath it at a fixed `indent`-width indent
    (ADR 0016), so a long filename never eats into the statement's wrap
    budget the way aligning continuation lines under it would. No blank
    line separates the two, so the statement stays part of the same
    Markdown list item (a lazily-continued paragraph) rather than
    becoming its own list-item paragraph.
    """
    label = f"- **{entry.affected_file}**:"
    pad = " " * indent
    statement = wrap_body_text(
        entry.change_statement, width, initial_indent=pad, subsequent_indent=pad
    )
    return f"{label}\n{statement}"


def format_section(
    name: str, entries: list[ChangelogEntry], width: int, indent: int = 4
) -> str | None:
    """Render one Keep a Changelog section, or None if it has no entries."""
    if not entries:
        return None
    lines = "\n".join(format_entry_line(entry, width, indent) for entry in entries)
    return f"### {name.capitalize()}\n{lines}"


def format_changelog_body(changelog: ChangelogSections, width: int, indent: int = 4) -> str:
    """Render every non-empty changelog category, in canonical order."""
    logger.debug("Rendering changelog body")
    sections = [
        format_section(name, entries, width, indent) for name, entries in sections_of(changelog)
    ]
    non_empty = [section for section in sections if section is not None]
    logger.debug("Rendered %d non-empty changelog section(s)", len(non_empty))
    return "\n\n".join(non_empty)


def render_commit_message(
    doc: DraftDocument, reference: str | None = None, width: int = 72, indent: int = 4
) -> str:
    """Render the full conventional-commit message: header + changelog body.

    `reference` (from -r/-b) is prepended to the header only, never to the
    body. `width` sets the body-text wrap column and `indent` the fixed
    per-entry indent under each bullet label (ADR 0016).
    """
    logger.info("Rendering commit message")
    header = apply_reference_prefix(format_header(doc), reference)
    body = format_changelog_body(doc.changelog, width, indent)
    return f"{header}\n\n{body}" if body else header


def render_changelog_only(doc: DraftDocument, width: int = 72, indent: int = 4) -> str:
    """Render just the Keep a Changelog body fragment, without the commit header."""
    logger.info("Rendering changelog-only body")
    return format_changelog_body(doc.changelog, width, indent)

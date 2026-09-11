"""Render a DraftDocument into a conventional-commit message (ADR 0006 render mode).

Small functions compose: header, one line per changelog entry, one section
per non-empty category, and the full message or changelog-only fragment.
Body text wraps at a configurable column width with a hanging indent
(ADR 0016); a reference prefix (-r/-b, ADR 0013) is stitched onto the
header here, never carried on the draft document itself.
"""

from __future__ import annotations

import logging
import textwrap

from git_suggest.model import ChangelogEntry, ChangelogSections, DraftDocument, sections_of

logger = logging.getLogger(__name__)


def wrap_body_text(text: str, width: int, subsequent_indent: str = "") -> str:
    """Wrap arbitrary body text to `width` columns with a hanging indent.

    General-purpose (ADR 0016): usable for any body text, not just
    changelog bullets. `subsequent_indent` is prepended to every
    continuation line after the first.
    """
    wrapped = textwrap.wrap(
        text,
        width=width,
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


def format_entry_line(entry: ChangelogEntry, width: int) -> str:
    """Render one changelog entry as a bullet line, wrapped with a hanging indent."""
    prefix = f"- **{entry.affected_file}**: "
    return wrap_body_text(
        f"{prefix}{entry.change_statement}", width, subsequent_indent=" " * len(prefix)
    )


def format_section(name: str, entries: list[ChangelogEntry], width: int) -> str | None:
    """Render one Keep a Changelog section, or None if it has no entries."""
    if not entries:
        return None
    lines = "\n".join(format_entry_line(entry, width) for entry in entries)
    return f"### {name.capitalize()}\n{lines}"


def format_changelog_body(changelog: ChangelogSections, width: int) -> str:
    """Render every non-empty changelog category, in canonical order."""
    logger.debug("Rendering changelog body")
    sections = [format_section(name, entries, width) for name, entries in sections_of(changelog)]
    non_empty = [section for section in sections if section is not None]
    logger.debug("Rendered %d non-empty changelog section(s)", len(non_empty))
    return "\n\n".join(non_empty)


def render_commit_message(doc: DraftDocument, reference: str | None = None, width: int = 72) -> str:
    """Render the full conventional-commit message: header + changelog body.

    `reference` (from -r/-b) is prepended to the header only, never to the
    body. `width` sets the body-text wrap column (ADR 0016).
    """
    logger.info("Rendering commit message")
    header = apply_reference_prefix(format_header(doc), reference)
    body = format_changelog_body(doc.changelog, width)
    return f"{header}\n\n{body}" if body else header


def render_changelog_only(doc: DraftDocument, width: int = 72) -> str:
    """Render just the Keep a Changelog body fragment, without the commit header."""
    logger.info("Rendering changelog-only body")
    return format_changelog_body(doc.changelog, width)

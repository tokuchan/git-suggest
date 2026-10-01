"""Tests for appending draft documents into CHANGELOG.md's Unreleased section (ADR 0022)."""

import pytest

from git_suggest.changelog import (
    append_draft_to_changelog,
    merge_entries_into_sections,
    parse_category_sections,
    split_unreleased_section,
)
from git_suggest.model import ChangelogEntry, ChangelogSections, CommitType, DraftDocument

_BOOTSTRAP = (
    "# Changelog\n\n"
    "Some preamble.\n\n"
    "## [Unreleased]\n\n"
    "## [26.09.0] - 2026-09-30\n\n"
    "Initial CalVer release.\n"
)


def _doc(**changelog_kwargs: object) -> DraftDocument:
    return DraftDocument(
        type=CommitType.FEAT,
        description="add thing",
        changelog=ChangelogSections(**changelog_kwargs),
    )


def _entry(affected_file: str, statement: str = "Did a thing.") -> ChangelogEntry:
    return ChangelogEntry(
        affected_file=affected_file, project_context="x", change_statement=statement
    )


def test_split_unreleased_section_finds_prefix_body_suffix() -> None:
    """split_unreleased_section separates the Unreleased body from everything around it."""
    prefix, body, suffix = split_unreleased_section(_BOOTSTRAP)
    assert prefix.endswith("## [Unreleased]\n")
    assert body == "\n"
    assert suffix.startswith("## [26.09.0]")


def test_split_unreleased_section_raises_without_the_header() -> None:
    """split_unreleased_section raises ValueError when there's no Unreleased header."""
    with pytest.raises(ValueError, match="Unreleased"):
        split_unreleased_section("# Changelog\n\n## [26.09.0] - 2026-09-30\n")


def test_parse_category_sections_empty_body_has_no_sections() -> None:
    """An empty Unreleased body parses to no existing category sections."""
    assert parse_category_sections("\n") == {}


def test_parse_category_sections_extracts_existing_bullets() -> None:
    """parse_category_sections extracts each ### section's raw bullet text."""
    body = "\n### Added\n- **a.py**:\n    Added a.\n\n### Fixed\n- **b.py**:\n    Fixed b.\n\n"
    sections = parse_category_sections(body)
    assert sections["added"] == "- **a.py**:\n    Added a."
    assert sections["fixed"] == "- **b.py**:\n    Fixed b."


def test_merge_entries_into_sections_appends_to_existing_category() -> None:
    """A new entry in an already-present category is appended after the existing bullets."""
    existing = {"added": "- **a.py**:\n    Added a."}
    doc = _doc(added=[_entry("b.py", "Added b.")])
    merged = merge_entries_into_sections(existing, doc, width=72, indent=4)
    assert merged["added"] == "- **a.py**:\n    Added a.\n- **b.py**:\n    Added b."


def test_merge_entries_into_sections_creates_new_category() -> None:
    """A category with no existing entries gets created fresh."""
    merged = merge_entries_into_sections({}, _doc(fixed=[_entry("c.py", "Fixed c.")]), 72, 4)
    assert merged["fixed"] == "- **c.py**:\n    Fixed c."


def test_append_draft_to_changelog_into_empty_unreleased() -> None:
    """Appending into a bootstrap (empty Unreleased) changelog inserts one new section."""
    doc = _doc(added=[_entry("src/x.py", "Added a thing.")])
    result = append_draft_to_changelog(_BOOTSTRAP, doc, width=72, indent=4)
    assert (
        "## [Unreleased]\n\n### Added\n- **src/x.py**:\n    Added a thing.\n\n## [26.09.0]"
        in result
    )


def test_append_draft_to_changelog_merges_across_two_calls() -> None:
    """A second append merges into the first's existing category and adds a new one."""
    first = append_draft_to_changelog(_BOOTSTRAP, _doc(added=[_entry("x.py")]), 72, 4)
    second = append_draft_to_changelog(
        first, _doc(added=[_entry("y.py")], fixed=[_entry("z.py")]), 72, 4
    )
    assert "- **x.py**:" in second
    assert "- **y.py**:" in second
    assert second.index("- **x.py**:") < second.index("- **y.py**:")
    assert "### Fixed\n- **z.py**:" in second


def test_append_draft_to_changelog_preserves_everything_outside_unreleased() -> None:
    """Content before Unreleased and after the next version header is untouched."""
    result = append_draft_to_changelog(_BOOTSTRAP, _doc(added=[_entry("x.py")]), 72, 4)
    assert result.startswith("# Changelog\n\nSome preamble.\n\n")
    assert result.endswith("## [26.09.0] - 2026-09-30\n\nInitial CalVer release.\n")


def test_append_draft_to_changelog_ignores_empty_categories() -> None:
    """A draft document with no changelog entries at all leaves Unreleased empty."""
    result = append_draft_to_changelog(_BOOTSTRAP, _doc(), 72, 4)
    assert result == _BOOTSTRAP

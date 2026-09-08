"""Tests for the draft document model."""

import json

from hypothesis import given
from hypothesis import strategies as st

from git_suggest.model import (
    CHANGELOG_CATEGORIES,
    ChangelogEntry,
    ChangelogSections,
    CommitType,
    DraftDocument,
    all_entries,
    sections_of,
)


def test_draft_document_round_trips_through_json() -> None:
    """A DraftDocument survives a dump-then-parse cycle unchanged."""
    doc = DraftDocument(
        type=CommitType.FEAT,
        scope="cli",
        description="add render subcommand",
        changelog=ChangelogSections(
            added=[
                ChangelogEntry(
                    affected_file="src/git_suggest/render.py",
                    project_context="commit message rendering",
                    change_statement="Add the render subcommand.",
                )
            ]
        ),
    )
    restored = DraftDocument.model_validate(json.loads(doc.model_dump_json()))
    assert restored == doc


def test_sections_of_covers_all_categories_in_order() -> None:
    """sections_of yields exactly the six categories, in canonical order."""
    names = [name for name, _ in sections_of(ChangelogSections())]
    assert names == list(CHANGELOG_CATEGORIES)


_entry_strategy = st.builds(
    ChangelogEntry,
    affected_file=st.text(min_size=1, max_size=20),
    project_context=st.text(max_size=20),
    change_statement=st.text(min_size=1, max_size=20),
)


@given(entry_lists=st.lists(_entry_strategy, max_size=5))
def test_all_entries_preserves_count_for_single_category(entry_lists: list) -> None:
    """all_entries returns every entry placed into a single category, none dropped."""
    changelog = ChangelogSections(added=entry_lists)
    assert all_entries(changelog) == entry_lists

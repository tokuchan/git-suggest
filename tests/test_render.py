"""Tests for rendering a DraftDocument into a commit message."""

from hypothesis import given
from hypothesis import strategies as st

from git_suggest.model import (
    CHANGELOG_CATEGORIES,
    ChangelogEntry,
    ChangelogSections,
    CommitType,
    DraftDocument,
    all_entries,
)
from git_suggest.render import (
    format_header,
    render_changelog_only,
    render_commit_message,
)


def _doc(**overrides: object) -> DraftDocument:
    defaults: dict = {
        "type": CommitType.FEAT,
        "description": "add render subcommand",
        "changelog": ChangelogSections(
            added=[
                ChangelogEntry(
                    affected_file="src/git_suggest/render.py",
                    project_context="commit message rendering",
                    change_statement="Add the render subcommand.",
                )
            ]
        ),
    }
    defaults.update(overrides)
    return DraftDocument(**defaults)


def test_format_header_with_scope() -> None:
    """A scoped doc renders `type(scope): description`."""
    doc = _doc(scope="cli")
    assert format_header(doc) == "feat(cli): add render subcommand"


def test_format_header_without_scope() -> None:
    """An unscoped doc renders `type: description`."""
    doc = _doc(scope=None)
    assert format_header(doc) == "feat: add render subcommand"


def test_render_commit_message_golden() -> None:
    """The full message matches the expected header + Keep a Changelog body."""
    doc = _doc(scope="cli")
    expected = (
        "feat(cli): add render subcommand\n"
        "\n"
        "### Added\n"
        "- **src/git_suggest/render.py**: Add the render subcommand."
    )
    assert render_commit_message(doc) == expected


def test_render_commit_message_with_no_changelog_entries_is_header_only() -> None:
    """With no changelog entries at all, the message is just the header."""
    doc = _doc(changelog=ChangelogSections())
    assert render_commit_message(doc) == "feat: add render subcommand"


def test_render_changelog_only_omits_header() -> None:
    """--changelog-only output has no conventional-commit header line."""
    doc = _doc(scope="cli")
    expected = "### Added\n- **src/git_suggest/render.py**: Add the render subcommand."
    assert render_changelog_only(doc) == expected


_entry_strategy = st.builds(
    ChangelogEntry,
    affected_file=st.text(min_size=1, max_size=15).filter(str.strip),
    project_context=st.text(max_size=15),
    change_statement=st.text(min_size=1, max_size=15).filter(str.strip),
)


_categories_strategy = st.fixed_dictionaries(
    {name: st.lists(_entry_strategy, max_size=3) for name in CHANGELOG_CATEGORIES}
)


@given(entries_by_category=_categories_strategy)
def test_render_never_drops_a_changelog_entry(entries_by_category: dict) -> None:
    """Every entry present in the draft document appears somewhere in the rendered message."""
    changelog = ChangelogSections(**entries_by_category)
    doc = _doc(changelog=changelog)
    message = render_commit_message(doc)
    for entry in all_entries(changelog):
        assert entry.affected_file in message
        assert entry.change_statement in message

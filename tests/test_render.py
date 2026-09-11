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
    apply_reference_prefix,
    format_entry_line,
    format_header,
    render_changelog_only,
    render_commit_message,
    wrap_body_text,
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


def test_apply_reference_prefix_prepends_when_given() -> None:
    """A reference prefixes the header as '<reference>: <header>'."""
    assert apply_reference_prefix("feat: x", "AMCC-12202") == "AMCC-12202: feat: x"


def test_apply_reference_prefix_no_op_when_absent() -> None:
    """With no reference, the header passes through unchanged."""
    assert apply_reference_prefix("feat: x", None) == "feat: x"


def test_render_commit_message_with_reference_prefixes_header_only() -> None:
    """render_commit_message's reference prefixes just the header line, not the body."""
    doc = _doc(scope="cli")
    message = render_commit_message(doc, reference="AMCC-12202")
    lines = message.splitlines()
    assert lines[0] == "AMCC-12202: feat(cli): add render subcommand"
    assert "AMCC-12202" not in "\n".join(lines[1:])


def test_wrap_body_text_wraps_at_width_with_hanging_indent() -> None:
    """wrap_body_text wraps long text, indenting continuation lines."""
    text = "one two three four five six seven eight nine ten"
    wrapped = wrap_body_text(text, width=20, subsequent_indent="  ")
    lines = wrapped.splitlines()
    assert all(len(line) <= 20 for line in lines)
    assert len(lines) > 1
    assert all(line.startswith("  ") for line in lines[1:])


def test_format_entry_line_wraps_long_statement_under_hanging_indent() -> None:
    """A long changelog entry wraps with continuation lines under the statement text."""
    entry = ChangelogEntry(
        affected_file="a.py",
        project_context="x",
        change_statement="a very long change statement that should wrap onto more than one line",
    )
    rendered = format_entry_line(entry, width=30)
    lines = rendered.splitlines()
    assert lines[0].startswith("- **a.py**: ")
    prefix_width = len("- **a.py**: ")
    assert all(line.startswith(" " * prefix_width) for line in lines[1:])


_text_strategy = st.text(
    alphabet=st.characters(blacklist_categories=("Cc", "Cs", "Zs", "Zl", "Zp")),
    min_size=1,
    max_size=15,
).filter(str.strip)

_entry_strategy = st.builds(
    ChangelogEntry,
    affected_file=_text_strategy,
    project_context=st.text(max_size=15),
    change_statement=_text_strategy,
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

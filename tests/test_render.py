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
        "- **src/git_suggest/render.py**:\n"
        "    Add the render subcommand."
    )
    assert render_commit_message(doc) == expected


def test_render_commit_message_with_no_changelog_entries_is_header_only() -> None:
    """With no changelog entries at all, the message is just the header."""
    doc = _doc(changelog=ChangelogSections())
    assert render_commit_message(doc) == "feat: add render subcommand"


def test_render_commit_message_includes_narrative_as_first_paragraph() -> None:
    """A non-empty narrative renders between the header and the changelog body."""
    doc = _doc(scope="cli", narrative="In this commit I added the render subcommand.")
    expected = (
        "feat(cli): add render subcommand\n"
        "\n"
        "In this commit I added the render subcommand.\n"
        "\n"
        "### Added\n"
        "- **src/git_suggest/render.py**:\n"
        "    Add the render subcommand."
    )
    assert render_commit_message(doc) == expected


def test_render_commit_message_omits_narrative_paragraph_when_empty() -> None:
    """The default empty narrative adds no extra paragraph or blank line."""
    doc = _doc(scope="cli")
    assert "In this commit" not in render_commit_message(doc)


def test_render_commit_message_narrative_only_no_changelog() -> None:
    """A narrative with no changelog entries renders as header + narrative, no trailing body."""
    doc = _doc(changelog=ChangelogSections(), narrative="In this commit I did nothing yet.")
    expected = "feat: add render subcommand\n\nIn this commit I did nothing yet."
    assert render_commit_message(doc) == expected


def test_render_changelog_only_omits_narrative() -> None:
    """--changelog-only never includes the narrative paragraph, even when present."""
    doc = _doc(scope="cli", narrative="In this commit I added the render subcommand.")
    assert "In this commit" not in render_changelog_only(doc)


def test_render_commit_message_wraps_long_narrative_at_width() -> None:
    """A long narrative wraps at the given width, with no indent on any line."""
    long_narrative = "In this commit " + ("word " * 20).strip()
    doc = _doc(changelog=ChangelogSections(), narrative=long_narrative)
    message = render_commit_message(doc, width=20)
    narrative_block = message.split("\n\n", 1)[1]
    lines = narrative_block.splitlines()
    assert len(lines) > 1
    assert all(len(line) <= 20 for line in lines)
    assert all(not line.startswith(" ") for line in lines)


def test_render_changelog_only_omits_header() -> None:
    """--changelog-only output has no conventional-commit header line."""
    doc = _doc(scope="cli")
    expected = "### Added\n- **src/git_suggest/render.py**:\n    Add the render subcommand."
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


def test_wrap_body_text_applies_initial_indent_to_first_line_too() -> None:
    """A given initial_indent lands on the first line as well as continuations."""
    text = "one two three four five six seven eight nine ten"
    wrapped = wrap_body_text(text, width=20, initial_indent="    ", subsequent_indent="    ")
    lines = wrapped.splitlines()
    assert all(len(line) <= 20 for line in lines)
    assert len(lines) > 1
    assert all(line.startswith("    ") for line in lines)


def test_format_entry_line_puts_statement_on_its_own_indented_line() -> None:
    """The label ('- **file**:') is its own line; the statement is indented below it."""
    entry = ChangelogEntry(
        affected_file="a.py",
        project_context="x",
        change_statement="a short change statement",
    )
    rendered = format_entry_line(entry, width=72, indent=4)
    lines = rendered.splitlines()
    assert lines[0] == "- **a.py**:"
    assert all(line.startswith("    ") for line in lines[1:])
    assert "".join(lines[1:]).strip() != ""


def test_format_entry_line_wraps_long_statement_all_lines_indented() -> None:
    """A long changelog entry wraps with every statement line under the fixed indent.

    No blank line separates the label from the statement, so the wrapped
    statement stays part of the same Markdown list item as a lazily
    continued paragraph, rather than becoming its own list-item paragraph.
    """
    entry = ChangelogEntry(
        affected_file="a.py",
        project_context="x",
        change_statement="a very long change statement that should wrap onto more than one line",
    )
    rendered = format_entry_line(entry, width=30, indent=4)
    lines = rendered.splitlines()
    assert lines[0] == "- **a.py**:"
    assert len(lines) > 2  # label line + at least two wrapped statement lines
    assert all(line.startswith("    ") for line in lines[1:])
    assert all(len(line) <= 30 for line in lines[1:])
    assert "\n\n" not in rendered  # no blank line breaking the list item


def test_format_entry_line_long_filename_does_not_shrink_statement_wrap_width() -> None:
    """A long filename lives on its own label line, so it can't eat the wrap budget."""
    long_name = "src/" + "x" * 60 + "/file.py"
    entry = ChangelogEntry(
        affected_file=long_name,
        project_context="x",
        change_statement="a statement that needs the full width to fit on one line",
    )
    rendered = format_entry_line(entry, width=72, indent=4)
    lines = rendered.splitlines()
    assert lines[0] == f"- **{long_name}**:"
    # Full statement fits on one wrapped line since only the fixed 4-space
    # indent (not the long filename) constrains the statement's width.
    assert len(lines) == 2


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

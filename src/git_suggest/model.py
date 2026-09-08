"""The rigid, AI-produced structured commit document (ADR 0005, ADR 0007).

Models are frozen pydantic data containers with only short, data-focused
methods; composition happens via free functions, not object behavior.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict

#: Keep a Changelog category names, in their canonical display order.
CHANGELOG_CATEGORIES: tuple[str, ...] = (
    "added",
    "changed",
    "deprecated",
    "removed",
    "fixed",
    "security",
)


class CommitType(StrEnum):
    """The conventional-commit `type` field, constrained to a fixed set."""

    FEAT = "feat"
    FIX = "fix"
    DOCS = "docs"
    STYLE = "style"
    REFACTOR = "refactor"
    PERF = "perf"
    TEST = "test"
    BUILD = "build"
    CI = "ci"
    CHORE = "chore"
    REVERT = "revert"


class ChangelogEntry(BaseModel):
    """One structured change statement scoped to a single affected file."""

    model_config = ConfigDict(frozen=True)

    affected_file: str
    project_context: str
    change_statement: str


class ChangelogSections(BaseModel):
    """The six Keep a Changelog categories, each a list of entries."""

    model_config = ConfigDict(frozen=True)

    added: list[ChangelogEntry] = []
    changed: list[ChangelogEntry] = []
    deprecated: list[ChangelogEntry] = []
    removed: list[ChangelogEntry] = []
    fixed: list[ChangelogEntry] = []
    security: list[ChangelogEntry] = []


class DraftDocument(BaseModel):
    """The rigid intermediate document produced by `draft`, consumed by `render`."""

    model_config = ConfigDict(frozen=True)

    type: CommitType
    scope: str | None = None
    description: str
    changelog: ChangelogSections = ChangelogSections()


def sections_of(changelog: ChangelogSections) -> list[tuple[str, list[ChangelogEntry]]]:
    """Return (category_name, entries) pairs in Keep a Changelog order."""
    return [(name, getattr(changelog, name)) for name in CHANGELOG_CATEGORIES]


def all_entries(changelog: ChangelogSections) -> list[ChangelogEntry]:
    """Return every entry across all categories, in category order."""
    return [entry for _, entries in sections_of(changelog) for entry in entries]

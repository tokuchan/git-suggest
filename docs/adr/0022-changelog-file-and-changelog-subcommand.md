# CHANGELOG.md, Keep a Changelog format, updated by a new `changelog` subcommand

A `CHANGELOG.md` is added at the repo root, in standard Keep a Changelog
form: an `## [Unreleased]` section at the top, followed by dated version
sections (newest first), each broken into the same six categories already
used throughout this project (`### Added`, `### Changed`, `### Deprecated`,
`### Removed`, `### Fixed`, `### Security`).

**Backfill is deliberately lightweight.** Rather than building a new
capability to reconstruct itemized entries for the ~30 commits leading up
to the first CalVer release, the file starts with one hand-written entry:
`## [26.09.0] - 2026-09-30` with a short prose note marking it as the
initial public release. Itemized, per-commit entries start accumulating
from here forward. Reconstructing granular historical entries after the
fact wasn't worth a new feature surface just to backfill.

**A new `changelog` subcommand appends entries going forward**, matching
CONTEXT.md's own long-standing framing of git-suggest's subcommands as
independently reusable ("e.g. to update a project's changelog"). It takes
a `DraftDocument` as input — the same contract `render` already uses, so
it composes the same way: `git-suggest scan | git-suggest draft |
git-suggest changelog`. It reuses `model.py`'s existing `sections_of`/
category-ordering logic to find-or-create the right `### <Category>`
subheading within the `## [Unreleased]` block and appends each entry's
rendered bullet at the end of that subheading's list, in canonical
category order. Entries are never deduped against existing ones — two
commits touching the same file are two legitimate separate facts about
it, same as within a single commit's changelog already works.

This is a separate, explicit step you run when you choose to (ADR 0003's
small-composable-steps philosophy), not bundled into `--commit`/`--edit`:
a WIP commit you intend to squash later shouldn't necessarily get its own
changelog entry.

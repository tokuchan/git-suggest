# A separate `release` subcommand stamps CHANGELOG.md, tag-aware on compare links

A new `release` subcommand reads the current (already-bumped)
`pyproject.toml` version, renames `CHANGELOG.md`'s `## [Unreleased]`
heading to `## [<version>] - <today's date>`, inserts a fresh empty
`## [Unreleased]` above it, updates the footer's reference-style compare
links, and commits `CHANGELOG.md`. It takes no arguments beyond the
project path (same pattern as `bump`): the version to stamp always comes
from reading the file, never a passed-in argument, since that's always
exactly what `bump` already wrote there.

**Deliberately decoupled from `bump` and the pre-push hook (ADR 0021).**
`bump` stays plain and reusable, with zero awareness of this project's
own `CHANGELOG.md` — extending it to also rewrite the changelog would
re-litigate that boundary after the fact. Not every bumped push is a
"release" worth announcing in the changelog, so `release` is a separate,
manually-invoked step, run whenever you (or I, when asked) decide a
release is actually worth stamping.

**Compare links prefer a tag, falling back to a commit SHA.** Standard
Keep a Changelog templates end with links like `[Unreleased]:
.../compare/v1.1.0...HEAD`, which assume release tags exist. ADR 0021
introduced none. `release` first checks for a tag named `v<version>`
(the chosen convention, e.g. `v26.09.0` — also the convention a future
`bump --tag` option would use, keeping both paths consistent); if found,
the compare link uses it exactly like the standard template. If not
found, it falls back to a commit SHA, resolved via `git log -S'version =
"<version>"' -- pyproject.toml` — a pickaxe search for whichever commit
introduced that exact version line. This works uniformly whether that
commit was a normal `bump` commit or a hand-edited one (like the initial
26.09.0 switchover, whose commit message doesn't match `bump`'s own
template at all). The very first version ever stamped has no prior
version to compare against, so it gets no compare link — standard
practice for a changelog's oldest entry.

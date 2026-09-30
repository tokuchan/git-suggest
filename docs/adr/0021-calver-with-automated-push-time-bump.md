# CalVer (YY.MM.patch) versioning, bumped by a pre-push hook calling a plain subcommand

`pyproject.toml`'s `version` switches from unbumped semver (`0.1.0`) to
CalVer: `YY.MM.patch`, e.g. `26.09.0`. `patch` counts releases within a
given `YY.MM` and resets to `0` when the month changes, so it reads as
"the Nth release this month." This commit hand-sets the version to
`26.09.0` as the one-time switchover; every push after this one is where
the automation below takes over.

**The bump tool is plain, and reusable.** `git-suggest bump` is a new
subcommand: it reads the current version from `pyproject.toml`, computes
the next one from today's date, rewrites the file, and commits the
change (message: "chore(release): bump version to `<version>`"). It knows
nothing about git push, branches, or remotes — consistent with this
project's own framing of its subcommands as independently reusable (e.g.
"to update a project's changelog"), so any project can call it the same
way. `pyproject.toml`'s `version = "..."` line is rewritten with a
targeted regex substitution rather than a full TOML round-trip (e.g. via
`tomlkit`): the file's shape is fully under this project's control, and a
one-line edit doesn't need a new dependency.

**All push-specific policy lives in the hook, not the tool.** A tracked
`.githooks/pre-push` script (activated via `git config core.hooksPath
.githooks` — a one-time step per clone, since `core.hooksPath` itself
isn't something git versions) does the orchestration: it only acts on
pushes updating `refs/heads/master`; it refuses to bump (with a clear
message) if the working tree isn't clean, to keep the bump commit
surgical; and it compares the local `pyproject.toml` version against the
version at the remote-tracking SHA already provided on the hook's stdin
(via `git show <remote-sha>:pyproject.toml`, no extra fetch needed). If
they already differ, the version for this push has already been decided
— by a previous bump-and-retry cycle, or by hand (as with this very
commit) — and the hook lets the push through unbumped. Otherwise it calls
`git-suggest bump` and aborts the push, asking for a manual retry.

**The hook cannot complete the push it fires from, so it asks for a
retry instead of trying to be fully seamless.** git's pre-push hook
receives the ref updates it's about to push before it runs; a commit
made inside the hook does not retroactively become part of that same
push. The reliable fix is to bump, commit, and abort (exit non-zero)
with a message to run `git push` again — the next invocation naturally
picks up the new commit and (per the paragraph above) sees local/remote
versions already differ, so it passes through without bumping again. The
alternative — having the hook recursively invoke `git push` itself,
guarded against re-entering — would make a single `git push` fully
sufficient, but trades that convenience for a failure mode (e.g. a
network drop mid-recursion) that's confusing to debug. Not chosen.

No git tags are introduced by this. `pyproject.toml` alone holds the
version; if release tags (for GitHub releases, `uv tool install` pinning,
etc.) become useful later, that's a separate decision with its own
tradeoffs (tag format, who pushes them, what consumes them).

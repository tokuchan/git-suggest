# stage-related: git-native hunk splitting, patch-based staging, one intent per run

`stage-related` is the workflow this project set out to support: stage
one hunk by hand, then run `git-suggest stage-related` to pull in every
other hunk that belongs with it, splitting any hunk that actually covers
more than one concern.

**Splitting reuses git's own deterministic algorithm, not an AI call.**
`git add -p`/`add -i`'s `s` command already splits a hunk into smaller
hunks wherever there's a contiguous run of unchanged lines between
changed blocks. `stage-related` reuses exactly that splitting boundary
rather than asking an AI backend to partition a hunk's diff text into
labeled sub-concerns — free, deterministic, and already exactly what a
human reviewer reaches for today. The tradeoff: it can't split *within*
a single contiguous run of changed lines the way an AI-assisted read of
the diff's content might. Accepted for now; AI-assisted splitting is a
reasonable follow-up if git's own granularity proves too coarse in
practice.

**Candidates are evaluated against one intent, drafted once per run.**
Before scoring any candidate, `stage-related` asks the existing
prose-based AI backend (the same claude/copilot/opencode priority list
`draft` already uses) for a single short sentence describing what the
currently-staged selection is about — not a full `DraftDocument`, just
the one line this feature needs. Every candidate hunk's decision-backend
call (ADR 0025) then asks "does this belong with: `<that intent>`?"
rather than repeating the full staged diff as context on every one of
what could be many per-candidate calls. One cheap AI call up front, many
cheap decision-backend calls after.

**Candidates include both unstaged hunks in tracked files and whole
untracked files.** An untracked new file is treated as a single
candidate (no internal splitting, since there's no "already there"
baseline to diff against).

**Staging constructs a patch per chosen hunk and applies it with `git
apply --cached`** — the same underlying mechanism `git add -p` itself
uses once you've picked a hunk, just invoked directly rather than
scripting `add -p`'s interactive keystroke protocol.

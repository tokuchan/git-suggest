# git-suggest

## Rules

ALL changes must comport with ALL ADRs in `docs/adr/`, as written. If a
change would conflict with an ADR, or two ADRs conflict with each other,
stop and clarify with the project owner before proceeding — do not silently
resolve the conflict or override an ADR.

A CLI tool that scans staged git changes, drafts a structured commit-message
document via an AI agent, and renders it as a conventional-commit message
with a Keep a Changelog-style body. Built as a standalone `uv`-installable
Python package so it can also be reused (e.g. inside `lazygit`) and its
subcommands reused independently (e.g. to update a project's changelog).

## Language

**Scan report**:
A concise, plain-text summary of the staged diff (`git diff --cached`),
produced by the `scan` subcommand and intended as input to an AI agent.
_Avoid_: diff, patch

**Draft document**:
The structured JSON document produced by the `draft` subcommand: subject
fields (type/scope/description), a narrative, and a changelog-entries
structure. This is the "rigid format" intermediate representation between
`scan` and `render`.
_Avoid_: commit JSON, message object

**Narrative**:
An optional free-text paragraph on a draft document answering *why* a
commit exists: the problem it solves, then the intent behind its
solution. Written in first-person, active voice, starting with the
literal phrase "In this commit". Distinct from `description` (the
one-line subject) and a changelog entry's `change_statement` (a single
grounded fact about one file's change); `render` places it as the
message's first paragraph, ahead of the changelog body.
_Avoid_: rationale, intent, motivation

**Changelog entry**:
One structured statement within a draft document's changelog-entries,
scoped to exactly one of the six Keep a Changelog categories (added,
changed, deprecated, removed, fixed, security). Holds the affected file,
project context, and change statement.
_Avoid_: change item, log line

**AI backend**:
An external AI-capable CLI (`claude`, `copilot`, or `opencode`) that
`draft` shells out to, in that priority order, using the first one found
working on the system.
_Avoid_: AI agent, model, LLM

**Commit type**:
The conventional-commit `type` field in a draft document, constrained to a
fixed enum: feat, fix, docs, style, refactor, perf, test, build, ci, chore,
revert.
_Avoid_: category, kind

**Config file**:
`~/.config/git-suggest/config.toml`, controlling AI backend priority order,
per-backend command/model override flags, and context-scope overrides
(how much repo context `draft` gathers). Every default value in the tool is
defined as a config field, never hardcoded, so it's always overridable here.
_Avoid_: settings, preferences

**Config model**:
The frozen (immutable) pydantic model holding merged config (built-in
defaults + TOML overrides), produced once per process by a memoized pure
function and passed explicitly to the functions that need it.
_Avoid_: config manager, config singleton, Borg

**Reference prefix**:
A literal string (from `-r/--reference`, or the current branch name from
`-b/--branch-reference`) prepended to the rendered commit subject as
`"<reference>: "`, ahead of the conventional-commit `type(scope): `
segment. Stitched on at render time; never part of the AI-produced draft
document.
_Avoid_: ticket prefix, issue tag

**Subject budget**:
The pair of character-count hints (`max`, `preferred`) that `scan` computes
from the reference prefix's length and embeds as a leading line in its
plain-text report, so `draft` can instruct the AI backend how much room
the `type(scope): description` portion of the subject has before the
hard 72-character and preferred 50-character subject-line limits are hit.
_Avoid_: length limit, character budget

**Repo-relative output path**:
The git-dir-anchored file target from `-R`/`--output-repo-path`, resolved
via `git rev-parse --absolute-git-dir` so it lands in `.git/` (or
`.git/modules/<submodule>/`, or `.git/worktrees/<name>/`, whichever
applies), rejecting values that try to escape that directory. Mutually
exclusive with `-o`/`--output-path`.
_Avoid_: git-dir path, repo path

**CalVer version**:
This project's own `pyproject.toml` version, in `YY.MM.patch` form (e.g.
`26.09.0`): two-digit year, two-digit month, and a patch counting
releases within that month, resetting to `0` when the month changes.
Distinct from the conventional-commit `type` enum and unrelated to
semver; this project has no major/minor concept.
_Avoid_: semver, release number

**Bump**:
The act of computing and writing this project's next CalVer version,
performed by the `bump` subcommand: read the current version, compute
the next one from today's date, rewrite `pyproject.toml`, and commit the
change. Knows nothing about git push, branches, or remotes — that policy
lives in the pre-push hook that calls it.
_Avoid_: release, cut a version

**Pre-push version hook**:
The tracked `.githooks/pre-push` script (activated once per clone via
`git config core.hooksPath .githooks`) that decides *whether* to bump:
only on a push updating `refs/heads/master`, only with a clean working
tree, and only when the local `pyproject.toml` version still matches the
version at the remote-tracking SHA already being pushed. When those hold,
it calls `bump` and aborts the push, asking for a manual retry — a
commit made inside the hook can't retroactively join the push already in
flight.
_Avoid_: git hook, release hook

## Subcommands

**scan**: produces a scan report from staged changes.
**draft**: turns a scan report (plus repo context) into a draft document via an AI backend.
**render**: turns a draft document into a final commit message, or (with `--changelog-only`) just the Keep a Changelog body fragment.
**bump**: computes this project's next CalVer version, rewrites `pyproject.toml`, and commits the change.
**git-suggest** (bare): chains scan → draft → render, printing to stdout by default; `--edit` opens `git commit -e -F -`, `--commit` runs `git commit -F -` non-interactively.

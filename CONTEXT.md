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
fields (type/scope/description) plus a changelog-entries structure. This is
the "rigid format" intermediate representation between `scan` and `render`.
_Avoid_: commit JSON, message object

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

## Subcommands

**scan**: produces a scan report from staged changes.
**draft**: turns a scan report (plus repo context) into a draft document via an AI backend.
**render**: turns a draft document into a final commit message, or (with `--changelog-only`) just the Keep a Changelog body fragment.
**git-suggest** (bare): chains scan → draft → render, printing to stdout by default; `--edit` opens `git commit -e -F -`, `--commit` runs `git commit -F -` non-interactively.

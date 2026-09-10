# Copilot instructions for git-suggest

## What this is

A CLI (`git-suggest`) that drafts a conventional-commit message with a Keep
a Changelog body from **staged** git changes, by shelling out to an AI CLI
(`claude`, `copilot`, or `opencode`, in that priority order). It has three
composable subcommands — `scan`, `draft`, `render` — each reading
stdin/writing stdout by default (`--input`/`--output` override this), so
`git-suggest scan | git-suggest draft | git-suggest render` is equivalent
to the bare `git-suggest` command.

## Rules (non-negotiable)

**All changes must comport with every ADR in `docs/adr/`, as written.** If
a change would conflict with an ADR, or two ADRs conflict with each other,
stop and ask the project owner — do not silently resolve the conflict or
override an ADR. Read `docs/adr/*.md` and `CONTEXT.md` (project glossary)
before making non-trivial changes.

## Build, test, lint

```sh
uv sync --group dev        # install deps incl. dev group (pytest, hypothesis, ruff)
uv run pytest              # full test suite
uv run pytest tests/test_render.py            # single file
uv run pytest tests/test_render.py::test_name # single test
uv run ruff check .        # lint
uv run ruff format .       # format
```

Tests use `pytest` golden-file tests for `scan`/`render` plus `hypothesis`
for property-based tests (ADR 0009). Commits are made only after tests pass
locally, one working unit at a time (ADR 0010) — don't leave a commit with
failing or unrun tests.

## Architecture (`src/git_suggest/`)

- `cli.py` — Click entry point wiring `scan` → `draft` → `render`. Owns
  stdin/stdout/`--input`/`--output` handling and the bare-command chain.
- `scan.py` — turns `git diff --cached` into a plain-text scan report: full
  diffs for text files, filenames only for binary files, no truncation
  (ADR 0004).
- `draft.py` — gathers repo context itself (tracked files, README, recent
  commit log — not passed in from outside, ADR 0006), builds a prompt from
  the scan report + context, calls the AI backend, and validates the
  response into a `DraftDocument`.
- `backends.py` — picks the first working AI CLI on `PATH` from
  `config.backend_order` (default: `claude`, `copilot`, `opencode`,
  ADR 0002) and returns a runner function for it.
- `model.py` — pydantic `DraftDocument`: commit `type` (fixed conventional-
  commit enum: feat/fix/docs/style/refactor/perf/test/build/ci/chore/
  revert)/`scope`/`description`, plus changelog entries. This is a stable
  external contract, so JSON keys are snake_case matching field names
  directly (ADR 0005) — don't add camelCase/kebab-case aliasing.
- `render.py` — turns a `DraftDocument` into the final commit message, or
  (with `--changelog-only`) just the Keep a Changelog body fragment.
- `config.py` — `Config` is a **frozen** pydantic model (immutable, not a
  Borg/singleton with mutable state, ADR 0008), built once per process by
  `get_config()` (`functools.cache`-memoized) from defaults merged with
  `~/.config/git-suggest/config.toml`, then passed explicitly into the
  functions that need it. **Every tunable default must be a `Config`
  field** — never hardcode a default inline; it must be overridable via
  the TOML file.
- `logging_utils.py` — progress (entering/leaving scan/draft/render, git
  calls, AI round trip) goes through Python `logging`, always to stderr.
  On a TTY at default verbosity this drives a spinner instead of printing
  log lines; `--log`, non-TTY stdout, or `-v`/`-q` moving off `INFO` forces
  log lines. Use `logger.info(...)` for this progress narration, not
  `print`/`click.echo` (those are reserved for actual command output).

## Conventions

- **Functional style** (ADR 0007): small, single-purpose, composable
  functions, not stateful "manager" classes. Prefer a function returning a
  function (currying) over an object holding config in instance state.
  Pydantic models are fine as data containers with short methods, not as
  behavior-heavy mutable services.
- Subcommands must stay composable via stdin/stdout — don't add behavior
  that only works when subcommands are chained in-process.

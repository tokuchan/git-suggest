# git-suggest

Generate a suggested git commit message from your **staged** changes:
a conventional-commit header plus a Keep a Changelog-style body,
drafted by shelling out to an AI CLI you already have installed.

## How it works

1. **scan** — turns `git diff --cached` into a concise report (full diffs
   for text files, filenames only for binary files).
2. **draft** — sends the scan report plus repo context (tracked files,
   README, recent commit log) to an AI backend, and validates its
   response into a rigid JSON "draft document" (subject type/scope/
   description, an optional narrative, plus Keep a Changelog entries per
   category).
3. **render** — turns a draft document into the final commit message
   (or, with `--changelog-only`, just the changelog body fragment).

Each subcommand reads stdin/writes stdout by default (`--input`/`-o`/
`--output-path` override this; `-` means stdin/stdout explicitly), so they
compose:

```sh
git-suggest scan | git-suggest draft | git-suggest render
```

Running `git-suggest` with no subcommand does exactly that chain for you.

## Install

```sh
uv tool install git+https://github.com/tokuchan/git-suggest
```

## Usage

```sh
git add -p                 # stage what you want to commit
git-suggest                # print a suggested commit message to stdout
git-suggest --edit          # ...then open it in `git commit -e -F -`
git-suggest --commit        # ...or commit it non-interactively
git-suggest -o out.txt      # ...or write it to a file (-a to append)
git-suggest -R LAZYGIT_PENDING_COMMIT  # ...or write it inside .git/
git-suggest -r AMCC-12202   # ...prefixed with "AMCC-12202: "
git-suggest -b              # ...prefixed with the current branch name
```

Because the default (no flags) prints plain text to stdout, `git-suggest`
also works as a custom command inside [lazygit](https://github.com/jesseduffield/lazygit)
to populate a commit message suggestion.

## Reference prefixes

`-r/--reference REF` prefixes the rendered subject with `"REF: "`, ahead of
the conventional-commit `type(scope): ` segment — handy for ticket IDs.
`-b/--branch-reference` does the same using the current branch name
verbatim. The two are mutually exclusive. Both are also accepted by `scan`
and `render` (`scan` uses them only to size the subject-length budget it
hands to `draft`; `render` is where the literal prefix text is applied).

## Repo-relative output

`-R/--output-repo-path PATH` (accepted anywhere `-o/--output-path` is)
writes output to `PATH` resolved inside the current repo's git directory
— `.git/`, or `.git/modules/<submodule>/`, or `.git/worktrees/<name>/`,
whichever applies — rather than a literal `.git/` under the working
directory, so it still works correctly from inside a submodule or a
linked worktree. This is how tools like lazygit expect their own
temporary files (e.g. `LAZYGIT_PENDING_COMMIT`) to be found:

```sh
git-suggest -R LAZYGIT_PENDING_COMMIT
```

`PATH` must be relative and can't `..` its way out of that directory;
`-o/--output-path` and `-R/--output-repo-path` are mutually exclusive.

## Subject and body length

The rendered subject line (reference prefix + `type(scope): description`)
targets 72 characters as a hard cap, and 50 as a preferred cap, matching
conventional git commit-message style. `draft` asks the AI backend for
this directly and retries with a shorter `description` (up to 3 times) if
the response comes back too long, falling back to the shortest attempt
with a logged warning rather than failing outright. Changelog body bullets
wrap at 72 columns with a hanging indent under the bullet's text.

## Narrative

`draft` also asks the AI backend for a `narrative`: a short paragraph
starting with the literal phrase "In this commit", written in first-person
active voice, describing the problem the commit solves and the intent
behind its solution. `render` places it as the message's first paragraph,
ahead of the changelog body; `--changelog-only` never includes it. Set
`narrative_enabled = false` in the config file to stop asking for one.

## Output and logging

Progress (entering/leaving scan/draft/render, git calls, the AI round trip)
is reported via Python logging, always written to stderr so stdout stays
pipe-clean. By default, on a real terminal, this drives a spinner's text
instead of printing log lines; add `--log` to force log lines instead, which
also happens automatically when stdout isn't a terminal or when `-v`/`-q`
moves verbosity away from the default `INFO` level.

- `-v` / `-q` (repeatable, e.g. `-vv`, and `-vq` cancels): raise/lower the
  log level (`INFO` by default, up to `DEBUG`, down to `CRITICAL`).
- `--log`: print log lines instead of a spinner, even on a TTY at the
  default level.

## AI backend

`draft` shells out to the first of these found on `PATH`, in order:
`claude` (claude-code), `copilot` (GitHub Copilot CLI), `opencode`.

## Configuration

All defaults are overridable via `~/.config/git-suggest/config.toml`,
including backend priority order, per-backend command overrides, and how
much repo context `draft` gathers:

```toml
backend_order = ["copilot", "claude", "opencode"]
context_log_line_count = 50
context_include_readme = true
output_style = "auto"  # auto | always | never
subject_max_length = 72
subject_preferred_length = 50
subject_retry_attempts = 3
body_wrap_width = 72
narrative_enabled = true
release_commit_message_template = "chore(release): bump version to {version}"
```

## Versioning

This project's own version (`pyproject.toml`) follows CalVer: `YY.MM.patch`
(e.g. `26.09.0`), where `patch` counts releases within that month and resets
to `0` when the month changes. `git-suggest bump` computes, writes, and
commits the next version; it's plain and reusable (it knows nothing about
git push, branches, or remotes), so any project can call it directly:

```sh
git-suggest bump                       # bump ./pyproject.toml
git-suggest bump --project-path path/to/pyproject.toml
```

## Development

```sh
uv sync --group dev
uv run pytest
uv run ruff check .
uv run ruff format .
```

Run this once per clone to enable the tracked pre-push hook, which bumps
the version automatically (ADR 0021):

```sh
git config core.hooksPath .githooks
```

It only acts on pushes to `master`, refuses to bump with a dirty working
tree, and skips bumping when the version was already decided some other
way (e.g. a previous bump-and-retry cycle). On a real bump it commits the
change and aborts the push, asking you to run `git push` again — a
commit made inside the hook can't retroactively join the push already in
flight.

Architecture decisions are recorded in `docs/adr/`; the project glossary is
in `CONTEXT.md`. All changes must comport with every ADR as written.

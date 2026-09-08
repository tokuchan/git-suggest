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
   description, plus Keep a Changelog entries per category).
3. **render** — turns a draft document into the final commit message
   (or, with `--changelog-only`, just the changelog body fragment).

Each subcommand reads stdin/writes stdout by default (`--input`/`--output`
override this), so they compose:

```sh
git-suggest scan | git-suggest draft | git-suggest render
```

Running `git-suggest` with no subcommand does exactly that chain for you.

## Install

```sh
uv tool install git+https://github.com/<you>/git-suggest
```

## Usage

```sh
git add -p                 # stage what you want to commit
git-suggest                # print a suggested commit message to stdout
git-suggest --edit          # ...then open it in `git commit -e -F -`
git-suggest --commit        # ...or commit it non-interactively
```

Because the default (no flags) prints plain text to stdout, `git-suggest`
also works as a custom command inside [lazygit](https://github.com/jesseduffield/lazygit)
to populate a commit message suggestion.

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
```

## Development

```sh
uv sync --group dev
uv run pytest
uv run ruff check .
uv run ruff format .
```

Architecture decisions are recorded in `docs/adr/`; the project glossary is
in `CONTEXT.md`. All changes must comport with every ADR as written.

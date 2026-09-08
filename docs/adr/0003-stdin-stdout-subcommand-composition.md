# Subcommands compose via stdin/stdout, with optional --input/--output file flags

`scan`, `draft`, and `render` each read from stdin and write to stdout by
default (overridable with `--input FILE` / `--output FILE`), so they compose
as `git-suggest scan | git-suggest draft | git-suggest render` and remain
independently reusable — e.g. by a future changelog-update tool that only
needs `draft` + `render --changelog-only`.

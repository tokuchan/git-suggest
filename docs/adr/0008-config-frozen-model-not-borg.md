# Config is a frozen model loaded once via a memoized pure function, not a Borg

A Borg-pattern config object (shared mutable state singleton) was considered
and rejected: it conflicts with ADR 0007's functional style (no manager
objects, no implicit shared mutable state). Instead, config is a frozen
(immutable) pydantic model, produced by a pure function memoized with
`functools.cache` so it's only read/merged from disk once per process, then
passed explicitly into the functions that need it. Every default value in
the tool must be defined as a config field with that default, never
hardcoded inline, so every default is overridable via
`~/.config/git-suggest/config.toml`.

# Commit gate extends to formatting and linting, not just tests

ADR 0010 required only that tests pass before a commit. In practice `ruff
format --check` and `ruff check` (ADR 0011) are just as cheap to run and
just as capable of leaving the repo in a broken or inconsistent state if
skipped, so the gate now requires all three — `ruff format --check`,
`ruff check`, and `uv run pytest` — to pass locally before any commit.
This ADR supersedes ADR 0010's narrower "tests only" gate; ADR 0010 is kept
for history but its rule is superseded by this one.

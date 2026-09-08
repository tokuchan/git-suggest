# ruff for formatting, import sorting, and linting

`ruff` replaces the separate black + isort + flake8 combination: it
implements black-compatible formatting, isort-compatible import sorting,
and flake8-style linting in one tool, run in CI/pre-commit as
`ruff format` and `ruff check`.

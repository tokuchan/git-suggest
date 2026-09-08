# git-suggest lives in its own repository, separate from home-manager

git-suggest is a general-purpose CLI tool useful outside the WSL/home-manager
dotfiles config, needs its own release lifecycle (versioning, tags), and must
be installable via `uv tool install` from a real Python package (a directory
with `pyproject.toml`). It is developed at `~/dev/git-suggest` and is not
wired into the home-manager Nix build; installation is a manual
`uv tool install` step, documented in this repo's README.

# --output-repo-path resolves against `git rev-parse --absolute-git-dir`, not a literal ".git/"

Tools like lazygit drop their own temporary files (e.g.
`LAZYGIT_PENDING_COMMIT`) directly into a repo's git directory, so a
custom command wired up to git-suggest needs to land its output in that
same place. `-R`/`--output-repo-path PATH` (alongside the existing
`-o`/`--output-path`, mutually exclusive with it) exists for that: it
resolves `PATH` against the *discovered* git directory rather than
assuming the literal `.git/` folder under the current working directory.

Naively joining onto `.git/` breaks for two common cases:

- **Submodules** — a submodule's working-tree `.git` is a *file*, not a
  directory, pointing at the superproject's `.git/modules/<name>/`; a
  literal `.git/PATH` join would try to write inside that file.
- **Worktrees** — a linked worktree's `.git` file points at
  `.git/worktrees/<name>/` under the main repo, not the main repo's own
  git directory.

`git rev-parse --absolute-git-dir` resolves both correctly (and returns
an absolute path regardless of how deep `PATH` is relative to the repo
root, unlike plain `--git-dir`, which can return a path relative to the
current working directory). `absolute_git_dir()` in `scan.py` wraps this
call for reuse alongside `current_branch()`.

`PATH` must be a relative path and may not `..` its way back out of the
discovered git directory; both are rejected with a `click.UsageError`
rather than silently resolved, matching this project's existing stance
on ambiguous flag combinations (ADR-recorded for `-r`/`-b`). Missing
parent directories under the git directory are not auto-created, keeping
this consistent with `-o`/`--output-path`'s existing behavior. Running
`--output-repo-path` outside a git repository is a `click.ClickException`
naming the problem, not a stack trace.

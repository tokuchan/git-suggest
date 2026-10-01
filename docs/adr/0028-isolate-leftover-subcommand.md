# isolate-leftover: stash by default, a detached worktree as an opt-in

After `stage-related` runs, whatever's still unstaged is the "leftover":
hunks the tool didn't think belonged with the current selection (or that
you rejected during confirmation). `isolate-leftover` gets it out of the
way so you can build/test the staged selection cleanly, without caring
whether `stage-related` is what produced that leftover — it just acts on
whatever's currently unstaged, the same staged/unstaged partition every
other git-suggest command already relies on.

**Defaults to `git stash push` (including untracked, via `-u`).** Lighter
weight than a worktree: no new directory to create or clean up
afterward, and `git stash pop` is the natural way back. `--mode=worktree`
is available as an explicit opt-in for when a separate directory to
build/test in is actually what's wanted.

**The worktree mode checks out a detached HEAD, not a new branch.** `git
worktree add --detach <path> HEAD`, then the leftover diff is applied
there as a constructed patch (the same mechanism `stage-related` itself
uses, ADR 0026). A detached checkout avoids git's restriction against
checking out the same branch in two worktrees at once, and leaves no
throwaway branch name behind to remember to delete later.

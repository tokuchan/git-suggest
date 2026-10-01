# A new `scan-ref` subcommand produces a scan report from a git ref or range

A new sibling subcommand, `scan-ref`, produces a scan report from an
arbitrary git ref or range instead of the staged diff — for commits that
already exist (e.g. rewording a fixup commit into a real one, or
describing an already-pushed range of work). It reuses `scan.py`'s
existing per-file formatting (`format_entry`, binary/text dispatch,
subject-budget line) exactly as-is, parameterized by a different diff
source; `draft`/`render` need no changes at all, since a scan report is
already opaque plain text to them regardless of where it came from.

Kept as a separate subcommand rather than a flag on `scan`, since `scan`'s
own glossary definition (CONTEXT.md) is specifically "a summary of the
staged diff" — folding in an unrelated diff source would blur that
rather than compose alongside it, matching how scan/draft/render/bump
already stay single-purpose and composable (ADR 0003).

**Refspec handling has two distinct cases, by git necessity, not
choice.** A bare single ref (no `..`) means "what that one commit changed
relative to its parent" — `git diff <ref>~1..<ref>`, equivalent to `git
show <ref>`'s diff. This is deliberate: `git diff <ref>` alone means
something different in git — that ref compared against the *working
tree* — which would not answer "what did this commit do," the actual
need (e.g. turning a fixup commit into a proper one). A refspec
containing `..` or `...` (a real range, e.g. `HEAD~3..HEAD`) is passed
straight through to `git diff <refspec>` unchanged, producing one
flattened report for the whole range — not one report per commit in it.
Per-commit iteration (e.g. for itemized historical changelog backfill)
is a bigger feature with its own design surface (scan/draft/render have
no looping contract anywhere today) and isn't needed for either of the
motivating use cases here.

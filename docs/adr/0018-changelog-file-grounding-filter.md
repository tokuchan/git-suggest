# Hallucinated changelog file attribution is dropped, not retried

Dogfooding (ADR 0017) surfaced a real failure: the AI backend drafted a
changelog entry attributing a change to a file that wasn't part of the
staged diff at all — it had echoed a filename from `Project context`
(specifically a recent commit's message) into the changelog for a
commit that never touched that file.

Two layers now guard against this:

1. `build_prompt` explicitly instructs the AI that `affected_file` must
   be copied verbatim from a `## <path>` header under "Staged changes",
   never from "Project context" (tracked files, README, recent commits),
   and that `change_statement` should stay concise and strictly grounded
   in what the diff shows. This reduces how often the problem occurs, but
   instruction-following alone isn't reliable enough to depend on.
2. After parsing the AI's response, `staged_files_in_report` re-parses
   the same scan report text's `## <path>` headers — the ground truth of
   what the AI was actually shown — and `drop_ungrounded_changelog_entries`
   drops any changelog entry whose `affected_file` isn't in that set,
   logging a warning naming the dropped file and statement. This check is
   controlled by `changelog_grounding_enabled` (default `true`) per this
   project's rule that every default lives on `Config`.

Dropping a hallucinated entry outright, rather than retrying with a
corrective follow-up prompt (the pattern ADR 0015 uses for over-length
subjects), was a deliberate choice: it costs no extra AI backend round
trip, and a silently-dropped entry is strictly better than a wrong one
reaching a commit message. The tradeoff is that a real entry lost to a
false-positive mismatch (e.g. the AI paraphrasing a path) is gone rather
than corrected — accepted because the priority here is that surviving
entries are correct and concise, not that every entry survives.

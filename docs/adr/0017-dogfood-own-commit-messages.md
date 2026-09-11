# This feature work's own commits are drafted with git-suggest itself

The commits implementing `-o/--output-path`, `-a/--append`,
`-r/--reference`, `-b/--branch-reference`, and the subject/body length
work are drafted using `git-suggest` itself (`uv run git-suggest
--commit`, run against the in-progress editable install), rather than
hand-written messages. This is deliberate dogfooding: it's the most direct
way to catch problems in the tool's own commit-message output while
building it. No `-r`/`-b` reference is used for these commits, since this
work isn't tied to a ticket and is being done directly on `master`.

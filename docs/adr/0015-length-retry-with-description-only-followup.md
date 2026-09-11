# Over-budget subjects are fixed with a bounded description-only retry

`draft` computes the real subject length (`type(scope): description`)
after the AI backend responds — the only point where `type`/`scope`
lengths are actually known — and compares it against the budget's `max`
from ADR 0014. If it's over budget, `draft` sends a short follow-up prompt
asking only for a revised `description` (keeping `type`/`scope`/
`changelog` fixed), up to 3 attempts. If every attempt is still over
budget, `draft` uses the shortest of the attempts, logs a warning with the
actual vs. target length, and proceeds rather than failing the whole
command.

A description-only follow-up (rather than re-requesting the full
`DraftDocument`) was chosen because it's cheaper and simpler to parse, and
`type`/`scope`/changelog rarely need to change just to shorten the
subject.

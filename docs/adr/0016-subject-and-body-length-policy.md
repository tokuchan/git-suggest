# Commit subject targets 50/72 chars; body wraps at 72 with hanging indent

The full rendered subject line (reference prefix + `type(scope): ` +
description) must not exceed 72 characters, and should stay at or under
50 when possible — both counted end-to-end, per conventional git-message
style. Below that hard cap, enforcement is a mix of a pre-agent budget
hint (ADR 0014) and a post-response retry (ADR 0015); there is no separate
runtime truncation/error path in `render` for the description itself.

Changelog body bullets (`- **file**: statement`) wrap at 72 columns with a
hanging indent, so continuation lines align under the statement text
rather than under the bullet marker. This wrapping is implemented as a
general-purpose body-wrap function in `render.py`, not one hardcoded to
changelog bullets specifically, so future free-text body content can reuse
it without a rewrite.

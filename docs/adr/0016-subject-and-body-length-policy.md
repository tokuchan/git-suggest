# Commit subject targets 50/72 chars; body wraps at 72 with a fixed entry indent

The full rendered subject line (reference prefix + `type(scope): ` +
description) must not exceed 72 characters, and should stay at or under
50 when possible — both counted end-to-end, per conventional git-message
style. Below that hard cap, enforcement is a mix of a pre-agent budget
hint (ADR 0014) and a post-response retry (ADR 0015); there is no separate
runtime truncation/error path in `render` for the description itself.

Changelog body bullets render as `- **file**:` on their own label line,
followed by the change statement wrapped at `body_wrap_width` (default
72) columns on the line(s) below, each indented by a fixed
`changelog_entry_indent` (default 4) columns — not aligned under the
statement text as a hanging indent. A long `affected_file` therefore
never eats into the statement's wrap budget: the indent is always the
same small width regardless of filename length. No blank line separates
the label from the statement, so the wrapped statement stays part of the
same Markdown list item (a lazily-continued paragraph under CommonMark's
list-item rules) rather than becoming a separate list-item paragraph;
this holds for any reasonable indent width, tight or loose.

This wrapping is implemented as a general-purpose body-wrap function in
`render.py` (`wrap_body_text`, supporting both `initial_indent` and
`subsequent_indent`), not one hardcoded to changelog bullets
specifically, so future free-text body content can reuse it without a
rewrite.

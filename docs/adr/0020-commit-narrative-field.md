# Draft document gets an optional narrative field, config-gated at draft time only

`DraftDocument` gains `narrative: str = ""`, positioned after `description`
and before `changelog`. It holds a short free-text paragraph answering
"why" a commit exists — the problem it solves and the solution's intent —
distinct from `description` (the one-line subject) and each changelog
entry's `change_statement` (a single grounded fact about one file). It is
optional with an empty-string default, not required, so every existing
hand-constructed `DraftDocument` (tests, and any externally-authored draft
JSON predating this field) keeps working unchanged — consistent with
`DraftDocument` being a stable external contract (ADR 0005).

`render_commit_message` renders `doc.narrative`, when non-empty, as the
message's first paragraph — after the header, before the changelog body —
wrapped at `body_wrap_width` with no extra indent, reusing the
general-purpose `wrap_body_text` exactly as ADR 0016 anticipated for
future free-text body content. `render_changelog_only` does not include
it: that mode's contract is specifically "just the changelog body
fragment," and a narrative paragraph isn't a changelog entry.

A new `narrative_enabled: bool = True` config field (per ADR 0006/0008,
every default lives on `Config`) gates only whether `draft`'s prompt asks
the AI to produce a narrative — mirroring `changelog_grounding_enabled`
(ADR 0018) as a draft-side concern. `render` has no `Config` dependency
today and stays that way: it renders whatever `narrative` value the
document actually holds, regardless of this flag, the same way it renders
whatever changelog entries a document holds regardless of grounding
settings.

The prompt instructs the narrative to start with the literal phrase "In
this commit", in first-person, active voice. This is enforced only by
instruction, not validated or retried at parse time — consistent with how
`description` and `change_statement` content/style are never
runtime-checked either; only structural fields (the `type` enum,
`affected_file` grounding) get that treatment. A stylistic prefix on a
low-stakes free-text field doesn't warrant a second AI round trip the way
an over-length subject (ADR 0015) or a hallucinated file (ADR 0018) does.

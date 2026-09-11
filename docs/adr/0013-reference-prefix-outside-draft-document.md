# Reference prefix is stitched on at render time, not part of the draft document

`-r/--reference` and `-b/--branch-reference` add a literal `"<ref>: "`
prefix to the final commit subject. It is applied in `render` (and the
bare command), never added as a field on `DraftDocument`, so the AI-facing
JSON contract in `model.py` stays exactly as defined by ADR 0005. `scan`
and `draft` only ever see the reference's *length*, not its text (see ADR
0014); only `render`/the bare command need the literal string, because
only they build the final printed subject line.

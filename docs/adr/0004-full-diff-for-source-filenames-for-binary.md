# scan includes full diffs for source files, filenames only for binary files

`scan` never truncates text/source diff hunks, even for large changesets,
because the AI agent in `draft` needs full context to write an accurate
change statement per file. Binary files are listed by filename only (no
attempt to represent binary content). This trades report size for
correctness; there is no line-count truncation threshold.

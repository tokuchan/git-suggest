# Testing: pytest golden files for scan/render, plus hypothesis for property tests

Golden-file tests (fixed input → expected output) cover `scan` and `render`
as pure functions. Where behavior is better described as a property that
must hold across many inputs (e.g. "render never drops a changelog entry
present in the draft document", "config merge never lets a TOML override
disappear") rather than as enumerable examples, use `hypothesis` to generate
cases instead of hand-writing many similar test cases.

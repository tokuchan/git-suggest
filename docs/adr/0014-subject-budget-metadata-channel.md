# Subject-length budget flows from scan to draft as a leading report line

`scan` accepts `-r/--reference`/`-b/--branch-reference` too, purely to
compute a subject-length budget: `max = 72 - len(prefix + ": ")` and
`preferred = max(0, 50 - len(prefix + ": "))`, using `72`/`50` unmodified
when no reference is given. This is embedded as a single leading line in
the otherwise plain-text scan report (e.g.
`# subject-budget: max=65 preferred=43`), which `draft` parses back out to
build its AI prompt instructions.

This keeps the reference's literal text out of the scan/draft path
entirely (ADR 0013) while still letting `draft` size its prompt correctly,
and — critically — keeps `scan | draft` composable over a single stdin/
stdout text stream (ADR 0003) instead of requiring a second, parallel
side-channel argument between the two subcommands. The commit `type`/
`scope` lengths are deliberately excluded from this pre-agent budget,
since the agent chooses them itself; ADR 0015 covers how the true,
post-response length is enforced instead.

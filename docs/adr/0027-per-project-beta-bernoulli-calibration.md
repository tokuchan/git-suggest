# Per-project Beta-Bernoulli calibration drives stage-related's confirm/auto-stage split

`stage-related`'s decision-backend call (ADR 0025) returns a probability
per candidate hunk, but a raw model probability isn't the same thing as
"how often does this user actually want hunks scored around here." A
calibration layer learns that mapping from your own confirm/reject
history and uses it to decide, per candidate, whether to auto-stage it,
auto-skip it, or ask.

**The model: fixed probability bins, each with its own Beta(α, β)
posterior.** The model's returned probability is bucketed into fixed
bins (deciles: 0.0–0.1, 0.1–0.2, … 0.9–1.0). Each bin maintains a
Beta(α, β) posterior over "given the model said roughly this, how often
do you actually want it included," updated by +1 to α (included) or β
(rejected) each time you confirm or reject a candidate that landed in
that bin. This was chosen over a smooth isotonic calibration curve: a
discrete per-bin Beta posterior needs no new dependency, persists as
plain JSON, and updates with simple arithmetic — an isotonic fit would
avoid bin-edge artifacts (a 0.69 and 0.71 candidate treated very
differently early on) but needs either a new dependency or a hand-rolled
incremental fit, for a benefit that matters less while few observations
exist anyway.

A plain Kalman filter was considered and explicitly rejected: Kalman
filters are built for continuous, linear-Gaussian measurements of a
hidden state, and a confirm/reject label at a known probability isn't
naturally that. Beta-Bernoulli per bin is the statistically native tool
for "learn a decision threshold from binary labels at known scores," and
produces the same autotuning, shrinking-uncertainty-band behavior
without an awkward fit.

**Auto-include/auto-exclude/ask cutoffs**, all `Config` fields:
`hunk_pick_credible_level` (default 0.90), `hunk_pick_auto_include_cutoff`
(default 0.9), `hunk_pick_auto_exclude_cutoff` (default 0.1). A bin
auto-includes once its 90% credible lower bound exceeds 0.9, auto-excludes
once its 90% credible upper bound is below 0.1, and otherwise is shown for
manual confirm/reject.

**Cold start is maximally cautious.** Before any history exists for a
bin, its Beta(1, 1) prior (uninformative) gives a wide credible interval
that straddles both cutoffs — so every candidate is shown for
confirmation until enough history narrows a bin's interval past one of
the cutoffs. This is deliberate: the feature starts as safe as a fully
manual review and only automates where its own track record has earned
it, rather than guessing at a hand-picked starting threshold.

**State is per-project, not global**, since one codebase's "what counts
as related" pattern (file layout, commit granularity habits) doesn't
necessarily transfer to another project. It's stored untracked inside
the repo's own git-dir — resolved via the same `absolute_git_dir()`
helper ADR 0019 already established, so it survives correctly inside
submodules/worktrees and is never accidentally committed or shared
across contributors with different judgment.

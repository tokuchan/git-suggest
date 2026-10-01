# A pluggable decision-backend abstraction: Laya in-process by default, HTTP for anything else

`stage-related`'s per-hunk inclusion judgment needs a fast, cheap,
probability-scored yes/no call — not a full prose-generating AI backend
round trip. Research into this category turned up three real products
that already converge on the same request/response shape: give it a
state (context text) plus a flat schema of typed questions (`choice`:
pick one of N options with a probability per option; `score`: an
expected level on an ordered rubric; `noul`: a calibrated P(true) for a
yes/no statement), get back typed answers in one forward pass, no
reasoning or generated text to parse:

- **Jev** (TypeSafe AI) — commercial, cloud-hosted, no self-hosting option.
- **Nimble** (Bespoke Labs, `bespokelabsai/nimble`) — open-weight (LoRA
  fine-tune of Qwen3.5-9B), but a heavy, hardware-specific stack
  (torch/mlx/transformers/peft, ~18GB+ for weights alone), meant to run
  as its own long-lived server (MLX on Apple Silicon, or CUDA).
- **Laya** (Convai Innovations, `pip install laya`) — open-weight
  (Apache 2.0), genuinely lightweight (ModernBERT-large, 421M params,
  ~808MB for the English checkpoint), and directly pip-installable.
  Runs fully in-process via its own Python API (`laya.load()` /
  `Router().predict()`), or self-hosted via `laya-serve`, which exposes
  the *exact same* `POST /v1/systemone` shape as Jev — explicitly
  documented as "Jev-compatible."

Because all three already share one contract, git-suggest defines a
single abstract decision-backend interface (state + flat choice/score/
noul schema in, typed answers + probabilities out) rather than bespoke
per-model integration code. Two concrete implementations exist behind
it:

1. **Laya, in-process, bundled as an optional extra** (e.g.
   `git-suggest[hunks]`) — calls the `laya` Python package directly, no
   subprocess or port to manage. This is the default, chosen specifically
   so the feature "just works" with nothing to stand up separately.
2. **A generic HTTP client**, for pointing at an already-running
   Jev-compatible server — covers a self-hosted Nimble deployment, a
   separately-run `laya-serve`, or (later) Jev's own cloud endpoint.

`Config.decision_backend` selects exactly one of these — there is no
priority-ordered auto-fallback list the way `backend_order` works for
the prose AI backends. Nimble (90.1%) and Laya (varies by checkpoint and
task) don't have an obvious "better, degrade to worse" ordering the way
claude/copilot/opencode roughly do; silently falling back to a different
model's accuracy profile without the user choosing that is worse than
just configuring one explicitly.

**Jev itself is deliberately out of scope for now.** The user explicitly
wants to run something local; the abstract contract leaves room to add
a Jev HTTP backend later without any redesign, since it already speaks
the same shape.

**Zero-shot accuracy expectations are set honestly.** Laya's own model
card is explicit that its stock checkpoints score only ~0.362 accuracy
on their own typed-decisions benchmark zero-shot (barely above a 0.318
random baseline) — their headline 0.766 number requires fine-tuning on
your own labeled data first, which is out of scope here. `stage-related`
ships with the stock checkpoint and leans on its calibration system
(ADR 0027) to compensate, rather than quietly overselling accuracy it
doesn't have out of the box.

**The per-hunk question uses `choice`, not `noul`.** Laya's own
documentation flags a known bug: `noul` can anchor on its own `true`/
`false` option labels instead of the actual content, confidently
returning "no" on clearly positive input. Their recommended workaround —
a neutral-keyed 2-option `choice` (e.g. `{"A": "belongs with the current
commit", "B": "is a separate concern"}`) instead of a literal boolean —
is what `stage-related` uses. This still yields a single scalar
probability (P(chosen option)) for the calibration system; nothing else
in the design changes.

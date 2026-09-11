> Superseded by ADR 0012: the gate now also requires formatting and lint
> checks to pass, not tests alone.

# Implementation proceeds via atomic, test-gated commits

While building git-suggest, each unit of work is committed only after its
tests pass locally. No commit is made with failing or unrun tests. This
keeps history bisectable and every commit in a working state.

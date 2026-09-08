# Implementation proceeds via atomic, test-gated commits

While building git-suggest, each unit of work is committed only after its
tests pass locally. No commit is made with failing or unrun tests. This
keeps history bisectable and every commit in a working state.

# draft shells out to an external AI CLI, trying claude, then copilot, then opencode

Rather than depend on a specific LLM SDK or API key, `draft` shells out to
whichever AI-capable CLI is already installed and working on the system,
checked in this priority order: `claude` (claude-code), `copilot`
(GitHub Copilot CLI), `opencode`. This avoids new credential management,
keeps the tool small, and lets the user's existing AI CLI setup (whichever
one they use day to day) drive commit-message drafting.

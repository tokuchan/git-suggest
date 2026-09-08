# draft gathers wider project context itself; a config file can override its scope

`draft` gathers project context (file listing, README, recent commit log)
itself via git commands — it is not passed in from outside. Both the AI
backend priority order and this context-gathering scope are overridable via
`~/.config/git-suggest/config.toml`, rather than hardcoded, since backend
availability and desired context depth are personal/environment-specific.

"""Command-line entry point wiring scan/draft/render together (ADR 0003, 0006).

Each subcommand reads stdin/writes stdout by default, overridable with
--input/--output. The bare command chains scan -> draft -> render.
"""

from __future__ import annotations

import logging
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from git_suggest.backends import get_backend_runner
from git_suggest.config import Config, get_config
from git_suggest.draft import run_draft
from git_suggest.logging_utils import (
    log_output_context,
    select_output_mode,
    set_level,
    verbosity_to_level,
)
from git_suggest.model import DraftDocument
from git_suggest.render import render_changelog_only, render_commit_message
from git_suggest.scan import build_scan_report

logger = logging.getLogger(__name__)

_INPUT_OPTION = click.option(
    "--input", "input_path", type=click.Path(path_type=Path), help="Read input from FILE."
)
_OUTPUT_OPTION = click.option(
    "--output", "output_path", type=click.Path(path_type=Path), help="Write output to FILE."
)

_CONFIG_EPILOG = """
\b
Key settings in ~/.config/git-suggest/config.toml (all defaults shown are
overridable there):
  backend_order                 AI backend priority, e.g. ["copilot", "claude"]
  backend_commands               per-backend executable name overrides
  context_include_readme         include README in AI context (default: true)
  context_include_file_listing   include tracked-file listing (default: true)
  context_log_line_count         recent commits included as context (default: 20)
  output_style                   "auto" | "always" | "never" rich styling (default: "auto")
"""


_NO_STAGED_CHANGES_MESSAGE = "No staged changes found; stage something first (`git add`)."


def read_input(input_path: Path | None) -> str:
    """Read text from --input FILE, or stdin otherwise."""
    return input_path.read_text() if input_path else sys.stdin.read()


def write_output(text: str, output_path: Path | None) -> None:
    """Write text to --output FILE, or stdout otherwise."""
    if output_path:
        output_path.write_text(text)
    else:
        click.echo(text)


def require_backend_runner(config: Config) -> Callable[[str], str]:
    """Return the configured backend runner, or raise a click error if none is available."""
    runner = get_backend_runner(config)
    if runner is None:
        raise click.ClickException(
            "No configured AI backend (claude/copilot/opencode) found on PATH."
        )
    return runner


def draft_document_from_scan(scan_report: str, config: Config) -> DraftDocument:
    """Run draft's context+prompt+backend pipeline for a given scan report."""
    return run_draft(scan_report, require_backend_runner(config), config)


def chain_scan_draft_render(config: Config) -> str | None:
    """Run scan -> draft -> render in-process, and return the rendered message.

    Returns None (without ever calling the AI backend) when there are no
    staged changes to describe. Progress is reported purely via logging,
    which log_output_context turns into either log lines or spinner text.
    """
    logger.info("Entering scan")
    scan_report = build_scan_report()
    logger.info("Leaving scan")
    if not scan_report.strip():
        return None
    logger.info("Entering draft")
    doc = draft_document_from_scan(scan_report, config)
    logger.info("Leaving draft")
    logger.info("Entering render")
    message = render_commit_message(doc)
    logger.info("Leaving render")
    return message


def print_message(message: str, style: str) -> None:
    """Print message, styled via rich when TTY/style calls for it, else plain."""
    should_style = {"always": True, "never": False}.get(style, sys.stdout.isatty())
    if should_style:
        Console().print(Panel(message, title="git-suggest"))
    else:
        click.echo(message)


def commit_with_message(message: str, edit: bool) -> None:
    """Run `git commit -F -`, adding -e when edit is True, feeding message via stdin."""
    args = ["git", "commit", "-e", "-F", "-"] if edit else ["git", "commit", "-F", "-"]
    subprocess.run(args, input=message, text=True, check=True)


@click.group(invoke_without_command=True, epilog=_CONFIG_EPILOG)
@click.option("--edit", is_flag=True, help="Open the message in `git commit -e -F -`.")
@click.option(
    "--commit", "do_commit", is_flag=True, help="Run `git commit -F -` non-interactively."
)
@click.option("-v", "--verbose", count=True, help="Increase log verbosity (repeatable: -v, -vv).")
@click.option(
    "-q", "--quiet", count=True, help="Decrease log verbosity (repeatable: -q, -qq); cancels -v."
)
@click.option(
    "--log", "want_log", is_flag=True, help="Print log lines instead of showing a spinner."
)
@click.pass_context
def main(
    ctx: click.Context,
    edit: bool,
    do_commit: bool,
    verbose: int,
    quiet: int,
    want_log: bool,
) -> None:
    """Draft a conventional-commit message with a Keep a Changelog body, from staged changes.

    \b
    Default flow (running `git-suggest` with no subcommand):
      1. scan   - summarize `git diff --cached` (full diffs for text files,
                  filenames only for binary files)
      2. draft  - ask an AI backend (claude, copilot, or opencode) to turn
                  that summary into a structured draft document
      3. render - format the draft into the final commit message

    The result is printed to stdout by default, so `git-suggest` also works
    as a custom command inside tools like lazygit. Pass --edit to open it in
    `git commit -e -F -`, or --commit to commit it non-interactively.

    Each of scan/draft/render can also be run and composed on its own, e.g.
    `git-suggest scan | git-suggest draft | git-suggest render`.
    """
    level = verbosity_to_level(verbose, quiet)
    set_level(level)
    mode = select_output_mode(sys.stdout.isatty(), want_log, level)
    ctx.obj = mode
    if ctx.invoked_subcommand is not None:
        return
    config = get_config()
    with log_output_context(mode):
        message = chain_scan_draft_render(config)
    if message is None:
        click.echo(_NO_STAGED_CHANGES_MESSAGE, err=True)
        return
    if edit or do_commit:
        commit_with_message(message, edit=edit)
    else:
        print_message(message, config.output_style)


@main.command("scan")
@_OUTPUT_OPTION
@click.pass_obj
def scan_command(mode: str, output_path: Path | None) -> None:
    """Print a concise report of staged changes (full diffs for text, filenames for binary)."""
    with log_output_context(mode):
        report = build_scan_report()
    write_output(report, output_path)


@main.command("draft")
@_INPUT_OPTION
@_OUTPUT_OPTION
@click.pass_obj
def draft_command(mode: str, input_path: Path | None, output_path: Path | None) -> None:
    """Turn a scan report (stdin, or --input) into a structured draft JSON document."""
    config = get_config()
    scan_report = read_input(input_path)
    if not scan_report.strip():
        click.echo(_NO_STAGED_CHANGES_MESSAGE, err=True)
        return
    with log_output_context(mode):
        doc = draft_document_from_scan(scan_report, config)
    write_output(doc.model_dump_json(indent=2), output_path)


@main.command("render")
@_INPUT_OPTION
@_OUTPUT_OPTION
@click.option("--changelog-only", is_flag=True, help="Render only the Keep a Changelog body.")
@click.pass_obj
def render_command(
    mode: str, input_path: Path | None, output_path: Path | None, changelog_only: bool
) -> None:
    """Render a draft JSON document (stdin, or --input) into a commit message."""
    doc = DraftDocument.model_validate_json(read_input(input_path))
    with log_output_context(mode):
        text = render_changelog_only(doc) if changelog_only else render_commit_message(doc)
    write_output(text, output_path)

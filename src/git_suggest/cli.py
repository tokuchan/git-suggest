"""Command-line entry point wiring scan/draft/render together (ADR 0003, 0006).

Each subcommand reads stdin/writes stdout by default, overridable with
--input/--output. The bare command chains scan -> draft -> render.
"""

from __future__ import annotations

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
from git_suggest.model import DraftDocument
from git_suggest.render import render_changelog_only, render_commit_message
from git_suggest.scan import build_scan_report

_INPUT_OPTION = click.option(
    "--input", "input_path", type=click.Path(path_type=Path), help="Read input from FILE."
)
_OUTPUT_OPTION = click.option(
    "--output", "output_path", type=click.Path(path_type=Path), help="Write output to FILE."
)


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


def chain_scan_draft_render(config: Config) -> str:
    """Run scan -> draft -> render in-process and return the rendered message."""
    doc = draft_document_from_scan(build_scan_report(), config)
    return render_commit_message(doc)


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


@click.group(invoke_without_command=True)
@click.option("--edit", is_flag=True, help="Open the message in `git commit -e -F -`.")
@click.option(
    "--commit", "do_commit", is_flag=True, help="Run `git commit -F -` non-interactively."
)
@click.pass_context
def main(ctx: click.Context, edit: bool, do_commit: bool) -> None:
    """Draft a commit message from staged changes (chains scan, draft, render)."""
    if ctx.invoked_subcommand is not None:
        return
    config = get_config()
    message = chain_scan_draft_render(config)
    if edit or do_commit:
        commit_with_message(message, edit=edit)
    else:
        print_message(message, config.output_style)


@main.command("scan")
@_OUTPUT_OPTION
def scan_command(output_path: Path | None) -> None:
    """Print a concise report of staged changes."""
    write_output(build_scan_report(), output_path)


@main.command("draft")
@_INPUT_OPTION
@_OUTPUT_OPTION
def draft_command(input_path: Path | None, output_path: Path | None) -> None:
    """Turn a scan report into a structured draft JSON document."""
    config = get_config()
    doc = draft_document_from_scan(read_input(input_path), config)
    write_output(doc.model_dump_json(indent=2), output_path)


@main.command("render")
@_INPUT_OPTION
@_OUTPUT_OPTION
@click.option("--changelog-only", is_flag=True, help="Render only the Keep a Changelog body.")
def render_command(input_path: Path | None, output_path: Path | None, changelog_only: bool) -> None:
    """Render a draft JSON document into a commit message."""
    doc = DraftDocument.model_validate_json(read_input(input_path))
    text = render_changelog_only(doc) if changelog_only else render_commit_message(doc)
    write_output(text, output_path)

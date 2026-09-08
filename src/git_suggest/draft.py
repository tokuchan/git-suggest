"""Turn a scan report into a validated DraftDocument via an AI backend.

Small functions compose: gather repo context, build a prompt, call a
backend runner (a curried function supplied by the caller), then parse and
validate the response.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from pathlib import Path

from git_suggest.config import Config
from git_suggest.model import DraftDocument
from git_suggest.scan import run_git

logger = logging.getLogger(__name__)


def find_readme(cwd: Path | None = None) -> str:
    """Return the content of the first top-level README* file, or "" if none."""
    base = cwd or Path.cwd()
    matches = sorted(base.glob("README*"))
    return matches[0].read_text() if matches else ""


def list_files(cwd: Path | None = None) -> str:
    """Return the tracked-file listing (`git ls-files`)."""
    return run_git("ls-files", cwd=cwd)


def recent_log(count: int, cwd: Path | None = None) -> str:
    """Return the last `count` commit subjects (`git log --oneline`)."""
    return run_git("log", "--oneline", f"-{count}", cwd=cwd)


def gather_context(config: Config, cwd: Path | None = None) -> str:
    """Compose the configured repo-context sections into one text block."""
    logger.info("Gathering project context for the AI backend")
    sections = []
    if config.context_include_file_listing:
        logger.debug("Including tracked-file listing in context")
        sections.append(f"# Tracked files\n{list_files(cwd=cwd)}")
    if config.context_include_readme:
        readme = find_readme(cwd=cwd)
        if readme:
            logger.debug("Including README in context")
            sections.append(f"# README\n{readme}")
    if config.context_log_line_count > 0:
        logger.debug("Including %d recent commit(s) in context", config.context_log_line_count)
        sections.append(f"# Recent commits\n{recent_log(config.context_log_line_count, cwd=cwd)}")
    return "\n\n".join(sections)


def build_prompt(scan_report: str, context: str) -> str:
    """Build the AI prompt combining instructions, repo context, and the scan report."""
    schema = json.dumps(DraftDocument.model_json_schema())
    return (
        "You are drafting a structured commit-message document.\n"
        "Respond with ONLY a single JSON object matching this JSON Schema, "
        "and nothing else:\n"
        f"{schema}\n\n"
        f"Project context:\n{context}\n\n"
        f"Staged changes:\n{scan_report}\n"
    )


def extract_json_object(text: str) -> str:
    """Extract the outermost JSON object from text that may include commentary."""
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("No JSON object found in AI backend response")
    return text[start : end + 1]


def parse_draft_response(raw: str) -> DraftDocument:
    """Parse and validate an AI backend's raw response into a DraftDocument."""
    logger.info("Validating AI backend response into a draft document")
    doc = DraftDocument.model_validate(json.loads(extract_json_object(raw)))
    logger.debug("Draft document type=%s scope=%r", doc.type, doc.scope)
    return doc


def run_draft(
    scan_report: str,
    runner: Callable[[str], str],
    config: Config,
    cwd: Path | None = None,
) -> DraftDocument:
    """Build the prompt, call the backend runner, and return the parsed DraftDocument."""
    context = gather_context(config, cwd=cwd)
    prompt = build_prompt(scan_report, context)
    logger.info("Requesting draft document from AI backend")
    return parse_draft_response(runner(prompt))

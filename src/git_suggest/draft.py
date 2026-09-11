"""Turn a scan report into a validated DraftDocument via an AI backend.

Small functions compose: gather repo context, build a prompt, call a
backend runner (a curried function supplied by the caller), then parse and
validate the response. A bounded description-only retry (ADR 0015) fixes
up an over-length subject once the AI's actual type/scope/description are
known.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from pathlib import Path

from git_suggest.config import Config
from git_suggest.model import DraftDocument
from git_suggest.render import format_header
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


_BUDGET_LINE_PATTERN = re.compile(r"^#\s*subject-budget:\s*max=(\d+)\s*preferred=(\d+)")


def parse_subject_budget(scan_report: str, config: Config) -> tuple[int, int]:
    """Parse the leading subject-budget line embedded by scan (ADR 0014).

    Falls back to config's subject_max_length/subject_preferred_length when
    the scan report has no such line (e.g. hand-crafted input, or an older
    scan report format).
    """
    first_line = scan_report.splitlines()[0] if scan_report else ""
    match = _BUDGET_LINE_PATTERN.match(first_line)
    if match:
        return int(match.group(1)), int(match.group(2))
    return config.subject_max_length, config.subject_preferred_length


def build_prompt(scan_report: str, context: str, max_len: int = 72, preferred_len: int = 50) -> str:
    """Build the AI prompt combining instructions, repo context, and the scan report."""
    schema = json.dumps(DraftDocument.model_json_schema())
    return (
        "You are drafting a structured commit-message document.\n"
        "Respond with ONLY a single JSON object matching this JSON Schema, "
        "and nothing else:\n"
        f"{schema}\n\n"
        "The rendered subject line combines `type`, `scope`, and "
        "`description` as `type(scope): description`. Keep that combined "
        f"text at or under {max_len} characters (hard limit), and ideally "
        f"at or under {preferred_len} characters if you can.\n\n"
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


def build_length_retry_prompt(doc: DraftDocument, max_len: int, preferred_len: int) -> str:
    """Build a follow-up prompt asking for just a shorter `description` (ADR 0015)."""
    header = format_header(doc)
    return (
        f"Your previous response produced this subject line:\n{header}\n"
        f"That is {len(header)} characters, which exceeds the {max_len}-character "
        "hard limit for the `type(scope): description` portion of the subject "
        f"(ideally at or under {preferred_len} characters).\n"
        "Respond with ONLY a single JSON object matching this shape, and "
        'nothing else: {"description": "<a shorter description>"}\n'
        f"Keep type={doc.type.value!r} and scope={doc.scope!r} unchanged."
    )


def parse_length_retry_response(raw: str) -> str:
    """Parse a description-only retry response into its `description` string."""
    payload = json.loads(extract_json_object(raw))
    return payload["description"]


def enforce_subject_length(
    doc: DraftDocument,
    runner: Callable[[str], str],
    max_len: int,
    preferred_len: int,
    attempts: int,
) -> DraftDocument:
    """Retry with a description-only follow-up until the subject fits, or give up.

    Tries up to `attempts` times; if every attempt is still over budget,
    falls back to the shortest attempt and logs a warning (ADR 0015).
    """
    if len(format_header(doc)) <= max_len:
        return doc
    candidates = [doc]
    current = doc
    for _ in range(attempts):
        prompt = build_length_retry_prompt(current, max_len, preferred_len)
        logger.info("Subject line over budget; requesting a shorter description")
        new_description = parse_length_retry_response(runner(prompt))
        current = current.model_copy(update={"description": new_description})
        candidates.append(current)
        if len(format_header(current)) <= max_len:
            return current
    shortest = min(candidates, key=lambda candidate: len(format_header(candidate)))
    logger.warning(
        "Subject line still %d chars after %d retries (limit %d chars); using the shortest attempt",
        len(format_header(shortest)),
        attempts,
        max_len,
    )
    return shortest


def run_draft(
    scan_report: str,
    runner: Callable[[str], str],
    config: Config,
    cwd: Path | None = None,
) -> DraftDocument:
    """Build the prompt, call the backend runner, and return the parsed DraftDocument.

    Once a response is parsed, an over-length subject is retried (ADR 0015)
    against the budget parsed from the scan report (ADR 0014).
    """
    context = gather_context(config, cwd=cwd)
    max_len, preferred_len = parse_subject_budget(scan_report, config)
    prompt = build_prompt(scan_report, context, max_len, preferred_len)
    logger.info("Requesting draft document from AI backend")
    doc = parse_draft_response(runner(prompt))
    return enforce_subject_length(
        doc, runner, max_len, preferred_len, config.subject_retry_attempts
    )

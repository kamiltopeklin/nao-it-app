"""Cover letter body helpers: candidate name and sign-off hygiene."""

from __future__ import annotations

import re

# Trailing closing + optional name line the model often invents.
_SIGNOFF_TAIL_RE = re.compile(
    r"(?is)\n*\s*"
    r"(?:best regards|kind regards|warm regards|regards|sincerely|yours sincerely|"
    r"yours truly|thanks|thank you|with regards)\s*,?"
    r"(?:\s*\n+[^\n]*)?"
    r"\s*$"
)


def candidate_name_from_profile_text(profile_text: str) -> str:
    """Return the H1 name from OpenAI profile text (``# Full Name``), or empty."""
    for line in (profile_text or "").splitlines():
        s = line.strip()
        if s.startswith("##"):
            continue
        if s.startswith("#"):
            return s.lstrip("#").strip()
    return ""


def fix_cover_letter_signoff(body: str, candidate_name: str) -> str:
    """Force the letter to end with ``Best regards,\\n{candidate_name}``.

    Replaces whatever closing/name the model wrote (Jane Doe, Candidate, etc.).
    If *candidate_name* is empty, returns *body* unchanged.
    """
    name = (candidate_name or "").strip()
    text = (body or "").strip()
    if not name or not text:
        return body if body is not None else ""

    core = _SIGNOFF_TAIL_RE.sub("", text).rstrip()
    if not core:
        return f"Best regards,\n{name}"
    return f"{core}\n\nBest regards,\n{name}"

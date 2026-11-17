"""Canonical on-disk layout for per-user job documents + migration helpers.

Layout::

    {RESUME_OUTPUT_ROOT}/{user_id}/{Company}/{job_id}/{kind}/{filename}

``kind`` is ``resume`` or ``cover_letter``. Migration moves only files that a
``resume_build_results`` row already points at, so ownership always comes from
the DB (never from guessing who owns an orphan on disk).
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from app.services.resume_builder_service import (
    DOCUMENT_KINDS,
    artifact_path_in_new_layout,
    build_kind_directory,
    build_output_directory,
    resolve_resume_artifact_path,
    resume_output_root,
    safe_path_segment,
)

# DB column → document kind folder
PATH_COLUMNS: tuple[tuple[str, str], ...] = (
    ("resume_docx_path", "resume"),
    ("resume_pdf_path", "resume"),
    ("cover_letter_docx_path", "cover_letter"),
    ("cover_letter_pdf_path", "cover_letter"),
)


@dataclass(frozen=True)
class ArtifactMove:
    """One file that should move from an old path into the new layout."""

    build_id: str
    user_id: str
    job_id: str
    company: str
    column: str
    kind: str
    source: Path
    destination: Path
    shared_source: bool = False  # True when another row also points at source


def plan_artifact_move(
    *,
    build_id: str,
    user_id: str,
    job_id: str,
    company: str,
    column: str,
    kind: str,
    stored_path: str | None,
) -> ArtifactMove | None:
    """Return a move plan when the stored path exists and is not already correct.

    Returns None when there is nothing to do (empty path, missing file, or
    already under the new layout for this user/job/kind).
    """
    raw = (stored_path or "").strip()
    if not raw:
        return None
    source = resolve_resume_artifact_path(raw)
    if source is None or not source.is_file():
        return None
    if artifact_path_in_new_layout(source, user_id=user_id, job_id=job_id, kind=kind):
        return None

    kind_dir = build_kind_directory(
        company, job_id, user_id=user_id, kind=kind, create=False,
    )
    destination = (kind_dir / source.name).resolve()
    if destination == source.resolve():
        return None
    return ArtifactMove(
        build_id=build_id,
        user_id=user_id,
        job_id=job_id,
        company=company,
        column=column,
        kind=kind,
        source=source.resolve(),
        destination=destination,
    )


def mark_shared_sources(moves: list[ArtifactMove]) -> list[ArtifactMove]:
    """Flag sources referenced by more than one planned move (must copy, not rename)."""
    counts: dict[str, int] = {}
    for m in moves:
        key = str(m.source)
        counts[key] = counts.get(key, 0) + 1
    out: list[ArtifactMove] = []
    for m in moves:
        shared = counts.get(str(m.source), 0) > 1
        if shared == m.shared_source:
            out.append(m)
        else:
            out.append(
                ArtifactMove(
                    build_id=m.build_id,
                    user_id=m.user_id,
                    job_id=m.job_id,
                    company=m.company,
                    column=m.column,
                    kind=m.kind,
                    source=m.source,
                    destination=m.destination,
                    shared_source=shared,
                )
            )
    return out


def apply_artifact_move(move: ArtifactMove, *, apply: bool) -> str:
    """Copy or rename *move* onto disk. Returns action label.

    When ``apply`` is False, only validates and returns ``would_*``.
    Destination collisions: if dst exists with different bytes, refuse.
    """
    src = move.source
    dst = move.destination
    if not src.is_file():
        return "missing_source"
    if dst.exists():
        if dst.is_file() and dst.stat().st_size == src.stat().st_size and dst.read_bytes() == src.read_bytes():
            if not apply:
                return "would_reuse_identical_destination"
            return "reuse_identical_destination"
        return "destination_conflict"
    if not apply:
        return "would_copy" if move.shared_source else "would_move"

    dst.parent.mkdir(parents=True, exist_ok=True)
    if move.shared_source:
        shutil.copy2(src, dst)
        return "copied"
    shutil.move(str(src), str(dst))
    return "moved"


def job_root_for_row(*, user_id: str, company: str, job_id: str) -> Path:
    return build_output_directory(company, job_id, user_id=user_id)


def company_from_job_or_path(company: str | None, stored_path: str | None) -> str:
    """Prefer the Job.company value; fall back to a segment from an old path."""
    if company and str(company).strip():
        return str(company).strip()
    if stored_path:
        try:
            p = resolve_resume_artifact_path(stored_path) or Path(stored_path)
            root = resume_output_root().resolve()
            rel = p.resolve().relative_to(root)
            # Old: {Company}/{job_id}/file
            # Partial new: {Company}/{job_id}/{user_id}/file
            # New: {user_id}/{Company}/{job_id}/{kind}/file
            if len(rel.parts) >= 2:
                # If first part looks like a user uuid and second is company, use second.
                first = rel.parts[0]
                if len(first) >= 32 and "-" in first and len(rel.parts) >= 2:
                    return rel.parts[1]
                return rel.parts[0]
        except (ValueError, OSError):
            pass
    return "Unknown"


def collect_referenced_paths(rows: Iterable[object]) -> set[str]:
    """Absolute path strings still referenced by any path column on *rows*."""
    out: set[str] = set()
    for row in rows:
        for col, _kind in PATH_COLUMNS:
            raw = getattr(row, col, None)
            if not isinstance(raw, str) or not raw.strip():
                continue
            resolved = resolve_resume_artifact_path(raw)
            if resolved is not None and resolved.is_file():
                out.add(str(resolved.resolve()))
    return out


def safe_unlink_unreferenced(paths: Iterable[Path], referenced: set[str]) -> int:
    """Delete files that are no longer referenced by any build row."""
    deleted = 0
    for p in paths:
        try:
            key = str(p.resolve())
            if key in referenced:
                continue
            if p.is_file():
                p.unlink(missing_ok=True)
                deleted += 1
        except OSError:
            continue
    return deleted


def normalize_user_job_segments(user_id: str, job_id: str) -> tuple[str, str]:
    return (
        safe_path_segment(str(user_id or "").strip(), fallback="user", max_len=36),
        safe_path_segment(str(job_id or "").strip(), fallback="job", max_len=36),
    )


assert set(DOCUMENT_KINDS) == {"resume", "cover_letter"}

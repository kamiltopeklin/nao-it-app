"""Move job documents into ``resume_output/{user_id}/{Company}/{job_id}/{kind}/``.

Ownership is taken only from ``resume_build_results`` path columns (never by
guessing who owns an orphan file on disk). Defaults to a dry run.

Usage:
    python -m scripts.migrate_resume_output_layout
    python -m scripts.migrate_resume_output_layout --apply
    python -m scripts.migrate_resume_output_layout --apply --cleanup-old
"""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from pathlib import Path

from sqlalchemy import select

from app.core.logging import get_logger
from app.models.database import Job, ResumeBuildResult
from app.services.resume_output_layout import (
    PATH_COLUMNS,
    apply_artifact_move,
    collect_referenced_paths,
    company_from_job_or_path,
    job_root_for_row,
    mark_shared_sources,
    plan_artifact_move,
    safe_unlink_unreferenced,
)
from app.storage.database import close_database, get_session, init_database

logger = get_logger(__name__)


async def _run(*, apply: bool, cleanup_old: bool, limit: int | None) -> None:
    await init_database()
    stats: Counter[str] = Counter()
    planned_sources: list[Path] = []

    try:
        async with get_session() as session:
            result = await session.execute(
                select(ResumeBuildResult, Job)
                .join(Job, Job.id == ResumeBuildResult.job_id, isouter=True)
                .order_by(ResumeBuildResult.updated_at.desc())
            )
            pairs = list(result.all())
        if limit is not None:
            pairs = pairs[: max(0, limit)]

        moves = []
        for row, job in pairs:
            company = company_from_job_or_path(
                getattr(job, "company", None) if job else None,
                row.resume_pdf_path
                or row.resume_docx_path
                or row.cover_letter_pdf_path
                or row.cover_letter_docx_path
                or row.output_directory,
            )
            for column, kind in PATH_COLUMNS:
                stored = getattr(row, column, None)
                move = plan_artifact_move(
                    build_id=row.id,
                    user_id=row.user_id,
                    job_id=row.job_id,
                    company=company,
                    column=column,
                    kind=kind,
                    stored_path=stored if isinstance(stored, str) else None,
                )
                if move is None:
                    if isinstance(stored, str) and stored.strip():
                        stats["already_ok_or_missing"] += 1
                    else:
                        stats["empty_path"] += 1
                    continue
                moves.append(move)

        moves = mark_shared_sources(moves)
        stats["planned"] = len(moves)
        print(f"Planned moves: {len(moves)} (apply={apply})")

        by_build: dict[str, list] = {}
        for m in moves:
            by_build.setdefault(m.build_id, []).append(m)

        async with get_session() as session:
            for build_id, build_moves in by_build.items():
                row = await session.get(ResumeBuildResult, build_id)
                if row is None:
                    stats["row_missing"] += 1
                    continue
                job = (
                    await session.execute(select(Job).where(Job.id == row.job_id))
                ).scalar_one_or_none()
                # Prefer Job.company; fall back to the company already planned
                # from the first pass (never re-parse a company string as a path).
                company = (
                    (getattr(job, "company", None) if job else None)
                    or build_moves[0].company
                    or "Unknown"
                )
                updated_any = False
                for m in build_moves:
                    action = apply_artifact_move(m, apply=apply)
                    stats[action] += 1
                    print(
                        f"  [{action}] user={m.user_id[:8]}… job={m.job_id[:8]}… "
                        f"{m.column}: {m.source.name} -> …/{m.kind}/{m.destination.name}"
                    )
                    if action in {
                        "moved",
                        "copied",
                        "reuse_identical_destination",
                        "would_move",
                        "would_copy",
                        "would_reuse_identical_destination",
                    }:
                        planned_sources.append(m.source)
                    if apply and action in {
                        "moved",
                        "copied",
                        "reuse_identical_destination",
                    }:
                        setattr(row, m.column, str(m.destination))
                        updated_any = True
                if apply and updated_any:
                    row.output_directory = str(
                        job_root_for_row(
                            user_id=row.user_id,
                            company=company,
                            job_id=row.job_id,
                        )
                    )

            # Also rewrite stale output_directory values that still point at the
            # shared old {Company}/{job_id} root (even when file columns were
            # already empty/missing so no ArtifactMove ran).
            if apply:
                from pathlib import Path

                from app.services.resume_builder_service import (
                    resume_output_root,
                    safe_path_segment,
                )

                all_pairs = (
                    await session.execute(
                        select(ResumeBuildResult, Job).join(
                            Job, Job.id == ResumeBuildResult.job_id, isouter=True,
                        )
                    )
                ).all()
                root = resume_output_root().resolve()
                for row, job in all_pairs:
                    raw_dir = (row.output_directory or "").strip()
                    if not raw_dir:
                        continue
                    d = Path(raw_dir)
                    d = d if d.is_absolute() else (root / d)
                    try:
                        rel = d.resolve().relative_to(root)
                    except (ValueError, OSError):
                        continue
                    uid = safe_path_segment(row.user_id, fallback="user", max_len=36)
                    jid = safe_path_segment(row.job_id, fallback="job", max_len=36)
                    if len(rel.parts) >= 3 and rel.parts[0] == uid and rel.parts[2] == jid:
                        continue
                    company = company_from_job_or_path(
                        getattr(job, "company", None) if job else None,
                        row.resume_pdf_path
                        or row.resume_docx_path
                        or row.cover_letter_pdf_path
                        or row.cover_letter_docx_path
                        or raw_dir,
                    )
                    new_dir = str(
                        job_root_for_row(
                            user_id=row.user_id, company=company, job_id=row.job_id,
                        )
                    )
                    row.output_directory = new_dir
                    stats["output_directory_rewritten"] += 1
                    print(
                        f"  [output_dir] user={row.user_id[:8]}… job={row.job_id[:8]}… "
                        f"-> …/{uid}/{safe_path_segment(company, fallback='Unknown', max_len=80)}/{jid}"
                    )

            if apply:
                await session.commit()

        if apply and cleanup_old and planned_sources:
            async with get_session() as session:
                rows = (await session.execute(select(ResumeBuildResult))).scalars().all()
                referenced = collect_referenced_paths(rows)
            deleted = safe_unlink_unreferenced(planned_sources, referenced)
            stats["old_sources_deleted"] = deleted
            print(f"Cleanup: deleted {deleted} unreferenced old source files")

        print("Stats:", dict(stats))
        logger.info("resume_output_layout_migrate_done", apply=apply, **dict(stats))
    finally:
        await close_database()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write files and update DB paths (default is dry run)",
    )
    parser.add_argument(
        "--cleanup-old",
        action="store_true",
        help="After --apply, delete old source files no longer referenced by any row",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only process the N most recently updated build rows (debug)",
    )
    args = parser.parse_args()
    if args.cleanup_old and not args.apply:
        parser.error("--cleanup-old requires --apply")
    asyncio.run(_run(apply=args.apply, cleanup_old=args.cleanup_old, limit=args.limit))


if __name__ == "__main__":
    main()

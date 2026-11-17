"""Orchestrates resume & cover letter PDF generation from stored tailored data.

Called by the resume build worker after the analysis pipeline has stored
tailored_resume_data and cover_letter_data on a ResumeBuildResult row.

Every résumé and cover letter PDF is printed by the shared Chromium document
renderer from the same templates the Resume studio shows. Job builds no longer
write DOCX/DOC artifacts under ``resume_output``; those file types are marked
``skipped``.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.api.websocket import publish_resume_event
from app.core.logging import bind_logging_context, get_logger
from app.models.database import Job
from app.services.document_content import tailored_design
from app.services.document_renderer import (
    profile_payload,
    render_cover_letter_pdf,
    render_resume_pdf,
)
from app.services.job_pipeline_mode import has_tailored_resume
from app.services.resume_builder_service import (
    build_kind_directory,
    build_output_directory,
    person_document_stem,
)
from app.services.resume_design_service import load_design_for_render
from app.storage.database import get_session
from app.storage.repository import ResumeBuildRepository
from app.storage.user_repository import UserRepository
from app.utils.flexible_date import design_date_style

logger = get_logger(__name__)

COVER_LETTER_CONTENT_MISSING_MSG = (
    "No cover letter content was generated. Re-run job analysis or check Phase B output."
)


async def _fail_file(
    repo: ResumeBuildRepository,
    build_id: str,
    *,
    user_id: str,
    job_id: str,
    file_type: str,
    error: str,
) -> None:
    await repo.update_file_status(build_id, file_type, "failed", error=error)
    await publish_resume_event({
        "type": "resume_file_failed",
        "user_id": user_id,
        "job_id": job_id,
        "file_type": file_type,
        "error": error,
    })


async def _mark_processing(
    repo: ResumeBuildRepository,
    build_id: str,
    *,
    user_id: str,
    job_id: str,
    file_type: str,
) -> None:
    await repo.update_file_status(build_id, file_type, "processing")
    await publish_resume_event({
        "type": "resume_file_processing",
        "user_id": user_id,
        "job_id": job_id,
        "file_type": file_type,
    })


async def _mark_completed(
    repo: ResumeBuildRepository,
    build_id: str,
    *,
    user_id: str,
    job_id: str,
    file_type: str,
    path: str,
) -> None:
    await repo.update_file_status(build_id, file_type, "completed", path=path)
    await publish_resume_event({
        "type": "resume_file_ready",
        "user_id": user_id,
        "job_id": job_id,
        "file_type": file_type,
    })


async def _mark_failed(
    repo: ResumeBuildRepository,
    build_id: str,
    *,
    user_id: str,
    job_id: str,
    file_type: str,
    error: str,
    log_event: str,
) -> None:
    logger.error(log_event, error=error)
    await repo.update_file_status(build_id, file_type, "failed", error=error)
    await publish_resume_event({
        "type": "resume_file_failed",
        "user_id": user_id,
        "job_id": job_id,
        "file_type": file_type,
        "error": error,
    })


async def run_resume_build(job_id: str, user_id: str) -> dict | None:
    """Build resume and cover letter PDFs only, reporting per-file progress
    on the resume WebSocket channel. Documents are rendered from the user's saved
    Resume Builder design (default theme if none saved)."""
    bind_logging_context(job_id=job_id, user_id=user_id)

    try:
        async with get_session() as session:
            repo = ResumeBuildRepository(session)
            user_repo = UserRepository(session)

            build = await repo.get(job_id, user_id)
            if not build:
                logger.warning("resume_build_no_row", job_id=job_id)
                return None

            tailored = build.tailored_resume_data if has_tailored_resume(build.tailored_resume_data) else None
            cover_data = build.cover_letter_data
            has_cover_body = bool(isinstance(cover_data, dict) and cover_data.get("body"))
            if not tailored and not has_cover_body:
                logger.warning("resume_build_no_tailored_data", job_id=job_id)
                return None
            # Original résumé mode: the user's own file is used as is, so only the cover letter is built.
            cover_only = not tailored

            user = await user_repo.get_by_id(user_id)
            if not user:
                logger.warning("resume_build_no_user", user_id=user_id)
                return None

            # Single source of truth: active library resume (Studio), then mirror, then default.
            design, has_design = await load_design_for_render(session, user)
            logger.info(
                "resume_build_design_resolved",
                job_id=job_id,
                user_id=user_id,
                has_design=has_design,
                theme_id=getattr(design, "theme_id", None),
                active_resume_id=getattr(user, "active_resume_id", None),
                accent=getattr(getattr(design, "colors", None), "accent", None),
            )

            first = (user.name_first or "").strip()
            last = (user.name_last or "").strip()
            resume_stem = person_document_stem(first, last, "resume")
            cover_stem = person_document_stem(first, last, "cover_letter")

            r = await session.execute(select(Job).where(Job.id == job_id))
            job = r.scalar_one_or_none()
            company = (job.company if job else None) or "Unknown"

            # Disk layout:
            # resume_output/{user_id}/{Company}/{job_id}/resume|cover_letter/{stem}.pdf
            job_out_dir = build_output_directory(company, job_id, user_id=user_id)
            resume_dir = build_kind_directory(
                company, job_id, user_id=user_id, kind="resume",
            )
            cover_dir = build_kind_directory(
                company, job_id, user_id=user_id, kind="cover_letter",
            )
            await repo.set_output_directory(build.id, str(job_out_dir))

            resume_pdf_name = f"{resume_stem}.pdf"
            cl_pdf_name = f"{cover_stem}.pdf"

            results: dict[str, str | None] = {}
            profile = profile_payload(user)
            with design_date_style(design):
                job_design = None if cover_only else tailored_design(design, profile, tailored)
            display_name = " ".join(p for p in (first, last) if p) or "Resume"
            build_id = build.id

            # Job builds are PDF-only: never write DOCX under resume_output.
            await repo.update_file_status(build_id, "resume_docx", "skipped")
            await repo.update_file_status(build_id, "cover_letter_docx", "skipped")

            if cover_only:
                await repo.update_file_status(build_id, "resume_pdf", "skipped")
            else:
                await _mark_processing(
                    repo, build_id, user_id=user_id, job_id=job_id, file_type="resume_pdf",
                )

            if has_cover_body:
                await _mark_processing(
                    repo, build_id, user_id=user_id, job_id=job_id, file_type="cover_letter_pdf",
                )
            else:
                logger.warning("cover_letter_build_no_content", user_id=user_id, job_id=job_id)
                await _fail_file(
                    repo,
                    build_id,
                    user_id=user_id,
                    job_id=job_id,
                    file_type="cover_letter_pdf",
                    error=COVER_LETTER_CONTENT_MISSING_MSG,
                )

            cover_body = cover_data["body"] if has_cover_body else ""

            pdf_jobs: list[tuple[str, Path]] = []
            if not cover_only:
                pdf_jobs.append(("resume_pdf", resume_dir / resume_pdf_name))
            if has_cover_body:
                pdf_jobs.append(("cover_letter_pdf", cover_dir / cl_pdf_name))

            async def _pdf_task(
                file_type: str, pdf_path: Path,
            ) -> tuple[str, Path | None, str | None]:
                try:
                    if file_type == "resume_pdf":
                        rendered = await render_resume_pdf(
                            job_design, profile, title=f"{display_name} - Resume",
                        )
                    else:
                        rendered = await render_cover_letter_pdf(
                            design, profile, cover_body, title=f"{display_name} - Cover Letter",
                        )
                    pdf_path.parent.mkdir(parents=True, exist_ok=True)
                    pdf_path.write_bytes(rendered.pdf)
                    return (file_type, pdf_path, None)
                except Exception as e:
                    return (file_type, None, str(e))

            if pdf_jobs:
                for file_type, path, err in await asyncio.gather(
                    *[_pdf_task(ft, dst) for ft, dst in pdf_jobs]
                ):
                    if path is not None:
                        results[file_type] = str(path)
                        await _mark_completed(
                            repo,
                            build_id,
                            user_id=user_id,
                            job_id=job_id,
                            file_type=file_type,
                            path=str(path),
                        )
                    else:
                        log_event = (
                            "resume_pdf_conversion_failed"
                            if file_type == "resume_pdf"
                            else "cover_letter_pdf_conversion_failed"
                        )
                        await _mark_failed(
                            repo,
                            build_id,
                            user_id=user_id,
                            job_id=job_id,
                            file_type=file_type,
                            error=err or "unknown error",
                            log_event=log_event,
                        )

            await session.commit()
            logger.info("resume_build_completed", job_id=job_id, files=list(results.keys()))
            return results if results else None

    except Exception as e:
        logger.exception("resume_build_failed", job_id=job_id, error=str(e))
        await publish_resume_event({
            "type": "resume_build_failed",
            "user_id": user_id,
            "job_id": job_id,
            "error": str(e),
        })
        return None

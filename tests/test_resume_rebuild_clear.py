"""Rebuild docs must detach DB attachments and remove disk artifacts before regen."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.resume_builder_service import delete_resume_artifacts
from app.storage.repository import ResumeBuildRepository


def test_delete_resume_artifacts_removes_files_and_job_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "resume_output"
    job_dir = root / "Acme" / "job-1"
    job_dir.mkdir(parents=True)
    resume = job_dir / "Ada_resume.pdf"
    cover = job_dir / "Ada_cover_letter.pdf"
    resume.write_bytes(b"%PDF-old")
    cover.write_bytes(b"%PDF-old")

    monkeypatch.setattr(
        "app.services.resume_builder_service.resume_output_root",
        lambda: root,
    )

    removed = delete_resume_artifacts([str(resume), str(cover), str(job_dir)])
    assert removed >= 2
    assert not resume.exists()
    assert not cover.exists()
    assert not job_dir.exists()


def test_clear_attached_documents_nulls_paths_and_content() -> None:
    import asyncio

    row = SimpleNamespace(
        tailored_resume_data={"profile_summary": "old"},
        cover_letter_data={"body": "old letter"},
        content_generation_status="completed",
        content_generation_error=None,
        resume_docx_status="completed",
        resume_pdf_status="completed",
        cover_letter_docx_status="completed",
        cover_letter_pdf_status="completed",
        resume_docx_path="/tmp/r.docx",
        resume_pdf_path="/tmp/r.pdf",
        cover_letter_docx_path="/tmp/c.docx",
        cover_letter_pdf_path="/tmp/c.pdf",
        output_directory="/tmp/out",
        error_message=None,
        updated_at=None,
    )
    session = MagicMock()
    session.flush = AsyncMock()
    repo = ResumeBuildRepository(session)
    repo.get = AsyncMock(return_value=row)

    cleared, paths = asyncio.run(repo.clear_attached_documents("job-1", "user-1"))

    assert cleared is row
    assert row.tailored_resume_data is None
    assert row.cover_letter_data is None
    assert row.content_generation_status == "pending"
    assert row.resume_pdf_path is None
    assert row.resume_docx_path is None
    assert row.cover_letter_pdf_path is None
    assert row.output_directory is None
    assert set(paths) == {
        "/tmp/r.docx",
        "/tmp/r.pdf",
        "/tmp/c.docx",
        "/tmp/c.pdf",
        "/tmp/out",
    }

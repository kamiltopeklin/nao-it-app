"""Per-user resume_output layout + migration planning."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.resume_builder_service import (
    artifact_path_in_new_layout,
    build_kind_directory,
    build_output_directory,
)
from app.services.resume_output_layout import (
    apply_artifact_move,
    mark_shared_sources,
    plan_artifact_move,
)


@pytest.fixture()
def output_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "resume_output"
    root.mkdir()
    monkeypatch.setattr(
        "app.services.resume_builder_service.resume_output_root",
        lambda: root,
    )
    monkeypatch.setattr(
        "app.services.resume_output_layout.resume_output_root",
        lambda: root,
    )
    return root


def test_build_paths_include_user_and_kind(output_root: Path) -> None:
    job = build_output_directory("Acme Corp", "job-1", user_id="user-aaaa", create=True)
    resume = build_kind_directory(
        "Acme Corp", "job-1", user_id="user-aaaa", kind="resume", create=True,
    )
    cover = build_kind_directory(
        "Acme Corp", "job-1", user_id="user-aaaa", kind="cover_letter", create=True,
    )
    assert job == output_root / "user-aaaa" / "Acme_Corp" / "job-1"
    assert resume == job / "resume"
    assert cover == job / "cover_letter"
    assert resume.is_dir() and cover.is_dir()


def test_plan_moves_old_layout_to_user_kind(output_root: Path) -> None:
    old_dir = output_root / "Acme" / "job-1"
    old_dir.mkdir(parents=True)
    src = old_dir / "Ada_resume.pdf"
    src.write_bytes(b"%PDF-old")

    move = plan_artifact_move(
        build_id="b1",
        user_id="user-1",
        job_id="job-1",
        company="Acme",
        column="resume_pdf_path",
        kind="resume",
        stored_path=str(src),
    )
    assert move is not None
    assert move.source == src.resolve()
    assert move.destination == (
        output_root / "user-1" / "Acme" / "job-1" / "resume" / "Ada_resume.pdf"
    ).resolve()
    assert move.kind == "resume"


def test_plan_skips_when_already_in_new_layout(output_root: Path) -> None:
    dest_dir = build_kind_directory(
        "Acme", "job-1", user_id="user-1", kind="resume", create=True,
    )
    src = dest_dir / "Ada_resume.pdf"
    src.write_bytes(b"%PDF")
    assert artifact_path_in_new_layout(src, user_id="user-1", job_id="job-1", kind="resume")
    assert (
        plan_artifact_move(
            build_id="b1",
            user_id="user-1",
            job_id="job-1",
            company="Acme",
            column="resume_pdf_path",
            kind="resume",
            stored_path=str(src),
        )
        is None
    )


def test_shared_source_is_copied_not_moved(output_root: Path) -> None:
    old = output_root / "Acme" / "job-1"
    old.mkdir(parents=True)
    src = old / "shared.pdf"
    src.write_bytes(b"%PDF-shared")

    m1 = plan_artifact_move(
        build_id="b1",
        user_id="user-a",
        job_id="job-1",
        company="Acme",
        column="resume_pdf_path",
        kind="resume",
        stored_path=str(src),
    )
    m2 = plan_artifact_move(
        build_id="b2",
        user_id="user-b",
        job_id="job-1",
        company="Acme",
        column="resume_pdf_path",
        kind="resume",
        stored_path=str(src),
    )
    assert m1 and m2
    marked = mark_shared_sources([m1, m2])
    assert all(m.shared_source for m in marked)

    assert apply_artifact_move(marked[0], apply=True) == "copied"
    assert src.is_file()  # still there for the other user
    assert marked[0].destination.is_file()
    assert apply_artifact_move(marked[1], apply=True) == "copied"
    assert marked[1].destination.is_file()


def test_apply_move_refuses_conflicting_destination(output_root: Path) -> None:
    old = output_root / "Acme" / "job-1"
    old.mkdir(parents=True)
    src = old / "Ada_resume.pdf"
    src.write_bytes(b"%PDF-a")
    move = plan_artifact_move(
        build_id="b1",
        user_id="user-1",
        job_id="job-1",
        company="Acme",
        column="resume_pdf_path",
        kind="resume",
        stored_path=str(src),
    )
    assert move
    move.destination.parent.mkdir(parents=True, exist_ok=True)
    move.destination.write_bytes(b"%PDF-OTHER")
    assert apply_artifact_move(move, apply=True) == "destination_conflict"
    assert src.is_file()

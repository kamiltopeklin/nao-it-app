"""Active library design must win over a stale users.resume_template_design mirror."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.resume_design_schemas import ResumeDesign
from app.services.resume_design_service import load_design_for_render


def test_load_design_for_render_prefers_active_library_over_mirror() -> None:
    library_design = ResumeDesign.model_validate(
        {"theme_id": "modern", "colors": {"accent": "#112233"}}
    )
    mirror_design = ResumeDesign.model_validate(
        {"theme_id": "classic", "colors": {"accent": "#abcdef"}}
    )
    user = SimpleNamespace(
        id="u1",
        active_resume_id="r-active",
        resume_template_design=mirror_design.model_dump(mode="json"),
    )
    doc = SimpleNamespace(id="r-active", design=library_design.model_dump(mode="json"))

    session = MagicMock()
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=doc)
    repo.list_for_user = AsyncMock(return_value=[doc])

    with patch(
        "app.storage.resume_document_repository.ResumeDocumentRepository",
        return_value=repo,
    ):
        design, has_design = asyncio.run(load_design_for_render(session, user))

    assert has_design is True
    assert design.theme_id == "modern"
    assert design.colors.accent == "#112233"
    repo.get_by_id.assert_awaited_once_with("r-active", "u1")


def test_load_design_for_render_falls_back_to_mirror() -> None:
    mirror_design = ResumeDesign.model_validate(
        {"theme_id": "executive", "colors": {"accent": "#00aa00"}}
    )
    user = SimpleNamespace(
        id="u1",
        active_resume_id=None,
        resume_template_design=mirror_design.model_dump(mode="json"),
    )

    session = MagicMock()
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=None)
    repo.list_for_user = AsyncMock(return_value=[])

    with patch(
        "app.storage.resume_document_repository.ResumeDocumentRepository",
        return_value=repo,
    ):
        design, has_design = asyncio.run(load_design_for_render(session, user))

    assert has_design is True
    assert design.theme_id == "executive"
    assert design.colors.accent == "#00aa00"

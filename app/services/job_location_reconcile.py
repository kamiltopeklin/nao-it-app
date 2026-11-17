"""Restore jobs previously hidden by retired country-preference rules.

Country preference auto-hide is off. Opening Jobs still runs this so rows
hidden as outside_preferred_countries / legacy non_us_location come back.
Manual hides, dedup, and score exclusions are left alone.
"""

from __future__ import annotations

from sqlalchemy import and_, select

from app.api.websocket import publish_ws_event
from app.core.logging import get_logger
from app.models.database import Job, UserJobStatus
from app.services.job_exclusion_types import LOCATION_EXCLUSION_TYPES
from app.storage.database import get_session
from app.storage.repository import UserJobStatusRepository

logger = get_logger(__name__)


async def _restore_location_exclusions(user_id: str) -> int:
    """Bring back jobs auto-hidden by location rules now that the filter is off."""
    restored = 0
    async with get_session() as session:
        stmt = (
            select(Job.id)
            .join(UserJobStatus, and_(
                UserJobStatus.job_id == Job.id,
                UserJobStatus.user_id == user_id,
            ))
            .where(
                Job.status != "blocked",
                UserJobStatus.status == "duplicated",
                UserJobStatus.exclusion_type.in_(list(LOCATION_EXCLUSION_TYPES)),
            )
        )
        job_ids = list((await session.execute(stmt)).scalars().all())
        ujs_repo = UserJobStatusRepository(session)
        for job_id in job_ids:
            await ujs_repo.upsert(
                user_id=user_id,
                job_id=job_id,
                status="active",
                exclusion_type=None,
                reason=None,
            )
            restored += 1
            await publish_ws_event({
                "type": "scrape_promoted",
                "user_id": user_id,
                "valid_job_id": job_id,
            })
    if restored:
        logger.info("job_location_reconcile_restored", user_id=user_id, restored=restored)
    return restored


async def reconcile_job_locations_for_user(user_id: str, *, batch_size: int = 500) -> dict:
    """Restore location-hidden jobs. Never hides by country again."""
    del batch_size  # kept for callers that still pass it
    restored = await _restore_location_exclusions(user_id)
    if restored:
        logger.info(
            "job_location_reconcile_completed",
            user_id=user_id,
            scanned=0,
            moved_non_us=0,
            moved_unknown=0,
            restored=restored,
            preferred_countries=[],
        )
    return {
        "scanned": 0,
        "moved_non_us": 0,
        "moved_unknown": 0,
        "restored": restored,
        "preferred_countries": [],
    }

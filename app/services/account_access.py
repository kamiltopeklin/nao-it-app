"""Who may do work on the platform.

An account may sign in and receive background work when it is active.
Admins turn an account off from Users. Disabled accounts cannot sign in,
and fan-outs (auto-prepare, job source syncs, encodings) skip them so a
disabled account does not keep spending work.
"""

from __future__ import annotations

from app.models.database import User


def can_use_app_clause():
    """SQL filter for accounts allowed to do background work."""
    return User.is_active.is_(True)


def can_use_app(user: User | None) -> bool:
    return bool(user is not None and user.is_active)

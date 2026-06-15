"""SQLiteSession wrapper with per-user isolation and trace group support."""
from __future__ import annotations

import os
from agents import SQLiteSession

# Sessions DB lives next to the main aria.db
_SESSIONS_DB = os.path.join(os.path.dirname(__file__), "..", "aria_sessions.db")


def get_session(session_id: str) -> SQLiteSession:
    """Return a SQLiteSession scoped to the given session_id."""
    return SQLiteSession(
        session_id=session_id,
        db_path=os.path.abspath(_SESSIONS_DB),
    )

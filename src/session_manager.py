from datetime import datetime, timedelta
from typing import Dict, Optional

from src.config import settings
from src.logging_config import get_logger
from src.models import ConversationSession

logger = get_logger(__name__)


class SessionManager:
    """Manage user conversation sessions (in-memory for MVP)."""

    def __init__(self) -> None:
        self._sessions: Dict[str, ConversationSession] = {}
        self._timeout = timedelta(minutes=settings.session_timeout_minutes)

    def get_session(self, user_id: str) -> ConversationSession:
        """Get or create a session for a user."""
        self._cleanup_expired_sessions()

        if user_id not in self._sessions:
            logger.info("creating_new_session", user_id=user_id)
            self._sessions[user_id] = ConversationSession(user_id=user_id)
        else:
            session = self._sessions[user_id]
            if self._is_expired(session):
                logger.info("session_expired_creating_new", user_id=user_id)
                self._sessions[user_id] = ConversationSession(user_id=user_id)
            else:
                session.update()

        return self._sessions[user_id]

    def update_session_context(
        self,
        user_id: str,
        key: str,
        value: str,
    ) -> None:
        """Update session context."""
        session = self.get_session(user_id)
        session.context[key] = value
        session.update()
        logger.info(
            "session_context_updated",
            user_id=user_id,
            key=key,
        )

    def clear_session(self, user_id: str) -> None:
        """Clear a user's session."""
        if user_id in self._sessions:
            del self._sessions[user_id]
            logger.info("session_cleared", user_id=user_id)

    def _is_expired(self, session: ConversationSession) -> bool:
        """Check if a session has expired."""
        return datetime.utcnow() - session.updated_at > self._timeout

    def _cleanup_expired_sessions(self) -> None:
        """Remove expired sessions."""
        expired_users = [
            user_id
            for user_id, session in self._sessions.items()
            if self._is_expired(session)
        ]

        for user_id in expired_users:
            del self._sessions[user_id]
            logger.info("expired_session_removed", user_id=user_id)

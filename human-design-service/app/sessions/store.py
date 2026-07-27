from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from threading import RLock
from typing import Any


@dataclass
class DemoSession:
    session_id: str
    telegram_user_id: int
    birth_data: dict[str, Any]
    normalized_bodygraph: dict[str, Any]
    summary: dict[str, Any]
    image_png: bytes
    demo_mode: str
    answers: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0.0

    def is_expired(self) -> bool:
        return time.time() >= self.expires_at


class SessionStore:
    def __init__(self, ttl_seconds: int = 3600) -> None:
        self.ttl_seconds = ttl_seconds
        self._sessions: dict[str, DemoSession] = {}
        self._lock = RLock()

    def create(
        self,
        *,
        telegram_user_id: int,
        birth_data: dict[str, Any],
        normalized_bodygraph: dict[str, Any],
        summary: dict[str, Any],
        image_png: bytes,
        demo_mode: str,
    ) -> DemoSession:
        self.cleanup()
        session_id = str(uuid.uuid4())
        now = time.time()
        session = DemoSession(
            session_id=session_id,
            telegram_user_id=telegram_user_id,
            birth_data=birth_data,
            normalized_bodygraph=normalized_bodygraph,
            summary=summary,
            image_png=image_png,
            demo_mode=demo_mode,
            created_at=now,
            expires_at=now + self.ttl_seconds,
        )
        with self._lock:
            self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> DemoSession | None:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return None
            if session.is_expired():
                del self._sessions[session_id]
                return None
            return session

    def get_for_user(self, session_id: str, telegram_user_id: int) -> DemoSession | None:
        session = self.get(session_id)
        if not session:
            return None
        if session.telegram_user_id != telegram_user_id:
            return None
        return session

    def save_answer(self, session_id: str, key: str, answer: dict[str, Any]) -> None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session and not session.is_expired():
                session.answers[key] = answer

    def cleanup(self) -> None:
        with self._lock:
            expired = [sid for sid, s in self._sessions.items() if s.is_expired()]
            for sid in expired:
                del self._sessions[sid]

    def clear(self) -> None:
        with self._lock:
            self._sessions.clear()

    def count(self) -> int:
        self.cleanup()
        with self._lock:
            return len(self._sessions)

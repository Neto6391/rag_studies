from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
import json

import aiosqlite

from src.domain.chat import ChatMessage

_SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    hallucinated INTEGER,
    sources TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
"""


class ConversationRepository:
    """Persistência das conversas do chat em SQLite (async via aiosqlite).
    Conexão única (singleton via app.state), criada no lifespan."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None

    async def init(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self._db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript(_SCHEMA)
        await self._ensure_sources_column()
        await self._conn.commit()

    async def _ensure_sources_column(self) -> None:
        cursor = await self._conn.execute("PRAGMA table_info(messages)")
        columns = {row["name"] for row in await cursor.fetchall()}
        if "sources" not in columns:
            await self._conn.execute("ALTER TABLE messages ADD COLUMN sources TEXT")

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        sources: Optional[List[dict]] = None,
    ) -> int:
        created_at = datetime.now(timezone.utc).isoformat()
        sources_json = json.dumps(sources, ensure_ascii=False) if sources else None
        cursor = await self._conn.execute(
            """
            INSERT INTO messages (session_id, role, content, sources, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, role, content, sources_json, created_at),
        )
        await self._conn.commit()
        return cursor.lastrowid

    async def set_hallucinated(self, message_id: int, hallucinated: bool) -> None:
        await self._conn.execute(
            "UPDATE messages SET hallucinated = ? WHERE id = ?",
            (1 if hallucinated else 0, message_id),
        )
        await self._conn.commit()

    async def set_sources(self, message_id: int, sources: List[dict]) -> None:
        await self._conn.execute(
            "UPDATE messages SET sources = ? WHERE id = ?",
            (json.dumps(sources, ensure_ascii=False), message_id),
        )
        await self._conn.commit()

    async def get_by_session(self, session_id: str) -> List[ChatMessage]:
        cursor = await self._conn.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY id ASC",
            (session_id,),
        )
        rows = await cursor.fetchall()
        return [self._to_message(row) for row in rows]

    async def list_sessions(self) -> List[dict]:
        cursor = await self._conn.execute(
            """
            SELECT
                session_id AS session_id,
                COUNT(*) AS message_count,
                MIN(created_at) AS created_at,
                MAX(created_at) AS updated_at,
                (
                    SELECT content FROM messages AS m2
                    WHERE m2.session_id = messages.session_id AND m2.role = 'user'
                    ORDER BY m2.id ASC
                    LIMIT 1
                ) AS preview
            FROM messages
            GROUP BY session_id
            ORDER BY updated_at DESC
            """
        )
        rows = await cursor.fetchall()
        return [
            {
                "session_id": row["session_id"],
                "message_count": row["message_count"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "preview": row["preview"] or "Nova conversa",
            }
            for row in rows
        ]

    async def delete_session(self, session_id: str) -> int:
        cursor = await self._conn.execute(
            "DELETE FROM messages WHERE session_id = ?",
            (session_id,),
        )
        await self._conn.commit()
        return cursor.rowcount

    async def _count(self, query: str) -> int:
        cursor = await self._conn.execute(query)
        row = await cursor.fetchone()
        return row[0] if row else 0

    async def count_messages(self) -> int:
        return await self._count("SELECT COUNT(*) FROM messages")

    async def count_sessions(self) -> int:
        return await self._count("SELECT COUNT(DISTINCT session_id) FROM messages")

    async def count_hallucinations(self) -> int:
        return await self._count("SELECT COUNT(*) FROM messages WHERE hallucinated = 1")

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()

    @staticmethod
    def _to_message(row: aiosqlite.Row) -> ChatMessage:
        hallucinated = row["hallucinated"]
        sources_raw = row["sources"] if "sources" in row.keys() else None
        sources = None
        if sources_raw:
            try:
                parsed = json.loads(sources_raw)
                if isinstance(parsed, list):
                    sources = parsed
            except json.JSONDecodeError:
                sources = None
        return ChatMessage(
            id=row["id"],
            session_id=row["session_id"],
            role=row["role"],
            content=row["content"],
            hallucinated=None if hallucinated is None else bool(hallucinated),
            created_at=row["created_at"],
            sources=sources,
        )

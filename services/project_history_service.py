"""Small SQLite persistence boundary for the browser MVP.

The service stores only durable project/job history metadata. Generation and
AI Universe orchestration remain in their existing application services.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ProjectHistoryService:
    """Persist project and generation-job history without owning generation."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    topic TEXT NOT NULL,
                    universe_id TEXT,
                    avatar_id TEXT,
                    location_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS generation_jobs (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    output_path TEXT,
                    output_metadata TEXT NOT NULL DEFAULT '{}',
                    error_message TEXT NOT NULL DEFAULT '',
                    FOREIGN KEY(project_id) REFERENCES projects(id)
                )
                """
            )
            db.execute("CREATE INDEX IF NOT EXISTS idx_jobs_project ON generation_jobs(project_id)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_projects_updated ON projects(updated_at DESC)")

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def create_project(
        self,
        topic: str,
        *,
        universe_id: str | None = None,
        avatar_id: str | None = None,
        location_id: str | None = None,
    ) -> str:
        project_id = uuid.uuid4().hex
        now = self._now()
        with self._lock, self._connect() as db:
            db.execute(
                "INSERT INTO projects(id, topic, universe_id, avatar_id, location_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (project_id, topic, universe_id, avatar_id, location_id, now, now),
            )
        return project_id

    def create_job(self, project_id: str) -> str:
        job_id = uuid.uuid4().hex
        now = self._now()
        with self._lock, self._connect() as db:
            db.execute(
                "INSERT INTO generation_jobs(id, project_id, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (job_id, project_id, "queued", now, now),
            )
            db.execute("UPDATE projects SET updated_at = ? WHERE id = ?", (now, project_id))
        return job_id

    def update_job(
        self,
        job_id: str,
        *,
        status: str | None = None,
        output_path: str | None = None,
        output_metadata: dict[str, Any] | None = None,
        error_message: str | None = None,
    ) -> None:
        updates: list[str] = ["updated_at = ?"]
        values: list[Any] = [self._now()]
        if status is not None:
            updates.append("status = ?")
            values.append(status)
        if output_path is not None:
            updates.append("output_path = ?")
            values.append(output_path)
        if output_metadata is not None:
            updates.append("output_metadata = ?")
            values.append(json.dumps(output_metadata, sort_keys=True))
        if error_message is not None:
            updates.append("error_message = ?")
            values.append(error_message)
        values.append(job_id)
        with self._lock, self._connect() as db:
            db.execute(f"UPDATE generation_jobs SET {', '.join(updates)} WHERE id = ?", values)
            db.execute(
                "UPDATE projects SET updated_at = (SELECT updated_at FROM generation_jobs WHERE id = ?) WHERE id = (SELECT project_id FROM generation_jobs WHERE id = ?)",
                (job_id, job_id),
            )

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT j.*, p.topic, p.universe_id, p.avatar_id, p.location_id FROM generation_jobs j JOIN projects p ON p.id = j.project_id WHERE j.id = ?",
                (job_id,),
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def list_recent(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT j.*, p.topic, p.universe_id, p.avatar_id, p.location_id FROM generation_jobs j JOIN projects p ON p.id = j.project_id ORDER BY j.updated_at DESC LIMIT ?",
                (max(1, min(limit, 100)),),
            ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        result = dict(row)
        result["output_metadata"] = json.loads(result.get("output_metadata") or "{}")
        return result

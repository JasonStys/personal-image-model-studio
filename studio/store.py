"""Short-lived parameter-bound SQLite metadata storage; private large artifacts stay on disk."""

from __future__ import annotations

# Index: declarations module.Store@L13, Store.__init__@L16, Store.connection@L31, Store.put@L40, Store.get@L51, Store.list@L61, Store.add_feedback@L69, Store.feedback@L77, Store.quarantine@L86; variables root@L16, self@L16, db@L20, db@L24, self@L31, db@L33, body@L40, identity@L40, kind@L40, self@L40, text@L42, db@L45, identity@L51, kind@L51, self@L51, db@L53, row@L54, kind@L61, limit@L61, self@L61, db@L63, rows@L64, row@L67, body@L69, identity@L69, self@L69, db@L72, identity@L77, self@L77, db@L79, rows@L80, row@L84, identity@L86, records@L86, self@L86, db@L88, r@L95. Purposes/parameters: docs/code-map.json.
import json
import sqlite3
import time
from contextlib import contextmanager, closing
from pathlib import Path


class Store:
    """Small metadata repository with separate AI-origin quarantine database and explicit job lifecycle."""

    def __init__(self, root: Path):
        """Initialize additive schemas without overwriting user data."""
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript(
                "PRAGMA journal_mode=WAL; CREATE TABLE IF NOT EXISTS records(kind TEXT,id TEXT,body TEXT,created REAL,PRIMARY KEY(kind,id)); CREATE TABLE IF NOT EXISTS feedback(image_id TEXT,body TEXT,created REAL);"
            )
        with closing(sqlite3.connect(self.root / "quarantine.sqlite")) as db:
            with db:
                db.execute(
                    "CREATE TABLE IF NOT EXISTS flagged(dataset_id TEXT,image_hash TEXT,body TEXT,PRIMARY KEY(dataset_id,image_hash))"
                )

    @contextmanager
    def connection(self):
        """Commit/rollback and close every connection even when an operation raises."""
        db = sqlite3.connect(self.root / "studio.sqlite", timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    def put(self, kind: str, identity: str, body: dict) -> None:
        """Upsert one bounded metadata record; SQL identifiers are never derived from user text."""
        text = json.dumps(body, allow_nan=False)
        if len(text) > 2_000_000:
            raise ValueError("Record exceeds metadata limit")
        with self.connection() as db:
            db.execute(
                "INSERT INTO records VALUES(?,?,?,?) ON CONFLICT(kind,id) DO UPDATE SET body=excluded.body",
                (kind, identity, text, time.time()),
            )

    def get(self, kind: str, identity: str) -> dict:
        """Fetch one record by exact identity; unknown identities do not become file paths."""
        with self.connection() as db:
            row = db.execute(
                "SELECT body FROM records WHERE kind=? AND id=?", (kind, identity)
            ).fetchone()
        if not row:
            raise KeyError("Record not found")
        return json.loads(row[0])

    def list(self, kind: str, limit: int = 100) -> list[dict]:
        """Return a bounded newest-first list for the single-user workspace."""
        with self.connection() as db:
            rows = db.execute(
                "SELECT body FROM records WHERE kind=? ORDER BY created DESC LIMIT ?", (kind, limit)
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def add_feedback(self, identity: str, body: dict) -> None:
        """Preserve timestamped human feedback without applying hidden optimizer updates."""
        self.get("image", identity)
        with self.connection() as db:
            db.execute(
                "INSERT INTO feedback VALUES(?,?,?)", (identity, json.dumps(body), time.time())
            )

    def feedback(self, identity: str) -> list[dict]:
        """Read recent feedback in a stable timestamp sequence."""
        with self.connection() as db:
            rows = db.execute(
                "SELECT body FROM feedback WHERE image_id=? ORDER BY created DESC LIMIT 100",
                (identity,),
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def quarantine(self, identity: str, records: list[dict]) -> None:
        """Retain explicit AI-origin records in a physically separate metadata database."""
        db = sqlite3.connect(self.root / "quarantine.sqlite")
        try:
            with db:
                db.executemany(
                    "INSERT OR REPLACE INTO flagged VALUES(?,?,?)",
                    [
                        (identity, r["hash"], json.dumps(r))
                        for r in records
                        if r["origin"].startswith("ai_")
                    ],
                )
        finally:
            db.close()

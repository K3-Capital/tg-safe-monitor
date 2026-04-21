from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from .models import MonitoredSafe


class MonitorRepository:
    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS monitored_safes (
                    safe_address TEXT PRIMARY KEY,
                    added_by_user_id INTEGER,
                    added_by_username TEXT,
                    bootstrap_transaction_count INTEGER NOT NULL,
                    added_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS seen_transactions (
                    safe_address TEXT NOT NULL,
                    tx_uid TEXT NOT NULL,
                    first_seen_at TEXT NOT NULL,
                    PRIMARY KEY (safe_address, tx_uid),
                    FOREIGN KEY (safe_address) REFERENCES monitored_safes (safe_address) ON DELETE CASCADE
                );
                """
            )
            connection.commit()

    def add_safe(
        self,
        safe_address: str,
        *,
        added_by_user_id: int | None,
        added_by_username: str | None,
        bootstrap_transaction_count: int,
    ) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO monitored_safes (
                    safe_address,
                    added_by_user_id,
                    added_by_username,
                    bootstrap_transaction_count,
                    added_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    safe_address,
                    added_by_user_id,
                    added_by_username,
                    bootstrap_transaction_count,
                    datetime.now(UTC).isoformat(),
                ),
            )
            connection.commit()

    def remove_safe(self, safe_address: str) -> bool:
        with closing(self._connect()) as connection:
            cursor = connection.execute(
                "DELETE FROM monitored_safes WHERE safe_address = ?",
                (safe_address,),
            )
            connection.execute(
                "DELETE FROM seen_transactions WHERE safe_address = ?",
                (safe_address,),
            )
            connection.commit()
            return cursor.rowcount > 0

    def list_safes(self) -> list[MonitoredSafe]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT safe_address, added_by_user_id, added_by_username, bootstrap_transaction_count, added_at "
                "FROM monitored_safes ORDER BY safe_address"
            ).fetchall()
        return [
            MonitoredSafe(
                safe_address=row["safe_address"],
                added_by_user_id=row["added_by_user_id"],
                added_by_username=row["added_by_username"],
                bootstrap_transaction_count=row["bootstrap_transaction_count"],
                added_at=row["added_at"],
            )
            for row in rows
        ]

    def list_safe_addresses(self) -> list[str]:
        return [safe.safe_address for safe in self.list_safes()]

    def is_safe_monitored(self, safe_address: str) -> bool:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT 1 FROM monitored_safes WHERE safe_address = ?",
                (safe_address,),
            ).fetchone()
        return row is not None

    def record_seen_transaction(self, safe_address: str, tx_uid: str) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                "INSERT OR IGNORE INTO seen_transactions (safe_address, tx_uid, first_seen_at) VALUES (?, ?, ?)",
                (safe_address, tx_uid, datetime.now(UTC).isoformat()),
            )
            connection.commit()

    def has_seen_transaction(self, safe_address: str, tx_uid: str) -> bool:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT 1 FROM seen_transactions WHERE safe_address = ? AND tx_uid = ?",
                (safe_address, tx_uid),
            ).fetchone()
        return row is not None

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

import psycopg
from psycopg.rows import dict_row

from .models import MonitoredSafe


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class MonitorRepository(Protocol):
    def add_safe(
        self,
        safe_address: str,
        *,
        added_by_user_id: int | None,
        added_by_username: str | None,
        bootstrap_transaction_count: int,
    ) -> None: ...

    def remove_safe(self, safe_address: str) -> bool: ...

    def list_safes(self) -> list[MonitoredSafe]: ...

    def list_safe_addresses(self) -> list[str]: ...

    def is_safe_monitored(self, safe_address: str) -> bool: ...

    def record_seen_transaction(self, safe_address: str, tx_uid: str) -> None: ...

    def has_seen_transaction(self, safe_address: str, tx_uid: str) -> bool: ...


class InMemoryMonitorRepository:
    def __init__(self) -> None:
        self._safes: dict[str, MonitoredSafe] = {}
        self._seen_transactions: set[tuple[str, str]] = set()

    def add_safe(
        self,
        safe_address: str,
        *,
        added_by_user_id: int | None,
        added_by_username: str | None,
        bootstrap_transaction_count: int,
    ) -> None:
        self._safes[safe_address] = MonitoredSafe(
            safe_address=safe_address,
            added_by_user_id=added_by_user_id,
            added_by_username=added_by_username,
            bootstrap_transaction_count=bootstrap_transaction_count,
            added_at=_now_iso(),
        )

    def remove_safe(self, safe_address: str) -> bool:
        removed = self._safes.pop(safe_address, None) is not None
        self._seen_transactions = {
            pair for pair in self._seen_transactions if pair[0] != safe_address
        }
        return removed

    def list_safes(self) -> list[MonitoredSafe]:
        return [self._safes[address] for address in sorted(self._safes)]

    def list_safe_addresses(self) -> list[str]:
        return [safe.safe_address for safe in self.list_safes()]

    def is_safe_monitored(self, safe_address: str) -> bool:
        return safe_address in self._safes

    def record_seen_transaction(self, safe_address: str, tx_uid: str) -> None:
        self._seen_transactions.add((safe_address, tx_uid))

    def has_seen_transaction(self, safe_address: str, tx_uid: str) -> bool:
        return (safe_address, tx_uid) in self._seen_transactions


class PostgresMonitorRepository:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self._initialize()

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self.database_url, row_factory=dict_row)

    def _initialize(self) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS monitored_safes (
                        safe_address TEXT PRIMARY KEY,
                        added_by_user_id BIGINT,
                        added_by_username TEXT,
                        bootstrap_transaction_count INTEGER NOT NULL,
                        added_at TIMESTAMPTZ NOT NULL
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS seen_transactions (
                        safe_address TEXT NOT NULL REFERENCES monitored_safes (safe_address) ON DELETE CASCADE,
                        tx_uid TEXT NOT NULL,
                        first_seen_at TIMESTAMPTZ NOT NULL,
                        PRIMARY KEY (safe_address, tx_uid)
                    )
                    """
                )

    def add_safe(
        self,
        safe_address: str,
        *,
        added_by_user_id: int | None,
        added_by_username: str | None,
        bootstrap_transaction_count: int,
    ) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO monitored_safes (
                        safe_address,
                        added_by_user_id,
                        added_by_username,
                        bootstrap_transaction_count,
                        added_at
                    ) VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (safe_address) DO UPDATE SET
                        added_by_user_id = EXCLUDED.added_by_user_id,
                        added_by_username = EXCLUDED.added_by_username,
                        bootstrap_transaction_count = EXCLUDED.bootstrap_transaction_count,
                        added_at = EXCLUDED.added_at
                    """,
                    (
                        safe_address,
                        added_by_user_id,
                        added_by_username,
                        bootstrap_transaction_count,
                        _now_iso(),
                    ),
                )

    def remove_safe(self, safe_address: str) -> bool:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM monitored_safes WHERE safe_address = %s",
                    (safe_address,),
                )
                return cursor.rowcount > 0

    def list_safes(self) -> list[MonitoredSafe]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT safe_address, added_by_user_id, added_by_username, bootstrap_transaction_count, added_at
                    FROM monitored_safes
                    ORDER BY safe_address
                    """
                )
                rows = cursor.fetchall()
        return [self._to_monitored_safe(row) for row in rows]

    def list_safe_addresses(self) -> list[str]:
        return [safe.safe_address for safe in self.list_safes()]

    def is_safe_monitored(self, safe_address: str) -> bool:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM monitored_safes WHERE safe_address = %s",
                    (safe_address,),
                )
                return cursor.fetchone() is not None

    def record_seen_transaction(self, safe_address: str, tx_uid: str) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO seen_transactions (safe_address, tx_uid, first_seen_at)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (safe_address, tx_uid) DO NOTHING
                    """,
                    (safe_address, tx_uid, _now_iso()),
                )

    def has_seen_transaction(self, safe_address: str, tx_uid: str) -> bool:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM seen_transactions WHERE safe_address = %s AND tx_uid = %s",
                    (safe_address, tx_uid),
                )
                return cursor.fetchone() is not None

    @staticmethod
    def _to_monitored_safe(row: dict) -> MonitoredSafe:
        added_at = row["added_at"]
        if isinstance(added_at, datetime):
            added_at = added_at.isoformat()
        return MonitoredSafe(
            safe_address=row["safe_address"],
            added_by_user_id=row["added_by_user_id"],
            added_by_username=row["added_by_username"],
            bootstrap_transaction_count=row["bootstrap_transaction_count"],
            added_at=added_at,
        )
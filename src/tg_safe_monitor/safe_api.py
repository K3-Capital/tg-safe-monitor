from __future__ import annotations

import logging
from collections.abc import Mapping

import httpx

from .models import SafeTransaction

logger = logging.getLogger(__name__)


class SafeApiClient:
    def __init__(self, base_url: str, token: str = "", http_client: httpx.AsyncClient | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.http_client = http_client or httpx.AsyncClient(timeout=20.0)
        self._owns_client = http_client is None

    async def aclose(self) -> None:
        if self._owns_client:
            await self.http_client.aclose()

    async def is_safe(self, safe_address: str) -> bool:
        headers = {"accept": "application/json"}
        if self.token:
            headers["Authorization"] = self.token
        details_base = self.base_url.replace("/api/v2", "/api/v1") if "/api/v2" in self.base_url else self.base_url
        response = await self.http_client.get(f"{details_base}/safes/{safe_address}/", headers=headers)
        if response.status_code == 404:
            return False
        response.raise_for_status()
        return True

    async def list_transactions(self, safe_address: str) -> list[SafeTransaction]:
        url: str | None = f"{self.base_url}/safes/{safe_address}/multisig-transactions/"
        results: list[SafeTransaction] = []
        headers = {"accept": "application/json"}
        if self.token:
            headers["Authorization"] = self.token

        while url:
            response = await self.http_client.get(url, headers=headers)
            response.raise_for_status()
            payload = response.json()
            items = payload.get("results", [])
            results.extend(self._parse_transaction(safe_address, item) for item in items)
            url = payload.get("next")

        return results

    def _parse_transaction(self, safe_address: str, payload: Mapping[str, object]) -> SafeTransaction:
        safe_tx_hash = _string_or_none(payload.get("safeTxHash")) or _string_or_none(payload.get("safe_tx_hash"))
        tx_hash = _string_or_none(payload.get("transactionHash")) or _string_or_none(payload.get("transaction_hash"))
        nonce = _int_or_none(payload.get("nonce"))
        submission_date = _string_or_none(payload.get("submissionDate")) or _string_or_none(payload.get("submission_date"))
        tx_uid = safe_tx_hash or tx_hash or f"{safe_address}:{nonce}:{submission_date}"

        confirmations = payload.get("confirmations")
        confirmations_submitted = len(confirmations) if isinstance(confirmations, list) else None
        executed = bool(
            payload.get("isExecuted")
            or payload.get("is_executed")
            or payload.get("executionDate")
            or payload.get("execution_date")
            or tx_hash
        )

        return SafeTransaction(
            safe_address=safe_address,
            tx_uid=tx_uid,
            safe_tx_hash=safe_tx_hash,
            nonce=nonce,
            to=_string_or_none(payload.get("to")),
            value=_string_or_none(payload.get("value")),
            executed=executed,
            transaction_hash=tx_hash,
            operation=_int_or_none(payload.get("operation")),
            submission_date=submission_date,
            proposer=_extract_proposer(payload.get("proposer")),
            confirmations_submitted=confirmations_submitted,
        )


def _string_or_none(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _int_or_none(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            logger.debug("Could not coerce value %r to int", value)
            return None
    logger.debug("Could not coerce value %r to int", value)
    return None


def _extract_proposer(value: object) -> str | None:
    if isinstance(value, Mapping):
        return _string_or_none(value.get("value") or value.get("address"))
    return _string_or_none(value)

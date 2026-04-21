from __future__ import annotations

from collections.abc import Mapping

import httpx

from .models import ContractCallTransaction


class EthereumRpcClient:
    def __init__(self, rpc_url: str, http_client: httpx.AsyncClient | None = None) -> None:
        self.rpc_url = rpc_url.rstrip("/")
        self.http_client = http_client or httpx.AsyncClient(timeout=20.0)
        self._owns_client = http_client is None
        self._request_id = 0

    async def aclose(self) -> None:
        if self._owns_client:
            await self.http_client.aclose()

    async def get_block_number(self) -> int:
        result = await self._rpc("eth_blockNumber", [])
        return _hex_to_int(result)

    async def get_block_with_transactions(self, block_number: int) -> list[ContractCallTransaction]:
        result = await self._rpc("eth_getBlockByNumber", [hex(block_number), True])
        if not isinstance(result, Mapping):
            return []
        transactions = result.get("transactions", [])
        if not isinstance(transactions, list):
            return []
        return [self._parse_transaction(tx) for tx in transactions if isinstance(tx, Mapping)]

    async def get_transaction_receipt(self, tx_hash: str) -> Mapping[str, object] | None:
        result = await self._rpc("eth_getTransactionReceipt", [tx_hash])
        return result if isinstance(result, Mapping) else None

    async def get_code(self, address: str, block_tag: str = "latest") -> str:
        result = await self._rpc("eth_getCode", [address, block_tag])
        return str(result)

    async def _rpc(self, method: str, params: list[object]) -> object:
        self._request_id += 1
        response = await self.http_client.post(
            self.rpc_url,
            json={
                "jsonrpc": "2.0",
                "id": self._request_id,
                "method": method,
                "params": params,
            },
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("error"):
            raise RuntimeError(f"Ethereum RPC error for {method}: {payload['error']}")
        return payload.get("result")

    @staticmethod
    def _parse_transaction(payload: Mapping[str, object]) -> ContractCallTransaction:
        input_data = _string_or_default(payload.get("input"), "0x")
        return ContractCallTransaction(
            tx_hash=_string_or_default(payload.get("hash"), ""),
            block_number=_hex_to_int(payload.get("blockNumber")),
            from_address=_string_or_default(payload.get("from"), ""),
            to_address=_string_or_none(payload.get("to")),
            value=_normalize_value(payload.get("value")),
            input_data=input_data,
            selector=_selector_from_input(input_data),
            success=None,
        )


def _hex_to_int(value: object) -> int:
    if value is None:
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value, 16) if value.startswith("0x") else int(value)
    raise TypeError(f"Unsupported numeric value: {value!r}")


def _string_or_none(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _string_or_default(value: object, default: str) -> str:
    if value is None:
        return default
    return str(value)


def _normalize_value(value: object) -> str:
    if value is None:
        return "0"
    if isinstance(value, str) and value.startswith("0x"):
        return str(int(value, 16))
    return str(value)


def _selector_from_input(input_data: str) -> str | None:
    if not input_data or input_data == "0x" or len(input_data) < 10:
        return None
    return input_data[:10]

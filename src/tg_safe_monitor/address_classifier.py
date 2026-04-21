from __future__ import annotations

from eth_utils.address import is_address, to_checksum_address

from .models import AddressType, ClassifiedAddress


class AddressClassifier:
    def __init__(self, rpc_client, safe_client) -> None:
        self.rpc_client = rpc_client
        self.safe_client = safe_client

    async def classify(self, address: str) -> ClassifiedAddress:
        if not is_address(address):
            raise ValueError(f"Invalid address: {address}")
        normalized = to_checksum_address(address)
        code = await self.rpc_client.get_code(normalized, "latest")
        if not code or code == "0x":
            return ClassifiedAddress(address=normalized, address_type=AddressType.EOA)
        if await self.safe_client.is_safe(normalized):
            return ClassifiedAddress(address=normalized, address_type=AddressType.SAFE)
        return ClassifiedAddress(address=normalized, address_type=AddressType.CONTRACT)

from typing import cast

import pytest
from telegram import Update
from telegram.constants import ParseMode

from tg_safe_monitor.bot import _reply


class FakeMessage:
    def __init__(self) -> None:
        self.calls = []

    async def reply_text(self, text: str, **kwargs) -> None:
        self.calls.append((text, kwargs))


class FakeUpdate:
    def __init__(self, message: FakeMessage) -> None:
        self.effective_message = message


@pytest.mark.asyncio
async def test_reply_uses_markdown_parse_mode_for_inline_links() -> None:
    message = FakeMessage()
    update = FakeUpdate(message)

    await _reply(cast(Update, update), "See [label](https://etherscan.io/address/0x123)")

    assert message.calls == [
        (
            "See [label](https://etherscan.io/address/0x123)",
            {"parse_mode": ParseMode.MARKDOWN},
        )
    ]
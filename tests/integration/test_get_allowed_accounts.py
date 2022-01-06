import logging
import pytest

from podping_hivewriter.podping_hivewriter import get_allowed_accounts

from lighthive.client import Client


@pytest.mark.asyncio
async def test_get_allowed_accounts():
    # Checks the allowed accounts checkup
    client = Client(loglevel=logging.INFO)
    allowed_accounts = get_allowed_accounts(client)
    assert type(allowed_accounts) == set and len(allowed_accounts) > 0

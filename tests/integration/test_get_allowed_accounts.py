import logging
import pytest

from podping_hivewriter.hive import get_allowed_accounts

from lighthive.client import Client


@pytest.mark.asyncio
async def test_get_allowed_accounts():
    # Checks the allowed accounts checkup
    client = Client(loglevel=logging.WARN)
    allowed_accounts = get_allowed_accounts(client)
    assert type(allowed_accounts) == set and len(allowed_accounts) > 0

import pytest

from podping_hivewriter.hive import get_allowed_accounts


@pytest.mark.asyncio
async def test_get_allowed_accounts(lighthive_client):
    # Checks the allowed accounts checkup
    allowed_accounts = get_allowed_accounts(lighthive_client)
    assert type(allowed_accounts) == set and len(allowed_accounts) > 0

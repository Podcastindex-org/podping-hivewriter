import pytest

from podping_hivewriter import config, hive_writer


@pytest.mark.asyncio
async def test_get_allowed_accounts():
    # Checks the allowed accounts checkup
    allowed_accounts = hive_writer.get_allowed_accounts()
    if type(allowed_accounts) == set and len(allowed_accounts) > 0:
        assert True
    else:
        assert False

import pytest

from podping_hivewriter import config, run
from podping_hivewriter.podping_hivewriter import get_allowed_accounts


@pytest.mark.asyncio
async def test_get_allowed_accounts():
    # Checks the allowed accounts checkup
    allowed_accounts = get_allowed_accounts()
    if type(allowed_accounts) == set and len(allowed_accounts) > 0:
        assert True
    else:
        assert False

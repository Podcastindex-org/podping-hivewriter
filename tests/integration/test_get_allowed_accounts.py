import pytest

from podping_hivewriter.models.podping_settings import PodpingSettings
from podping_hivewriter.podping_hivewriter import get_allowed_accounts


@pytest.mark.asyncio
async def test_get_allowed_accounts():
    # Checks the allowed accounts checkup
    settings = PodpingSettings()
    allowed_accounts = get_allowed_accounts(settings.main_nodes)

    assert type(allowed_accounts) == set and len(allowed_accounts) > 0

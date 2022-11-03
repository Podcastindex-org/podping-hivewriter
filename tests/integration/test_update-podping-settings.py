import asyncio
import sys

import pytest

from podping_hivewriter import podping_settings
from podping_hivewriter.podping_settings_manager import PodpingSettingsManager


@pytest.mark.asyncio
async def test_update_podping_settings():
    # See if we can fetch data from podping
    # Must not use Testnet when looking for config data

    check_period = sys.maxsize

    # Override the default value of the dataclass
    podping_settings.PodpingSettings.__fields__[
        "control_account_check_period"
    ].default = check_period

    with PodpingSettingsManager(ignore_updates=True) as settings_manager:
        await settings_manager.update_podping_settings()
        answer = settings_manager._settings.control_account_check_period

        assert settings_manager.last_update_time != float("-inf")

    # Compare properties specifically because we aren't overriding all default values
    assert check_period != answer


@pytest.mark.asyncio
@pytest.mark.slow
async def test_update_podping_settings_loop(lighthive_client):
    # See if we can fetch data from podping
    # Must not use Testnet when looking for config data

    check_period = 1

    # Override the default value of the dataclass
    podping_settings.PodpingSettings.__fields__[
        "control_account_check_period"
    ].default = check_period

    with PodpingSettingsManager(
        ignore_updates=False, client=lighthive_client
    ) as settings_manager:
        await asyncio.sleep(3)

        # Check last update time
        assert settings_manager.last_update_time != float("-inf")

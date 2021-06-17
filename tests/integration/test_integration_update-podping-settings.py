import sys

import pytest

from podping_hivewriter import config, hive_writer


@pytest.mark.asyncio
async def test_update_podping_settings():
    # See if we can fetch data from podping
    # Must not use Testnet when looking for config data
    test_account_check_period = sys.maxsize
    config.Config.podping_settings.control_account_check_period = (
        test_account_check_period
    )
    await hive_writer.update_podping_settings("podping")

    # Compare properties specifically because we aren't overriding all default values
    assert (
        test_account_check_period
        != config.Config.podping_settings.control_account_check_period
    )

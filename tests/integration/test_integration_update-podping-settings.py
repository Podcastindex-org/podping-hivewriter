import sys
import asyncio
import pytest

from podping_hivewriter import config
from podping_hivewriter.run import update_podping_settings


@pytest.mark.asyncio
async def test_update_podping_settings():
    # See if we can fetch data from podping
    # Must not use Testnet when looking for config data

    #Other tests are changing this setting:
    config.Config.ignore_updates = False
    
    test_account_check_period = sys.maxsize
    config.Config.podping_settings.control_account_check_period = (
        test_account_check_period
    )
    await update_podping_settings("podping")
    await asyncio.sleep(2)
    answer = config.Config.podping_settings.control_account_check_period
    # Compare properties specifically because we aren't overriding all default values
    assert test_account_check_period != answer

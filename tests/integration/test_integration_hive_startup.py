import pytest
from beem.account import Account

from podping_hivewriter import config, hive_writer


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.timeout(10)
async def test_hive_startup():
    # Run the entire startup procedure and check returned hive object
    # Check on the main chain
    config.Config.test = False
    test_hive = await hive_writer.hive_startup()

    try:
        account = Account("podping", blockchain_instance=test_hive)
        print(account)
        assert True
    except Exception as ex:
        print(ex)
        assert False

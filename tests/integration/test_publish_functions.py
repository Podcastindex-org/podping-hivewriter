import os
import pytest
import asyncio
from podping_hivewriter.publish import publish, publish_async

EXAMPLE_DATA = [
    "https://3speak.tv/rss/brianoflondon.xml",
    "https://3speak.tv/rss/theycallmedan.xml",
]


def test_publish():
    server_account = os.environ["PODPING_HIVE_ACCOUNT"]
    posting_keys = [os.environ["PODPING_HIVE_POSTING_KEY"]]
    try:
        publish(
            iris=EXAMPLE_DATA,
            server_account=server_account,
            posting_keys=posting_keys,
            livetest=True,
            medium="podcast",
            reason="live",
            dry_run=True,
        )
        assert True
    except Exception:
        assert False


@pytest.mark.asyncio
async def test_publish_async():
    server_account = os.environ["PODPING_HIVE_ACCOUNT"]
    posting_keys = [os.environ["PODPING_HIVE_POSTING_KEY"]]
    try:
        await publish_async(
            iris=EXAMPLE_DATA,
            server_account=server_account,
            posting_keys=posting_keys,
            livetest=True,
            medium="podcast",
            reason="live",
            dry_run=True,
        )
        assert True
    except Exception as ex:
        print(ex)
        assert False

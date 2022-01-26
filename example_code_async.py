import asyncio
import logging
import os

from podping_hivewriter.send_podping import send_podpings_async


EXAMPLE_DATA = [
    "https://3speak.tv/rss/brianoflondon.xml",
    "https://3speak.tv/rss/theycallmedan.xml",
]


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S%z",
)


if __name__ == "__main__":
    server_account = os.environ["PODPING_HIVE_ACCOUNT"]
    posting_keys = [os.environ["PODPING_HIVE_POSTING_KEY"]]
    asyncio.run(
        send_podpings_async(
            iris=EXAMPLE_DATA,
            server_account=server_account,
            posting_keys=posting_keys,
            dry_run=True,
        )
    )

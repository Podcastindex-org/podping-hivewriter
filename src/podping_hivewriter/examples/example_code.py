import logging
import os

from podping_hivewriter.publish import publish


EXAMPLE_DATA = [
    "https://3speak.tv/rss/brianoflondon.xml",
    "https://3speak.tv/rss/theycallmedan.xml",
]

# You can set a logging level appropriate for your code.
# Set to .WARNING for fewer logging m

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S%z",
)


if __name__ == "__main__":
    server_account = os.environ["PODPING_HIVE_ACCOUNT"]
    posting_keys = [os.environ["PODPING_HIVE_POSTING_KEY"]]
    publish(
        iris=EXAMPLE_DATA,
        server_account=server_account,
        posting_keys=posting_keys,
        dry_run=True,
    )

import asyncio
import logging
import os

from podping_hivewriter.publish import publish_async


EXAMPLE_DATA = [
    "https://3speak.tv/rss/brianoflondon.xml",
    "https://3speak.tv/rss/theycallmedan.xml",
]


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S%z",
)


# medium must be one of newsletter, music, blog, audiobook, video, film, podcast
# reason must be one of live, update
# These codes can be found enumerated in

if __name__ == "__main__":
    server_account = os.environ["PODPING_HIVE_ACCOUNT"]
    posting_keys = [os.environ["PODPING_HIVE_POSTING_KEY"]]
    try:
        asyncio.run(
            publish_async(
                iris=EXAMPLE_DATA,
                server_account=server_account,
                posting_keys=posting_keys,
                livetest=True,
                medium="podcast",
                reason="live",
                dry_run=True,
            )
        )
    except Exception as ex:
        print(ex)

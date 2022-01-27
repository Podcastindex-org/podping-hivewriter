import asyncio
import logging
import os

from podping_hivewriter.publish import publish_async


EXAMPLE_DATA = [
    "https://3speak.tv/rss/brianoflondon.xml",
    "https://3speak.tv/rss/theycallmedan.xml",
]


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S%z",
)


# medium must be one of newsletter, music, blog, audiobook, video, film, podcast
# reason must be one of live, update

if __name__ == "__main__":
    server_account = os.environ["PODPING_HIVE_ACCOUNT"]
    # server_account = "baddata"
    posting_keys = [os.environ["PODPING_HIVE_POSTING_KEY"]]
    try:
        asyncio.run(
            publish_async(
                iris=EXAMPLE_DATA,
                server_account=server_account,
                posting_keys=posting_keys,
                medium="podcast",
                reason="live",
                dry_run=False,
            )
        )
    except Exception as ex:
        logging.error(f"{ex}")

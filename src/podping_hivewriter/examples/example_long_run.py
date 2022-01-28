import asyncio
import logging
import os
import uuid
from random import randint, random

from podping_hivewriter.publish import LoopPodpingHivewriter

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S%z",
)


async def long_test():
    """Keep producing sample iris for 10 minutes"""
    server_account = os.environ["PODPING_HIVE_ACCOUNT"]
    posting_keys = [os.environ["PODPING_HIVE_POSTING_KEY"]]

    ongoing_publish = LoopPodpingHivewriter(
        server_account=server_account,
        posting_keys=posting_keys,
        ignore_updates=False,
        livetest=True,
        medium="podcast",
        reason="live",
        dry_run=False,
    )

    async def add_batches(ongoing_publish: LoopPodpingHivewriter):
        session_uuid = uuid.uuid4()
        session_uuid_str = str(session_uuid)
        for n in range(10):
            num_iris = randint(2, 5)
            test_iris = {
                f"https://example.com?t=long_test&i={i}&s={session_uuid_str}"
                for i in range(num_iris)
            }
            for iri in test_iris:
                await ongoing_publish.iri_queue.put(iri)
                await asyncio.sleep(random())
            await asyncio.sleep(randint(55, 65))

    tasks = [add_batches(ongoing_publish)]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(long_test())

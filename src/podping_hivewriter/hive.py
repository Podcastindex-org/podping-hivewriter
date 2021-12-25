import asyncio
import logging
from typing import Iterable, Optional, List

import beem
from beemapi.exceptions import NumRetriesReached


async def get_hive(
    nodes: Iterable[str],
    posting_keys: Optional[List[str]] = None,
    nobroadcast: Optional[bool] = False,
) -> beem.Hive:
    nodes = tuple(nodes)
    errors = 0
    while True:
        try:
            if posting_keys:
                # Beem's expected type for nodes not set correctly
                # noinspection PyTypeChecker
                hive = beem.Hive(
                    node=nodes,
                    keys=posting_keys,
                    nobroadcast=nobroadcast,
                    num_retries=5,
                )

            else:
                # noinspection PyTypeChecker
                hive = beem.Hive(node=nodes, nobroadcast=nobroadcast, num_retries=5)

            return hive

        except NumRetriesReached:
            logging.warning(
                f"Unable to connect to Hive API | Internet connection down? | Failures: {errors}"
            )
            await asyncio.sleep(5 + errors * 2)
            errors += 1

        except Exception as ex:
            logging.error(f"{ex}")
            raise

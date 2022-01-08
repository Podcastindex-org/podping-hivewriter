import asyncio
import logging
from typing import Iterable, List, Optional

import beem
from beemapi.exceptions import NumRetriesReached
from lighthive.client import Client


def get_client(
    posting_keys: Optional[List[str]] = None,
    nobroadcast: Optional[bool] = False,
    nodes=None,
    connect_timeout=3,
    read_timeout=30,
    loglevel=logging.ERROR,
    chain=None,
) -> Client:
    try:
        client = Client(
            keys=posting_keys,
            nodes=nodes,
            connect_timeout=connect_timeout,
            read_timeout=read_timeout,
            loglevel=loglevel,
            chain=chain,
            automatic_node_selection=False,
        )
        return client
    except Exception as ex:
        raise ex


async def get_hive(
    nodes: Iterable[str],
    posting_keys: Optional[List[str]] = None,
    nobroadcast: Optional[bool] = False,
) -> beem.Hive:
    """Used for the test scripts only"""
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
                f"Unable to connect to Hive API | "
                f"Internet connection down? | Failures: {errors}"
            )
            await asyncio.sleep(5 + errors * 2)
            errors += 1

        except Exception as ex:
            logging.error(f"{ex}")
            raise

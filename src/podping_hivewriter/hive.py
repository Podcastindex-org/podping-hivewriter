import logging
from typing import Iterable, Optional, List
import beem
from beemapi.exceptions import NumRetriesReached


def get_hive(
    nodes: Iterable[str],
    posting_keys: Optional[List[str]] = None,
    nobroadcast: Optional[bool] = False,
) -> beem.Hive:
    nodes = tuple(nodes)

    try:
        if posting_keys:
            # Beem's expected type for nodes not set correctly
            # noinspection PyTypeChecker
            hive = beem.Hive(
                node=nodes, keys=posting_keys, nobroadcast=nobroadcast, num_retries=5
            )

        else:
            # noinspection PyTypeChecker
            hive = beem.Hive(node=nodes, nobroadcast=nobroadcast, num_retries=5)

        return hive

    except NumRetriesReached:
        logging.error(f"Unable to connect to Hive API | Internet connection down?")
        raise NumRetriesReached
    except Exception as ex:
        logging.debug(f"{ex}")
        raise

import logging
from typing import Iterable, Optional, List

import beem
from podping_hivewriter.config import Config


def get_hive(
    nodes: Iterable[str], posting_keys: Optional[List[str]] = None
) -> beem.Hive:
    nodes = tuple(nodes)

    if posting_keys:
        # Beem's expected type for nodes not set correctly
        # noinspection PyTypeChecker
        hive = beem.Hive(node=nodes, keys=posting_keys, nobroadcast=Config.nobroadcast)
    else:
        # noinspection PyTypeChecker
        hive = beem.Hive(node=nodes, nobroadcast=Config.nobroadcast)

    logging.info("---------------> Using Main Hive Chain ")

    return hive

import logging
from typing import Iterable, Optional, List

import beem


def get_hive(
    nodes: Iterable[str],
    posting_keys: Optional[List[str]] = None,
    nobroadcast: Optional[bool] = False,
) -> beem.Hive:
    nodes = tuple(nodes)

    if posting_keys:
        # Beem's expected type for nodes not set correctly
        # noinspection PyTypeChecker
        hive = beem.Hive(node=nodes, keys=posting_keys, nobroadcast=nobroadcast)
    else:
        # noinspection PyTypeChecker
        hive = beem.Hive(node=nodes, nobroadcast=nobroadcast)

    return hive

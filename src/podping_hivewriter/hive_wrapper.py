import asyncio
import itertools
import json
import logging
import random
from collections import deque
from timeit import default_timer as timer
from typing import Optional, Set, Tuple, List, Iterable

import aiohttp
import beem
from beem import nodelist
from beem.account import Account
from beem.nodelist import NodeList
from beem.transactionbuilder import TransactionBuilder
from beembase import operations

from podping_hivewriter.config import Config


def get_hive(nodes: Iterable[str], posting_key: str, use_testnet=False) -> beem.Hive:
    nodes = tuple(nodes)
    # Beem's expected type for nodes
    # noinspection PyTypeChecker
    hive = beem.Hive(node=nodes, keys=posting_key, nobroadcast=Config.nobroadcast)

    if use_testnet:
        logging.info(f"---------------> Using Test Nodes: {nodes}")
    else:
        hive.chain_params[
            "chain_id"
        ] = "beeab0de00000000000000000000000000000000000000000000000000000000"
        logging.info("---------------> Using Main Hive Chain ")

    return hive


class HiveWrapper:
    def __init__(
        self,
        nodes: Iterable[str],
        posting_key: str,
        daemon=True,
        use_testnet=False,
    ):
        self._tasks: List[asyncio.Task] = []

        self.posting_key = posting_key
        self.daemon = daemon
        self.use_testnet = use_testnet

        self.nodes = deque(nodes)
        self._hive: beem.Hive = get_hive(
            self.nodes, self.posting_key, use_testnet=self.use_testnet
        )
        self._hive_lock = asyncio.Lock()

        if daemon:
            self._add_task(asyncio.create_task(self._rotate_nodes_loop()))

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        self.close()

    def close(self):
        try:
            for task in self._tasks:
                task.cancel()
        except RuntimeError:
            pass

    def _add_task(self, task):
        self._tasks.append(task)

    async def _rotate_nodes_loop(self):
        while True:
            try:
                await self.rotate_nodes()
                await asyncio.sleep(Config.podping_settings.diagnostic_report_period)
            except Exception as e:
                logging.error(e, exc_info=True)
            except asyncio.CancelledError:
                raise

    async def rotate_nodes(self):
        async with self._hive_lock:
            self.nodes.rotate(1)
            self._hive = get_hive(
                self.nodes, self.posting_key, use_testnet=self.use_testnet
            )
            logging.info(f"New Hive Nodes in use: {self._hive}")

    async def custom_json(
        self, operation_id: str, payload: dict, required_posting_auths: List[str]
    ):
        async with self._hive_lock:
            # noinspection PyTypeChecker
            return self._hive.custom_json(
                id=operation_id,
                json_data=payload,
                required_posting_auths=required_posting_auths,
            )

    async def get_hive(self):
        async with self._hive_lock:
            return self._hive

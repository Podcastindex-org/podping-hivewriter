import asyncio
import logging
from collections import deque
from typing import List, Optional

import beem
from asgiref.sync import SyncToAsync
from podping_hivewriter.async_context import AsyncContext
from podping_hivewriter.async_wrapper import sync_to_async
from podping_hivewriter.hive import get_hive
from podping_hivewriter.podping_settings_manager import PodpingSettingsManager


class HiveWrapper(AsyncContext):
    def __init__(
        self,
        posting_keys: List[str],
        settings_manager: PodpingSettingsManager,
        dry_run=False,
        daemon=True,
    ):
        super().__init__()

        self.posting_keys = posting_keys
        self.settings_manager = settings_manager
        self.dry_run = dry_run
        self.daemon = daemon

        self.nodes: Optional[deque[str]] = None
        self._hive: Optional[beem.Hive] = None
        self._custom_json: Optional[SyncToAsync] = None
        self._hive_lock = asyncio.Lock()

        self._startup_done = False
        asyncio.ensure_future(self._startup())

    async def _startup(self):
        nodes = await self.settings_manager.get_nodes()

        self.nodes = deque(nodes)
        async with self._hive_lock:
            self._hive: beem.Hive = get_hive(
                nodes, self.posting_keys, nobroadcast=self.dry_run
            )
            self._custom_json = sync_to_async(
                self._hive.custom_json, thread_sensitive=False
            )

        if self.daemon:
            self._add_task(asyncio.create_task(self._rotate_nodes_loop()))

        self._startup_done = True

    async def wait_startup(self):
        settings = await self.settings_manager.get_settings()
        while not self._startup_done:
            await asyncio.sleep(settings.hive_operation_period)

    async def _rotate_nodes_loop(self):
        await self.wait_startup()
        while True:
            try:
                nodes = await self.settings_manager.get_nodes()
                if set(self.nodes) == set(nodes):
                    await self.rotate_nodes()
                else:
                    self.nodes = deque(nodes)
                settings = await self.settings_manager.get_settings()
                await asyncio.sleep(settings.diagnostic_report_period)
            except Exception as e:
                logging.error(e, exc_info=True)
            except asyncio.CancelledError:
                raise

    async def rotate_nodes(self):
        async with self._hive_lock:
            logging.debug(f"Rotating Hive nodes")
            self.nodes.rotate(1)
            self._hive = get_hive(
                self.nodes, self.posting_keys, nobroadcast=self.dry_run
            )
            self._custom_json = sync_to_async(
                self._hive.custom_json, thread_sensitive=False
            )
            logging.debug(f"New Hive Nodes in use: {self._hive}")

    async def custom_json(
        self, operation_id: str, payload: dict, required_posting_auths: List[str]
    ):
        await self.wait_startup()
        async with self._hive_lock:
            # noinspection PyTypeChecker
            return await self._custom_json(
                id=operation_id,
                json_data=payload,
                required_posting_auths=required_posting_auths,
            )

    async def get_hive(self):
        async with self._hive_lock:
            return self._hive

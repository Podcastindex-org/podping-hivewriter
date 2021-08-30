import asyncio
import logging
from timeit import default_timer as timer
from typing import Tuple

from podping_hivewriter.async_context import AsyncContext
from podping_hivewriter.models.podping_settings import PodpingSettings
from podping_hivewriter.podping_settings import get_podping_settings
from pydantic import ValidationError


class PodpingSettingsManager(AsyncContext):
    def __init__(self, ignore_updates=False):
        super().__init__()

        self.ignore_updates = ignore_updates

        self.last_update_time = float("-inf")

        self._settings = PodpingSettings()
        self._settings_lock = asyncio.Lock()

        self._startup_done = False
        asyncio.ensure_future(self._startup())

    async def _startup(self):
        if not self.ignore_updates:
            self._add_task(asyncio.create_task(self._update_podping_settings_loop()))

        self._startup_done = True

    async def _update_podping_settings_loop(self):
        while True:
            try:
                await self.update_podping_settings()
                await asyncio.sleep(self._settings.control_account_check_period)
            except Exception as e:
                logging.error(e, exc_info=True)
            except asyncio.CancelledError:
                raise

    async def update_podping_settings(self) -> None:
        try:
            nodes = await self.get_nodes()
            podping_settings = await get_podping_settings(
                nodes, self._settings.control_account
            )
            self.last_update_time = timer()
        except ValidationError as e:
            logging.warning(f"Problem with podping control settings: {e}")
        else:
            if self._settings != podping_settings:
                logging.debug(
                    f"Configuration override from Podping Hive: {podping_settings}"
                )
                async with self._settings_lock:
                    self._settings = podping_settings

    async def get_settings(self) -> PodpingSettings:
        async with self._settings_lock:
            return self._settings

    async def get_nodes(self) -> Tuple[str, ...]:
        settings = await self.get_settings()
        return settings.main_nodes

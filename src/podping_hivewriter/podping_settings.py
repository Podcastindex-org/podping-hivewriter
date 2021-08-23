import asyncio
import json
import logging
from timeit import default_timer as timer
from typing import Iterable, Optional, Tuple

from beem.account import Account
from podping_hivewriter.async_context import AsyncContext
from podping_hivewriter.constants import PODPING_SETTINGS_KEY
from podping_hivewriter.hive import get_hive
from podping_hivewriter.models.podping_settings import PodpingSettings
from pydantic import ValidationError


class PodpingSettingsManager(AsyncContext):
    def __init__(self, ignore_updates=False):
        super().__init__()

        self.ignore_updates = ignore_updates

        self.last_update_time = float("-inf")

        self._settings = PodpingSettings()
        self._settings_lock = asyncio.Lock()

        if not ignore_updates:
            self._add_task(asyncio.create_task(self._update_podping_settings_loop()))

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
        """Take newly found settings and put them into Config"""
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
                logging.info("Configuration override from Podping Hive")
                async with self._settings_lock:
                    self._settings = podping_settings

    async def get_settings(self) -> PodpingSettings:
        async with self._settings_lock:
            return self._settings

    async def get_nodes(self) -> Tuple[str, ...]:
        settings = await self.get_settings()
        return settings.main_nodes


async def get_settings_from_hive(
    nodes: Iterable[str], account_name: str
) -> Optional[dict]:
    """Returns podping settings if they exist"""
    # Must use main chain for settings
    hive = get_hive(nodes)
    acc = Account(account_name, blockchain_instance=hive, lazy=True)
    metadata = acc["posting_json_metadata"]
    if metadata:
        posting_meta = json.loads(metadata)
        return posting_meta.get(PODPING_SETTINGS_KEY)
    else:
        logging.error(f"posting_json_metadata for account {account_name} is empty")


async def get_podping_settings(
    nodes: Iterable[str], account_name: str
) -> PodpingSettings:
    """Return PodpingSettings object"""
    settings_dict = await get_settings_from_hive(nodes, account_name)
    return PodpingSettings.parse_obj(settings_dict)

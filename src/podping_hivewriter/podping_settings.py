import json
import logging
from typing import Iterable, Optional

from lighthive.client import Client
from podping_hivewriter.constants import PODPING_SETTINGS_KEY
from podping_hivewriter.hive import get_client
from podping_hivewriter.models.podping_settings import PodpingSettings


async def get_settings_from_hive(
    nodes: Iterable[str], account_name: str
) -> Optional[dict]:
    """Returns podping settings if they exist"""
    # Must use main chain for settings
    client: Client = get_client()
    account = client.account(account_name)
    if raw_meta := account.raw_data.get("posting_json_metadata"):
        metadata = json.loads(raw_meta)
        if podping_settings := metadata.get(PODPING_SETTINGS_KEY):
            return podping_settings
        else:
            logging.error(f"posting_json_metadata for account {account_name} is empty")


async def get_podping_settings(
    nodes: Iterable[str], account_name: str
) -> PodpingSettings:
    """Return PodpingSettings object"""
    settings_dict = await get_settings_from_hive(nodes, account_name)
    return PodpingSettings.parse_obj(settings_dict)

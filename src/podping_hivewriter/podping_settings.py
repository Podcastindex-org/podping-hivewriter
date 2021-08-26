import json
import logging
from typing import Iterable, Optional

from beem.account import Account
from podping_hivewriter.constants import PODPING_SETTINGS_KEY
from podping_hivewriter.hive import get_hive
from podping_hivewriter.models.podping_settings import PodpingSettings


async def get_settings_from_hive(
    nodes: Iterable[str], account_name: str
) -> Optional[dict]:
    """Returns podping settings if they exist"""
    # Must use main chain for settings
    hive = get_hive(nodes)
    account = Account(account_name, blockchain_instance=hive, lazy=True)
    metadata = account["posting_json_metadata"]
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

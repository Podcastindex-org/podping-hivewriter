import json
import logging
from typing import Iterable, Optional

from beem.account import Account
from podping_hivewriter.constants import PODPING_SETTINGS_KEY
from podping_hivewriter.hive import get_hive
from podping_hivewriter.models.podping_settings import PodpingSettings

import asyncio


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


async def get_fullnodeupdate_settings() -> Iterable[str]:
    """Return the most recent list of tested nodes from the @fullnodeupdate account"""
    # See https://peakd.com/@fullnodeupdate
    acc = Account("fullnodeupdate")
    json_metadata = json.loads(acc["json_metadata"])
    nodes = [item["node"] for item in json_metadata["report"] if item["hive"]]
    return nodes


async def get_podping_settings(
    nodes: Iterable[str], account_name: str
) -> PodpingSettings:
    """Return PodpingSettings object"""
    tasks = [get_settings_from_hive(nodes, account_name), get_fullnodeupdate_settings()]
    settings_dict, fullnodeupdate_nodes = await asyncio.gather(*tasks)
    if settings_dict.get("use_fullnodeupdate") == True:
        # Use the nodes from @fullnodeupdate if we find the flag "use_fullnodeupdate"
        # in the reply from the control account.
        settings_dict["main_nodes"] = fullnodeupdate_nodes
    return PodpingSettings.parse_obj(settings_dict)

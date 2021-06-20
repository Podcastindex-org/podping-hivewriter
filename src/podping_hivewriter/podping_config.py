import asyncio
import json
import logging
from timeit import default_timer as timer
from typing import Optional, Tuple

import beem
from beem.account import Account

from podping_hivewriter.config import Config, PodpingSettings

PODPING_SETTINGS_KEY = "podping-settings"


async def get_settings_from_hive(acc_name: str, nodes: Tuple[str]) -> Optional[dict]:
    """Returns podping settings if they exist"""
    hive = beem.Hive(node=nodes)
    acc = Account(acc_name, blockchain_instance=hive, lazy=True)
    posting_meta = json.loads(acc["posting_json_metadata"])
    return posting_meta.get(PODPING_SETTINGS_KEY)


async def get_podping_settings(acc_name: str, nodes: Tuple[str]) -> PodpingSettings:
    settings_dict = await get_settings_from_hive(acc_name, nodes)

    return PodpingSettings.parse_obj(settings_dict)


def run():
    logging.basicConfig(
        level=logging.INFO,
        format=f"%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s",
    )

    start = timer()
    podping_settings = asyncio.run(
        get_settings_from_hive("podping", nodes=Config.podping_settings.main_nodes)
    )

    logging.info(f"Took {timer() - start:0.2}s to fetch settings")
    if podping_settings:
        logging.info(json.dumps(podping_settings, indent=2))
    else:
        logging.warning("no settings found")


if __name__ == "__main__":
    run()

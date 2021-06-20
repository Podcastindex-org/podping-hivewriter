import asyncio
import json
import logging
from timeit import default_timer as timer
from typing import Optional, Tuple

import beem
from beem.account import Account
from beem.nodelist import NodeList
from pydantic.errors import BoolError

from podping_hivewriter.config import Config, PodpingSettings

PODPING_SETTINGS_KEY = "podping-settings"


async def get_settings_from_hive(acc_name: str, nodes: Tuple[str]) -> Optional[dict]:
    """Returns podping settings if they exist"""
    hive = beem.Hive(node=nodes)
    acc = Account(acc_name, blockchain_instance=hive, lazy=True)
    posting_meta = json.loads(acc["posting_json_metadata"])
    return posting_meta.get(PODPING_SETTINGS_KEY)


async def get_podping_settings(acc_name: str, nodes: Tuple[str]) -> PodpingSettings:
    """Return PodpingSettings object"""
    settings_dict = await get_settings_from_hive(acc_name, nodes)
    return PodpingSettings.parse_obj(settings_dict)


async def check_hive_node(acc_name: str, node: str):
    """Checks a specific Hive node for allowed accounts and
    sending a custom_json (using nobroadcast so doesn't write to chain)"""
    start = timer()
    try:
        hive: beem.Hive = beem.Hive(node=[node], nobroadcast=True)
        master_account = Account(acc_name, blockchain_instance=hive, lazy=True)
        allowed = set(master_account.get_following())
        elapsed = timer() - start
        logging.info(f"Hive Node: {node} - Time: {elapsed}")
        return node, elapsed
    except Exception as ex:
        logging.warning(f"Error: {ex}")
        return node, False


async def check_all_hive_nodes(acc_name: str = "podping") -> bool:
    """Checks every node in the Hive node list"""
    nodelist = NodeList()
    nodelist.update_nodes()
    nodes = nodelist.get_hive_nodes()
    nodes.append("https://api.ha.deathwig.me")
    # nodes = Config.podping_settings.main_nodes
    tasks = []
    for node in nodes:
        task = asyncio.create_task(check_hive_node(acc_name, node))
        tasks.append(task)

    answer = await asyncio.gather(*tasks)
    print(answer)
    # start = timer()
    # h = beem.Hive(node=node)
    # print(h)
    # master_account = Account(acc_name, blockchain_instance=h, lazy=True)
    # allowed = set(master_account.get_following())
    # print(allowed)
    # print(timer() - start)
    return True

"""
[
    ("https://api.deathwing.me", 0.858151393),
    ("https://api.pharesim.me", 0.7440138119999986),
    ("https://hived.emre.sh", 0.6555190240000002),
    ("https://rpc.ausbit.dev", 0.6370696890000005),
    ("https://rpc.ecency.com", 0.8608797330000009),
    ("https://hive.roelandp.nl", 0.8810059010000018),
    ("https://hived.privex.io", 1.3901671380000025),
    ("https://api.hive.blog", 0.8823300690000018),
    ("https://api.openhive.network", 1.2214132029999973),
    ("https://api.c0ff33a.uk", 7.723842510000001),
    ("https://anyx.io", 1.3463495069999993),
    ("https://techcoderx.com", 3.2101372240000003),
    ("https://api.ha.deathwig.me", False),
]
"""

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

    answer = asyncio.run(check_all_hive_nodes())


if __name__ == "__main__":
    run()

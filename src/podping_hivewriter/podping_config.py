import asyncio
import json
import logging
from timeit import default_timer as timer
from typing import Optional, Set, Tuple

import aiohttp
import beem
from beem import nodelist
from beem.account import Account
from beem.nodelist import NodeList
from beem.transactionbuilder import TransactionBuilder
from beembase import operations

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


async def check_hive_node(acc_name: str, node: str) -> Tuple[str, float]:
    """Checks a specific Hive node for allowed accounts"""
    start = timer()
    session = aiohttp.ClientSession()
    allowed = set()
    try:
        data = {
            "jsonrpc": "2.0",
            "method": "condenser_api.get_following",
            "params": [acc_name, None, "blog", 10],
            "id": 1,
        }
        async with session.post(node, data=json.dumps(data)) as response:
            answer = await response.json()
        await session.close()
        # response = requests.post(node, data=json.dumps(data))
        # answer = response.json()
        for ans in answer.get("result"):
            allowed.add(ans.get("following"))

        elapsed = timer() - start
        logging.info(f"Hive Node: {node} - Time: {elapsed}")
        return node, elapsed
    except Exception as ex:
        logging.warning(f"Node: {node} - Error: {ex}")
        return node, False
    finally:
        await session.close()


async def test_send_custom_json(acc_name: str, node: str) -> Tuple[str, float]:
    """Builds but doesn't send a custom_json not async."""
    start = timer()
    try:
        hive = beem.Hive(node=node, nobroadcast=True, wif=Config.posting_key)
        data = {"something": "here"}
        tx = hive.custom_json(
            id="podping-testing",
            json_data=data,
            required_posting_auths=[Config.server_account],
        )
    except Exception as ex:
        logging.warning(f"Node: {node} - Error: {ex}")
        return node, False
    elapsed = timer() - start
    logging.info(f"Node: {node} - Elapsed: {elapsed}")

    return node, elapsed


async def get_time_sorted_node_list(acc_name: str = None) -> Tuple[str, ...]:
    """Retuns a list of configured nodes sorted by response time for
    the get_following API call"""
    if not acc_name:
        acc_name = Config.podping_settings.control_account
    nodes = Config.nodes_in_use
    tasks = []
    for node in nodes:
        task = asyncio.create_task(check_hive_node(acc_name, node))
        tasks.append(task)

    answer = await asyncio.gather(*tasks)
    answer.sort(key=lambda a: a[1])
    node_list = []
    for node, time in answer:
        node_list.append(node)

    return tuple(node_list)


async def check_all_hive_nodes(acc_name: str = "podping") -> bool:
    """Checks every node in the Hive node list"""
    nodelist = NodeList()
    nodelist.update_nodes()
    nodes = nodelist.get_hive_nodes()

    print("Nodes:")
    print(nodes)
    print("--------------------")

    nodes.append("https://api.ha.deathwing.me")
    tasks_allowed = []
    for node in nodes:
        task = asyncio.create_task(check_hive_node(acc_name, node))
        tasks_allowed.append(task)

    answer = await asyncio.gather(*tasks_allowed)
    answer.sort(key=lambda a: a[1])
    print(answer)

    new_nodes = []
    for node, t in answer:
        new_nodes.append(node)

    print("Sorted Nodes:")
    print(json.dumps(new_nodes))
    print("--------------------")

    tasks_custom = []
    for node in nodes:
        task = asyncio.create_task(test_send_custom_json(acc_name, node))
        tasks_custom.append(task)
    answer2 = await asyncio.gather(*tasks_custom)
    answer2.sort(key=lambda a: a[1])
    print(answer2)


    new_nodes = []
    for node, t in answer2:
        new_nodes.append(node)

    print("Sorted Nodes:")
    print(json.dumps(new_nodes))
    print("--------------------")


    return True


def run():
    logging.basicConfig(
        level=logging.INFO,
        format=f"%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s",
    )

    start = timer()
    # Settings must always come from Main Hive nodes, not Test.
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

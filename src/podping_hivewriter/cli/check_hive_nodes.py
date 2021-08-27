import asyncio
import json
import logging
from timeit import default_timer as timer
from typing import Tuple

import aiohttp
import beem
from beem.nodelist import NodeList
from podping_hivewriter.config import Config
from podping_hivewriter.podping_settings import get_settings_from_hive


# TODO: This file is broken and hasn't been used in a very long time.
#  Might migrate it to the main CLI


async def get_node_latency(acc_name: str, node: str) -> Tuple[str, float]:
    """Checks a specific Hive node for allowed accounts"""
    async with aiohttp.ClientSession() as session:
        try:
            data = {
                "jsonrpc": "2.0",
                "method": "condenser_api.get_following",
                "params": [acc_name, None, "blog", 10],
                "id": 1,
            }
            start = timer()
            async with session.post(node, json=data) as _:
                pass
            elapsed = timer() - start
            logging.info(f"Hive Node: {node} - Time: {elapsed}")
            return node, elapsed
        except Exception as ex:
            logging.warning(f"Node: {node} - Error: {ex}")
            return node, False


async def test_send_custom_json(node: str) -> Tuple[str, float]:
    """Builds but doesn't send a custom_json not async."""
    try:
        hive = beem.Hive(node=node, nobroadcast=True, wif=Config.posting_keys)
        data = {"something": "here"}
        start = timer()
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
        task = asyncio.create_task(get_node_latency(acc_name, node))
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
    tasks_allowed = [get_node_latency(acc_name, node) for node in nodes]

    answer = await asyncio.gather(*tasks_allowed)
    answer.sort(key=lambda a: a[1])
    print(answer)

    new_nodes = [node for node, _ in answer]

    print("Sorted Nodes:")
    print(json.dumps(new_nodes))
    print("--------------------")

    tasks_custom = [test_send_custom_json(node) for node in nodes]
    answer2 = await asyncio.gather(*tasks_custom)
    answer2.sort(key=lambda a: a[1])
    print(answer2)

    new_nodes = [node for node, _ in answer2]

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
    podping_settings = asyncio.run(get_settings_from_hive("podping"))

    logging.info(f"Took {timer() - start:0.2}s to fetch settings")
    if podping_settings:
        logging.info(json.dumps(podping_settings, indent=2))
    else:
        logging.warning("no settings found")

    answer = asyncio.run(check_all_hive_nodes())


if __name__ == "__main__":
    run()

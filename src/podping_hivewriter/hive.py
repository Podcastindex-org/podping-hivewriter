import asyncio
import itertools
import logging
import os
from timeit import default_timer as timer
from typing import List, Optional, Set

import backoff
from lighthive.client import Client
from lighthive.exceptions import RPCNodeException

from podping_hivewriter.async_wrapper import sync_to_async


def get_client(
    posting_keys: Optional[List[str]] = None,
    nodes=None,
    connect_timeout=3,
    read_timeout=30,
    loglevel=logging.ERROR,
    chain=None,
    automatic_node_selection=False,
    api_type="condenser_api",
) -> Client:
    try:
        if os.getenv("PODPING_TESTNET", "False").lower() in (
            "true",
            "1",
            "t",
        ):
            nodes = [os.getenv("PODPING_TESTNET_NODE")]
            chain = {"chain_id": os.getenv("PODPING_TESTNET_CHAINID")}
        else:
            nodes = [
                "https://api.hive.blog",
                "https://api.deathwing.me",
                "https://hive-api.arcange.eu",
                "https://api.openhive.network",
                "https://api.hive.blue",
            ]
        client = Client(
            keys=posting_keys,
            nodes=nodes,
            connect_timeout=connect_timeout,
            read_timeout=read_timeout,
            loglevel=loglevel,
            chain=chain,
            automatic_node_selection=automatic_node_selection,
            backoff_mode=backoff.fibo,
            backoff_max_tries=3,
            load_balance_nodes=True,
            circuit_breaker=True,
        )
        return client(api_type)
    except Exception as ex:
        raise ex


def get_allowed_accounts(
    client: Client = None, account_name: str = "podping"
) -> Set[str]:
    """get a list of all accounts allowed to post by acc_name (podping)
    and only react to these accounts"""

    if not client:
        client = get_client()

    for _ in itertools.repeat(None):
        try:
            master_account = client.account(account_name)
            return set(master_account.following())
        except Exception as e:
            logging.warning(f"Unable to get account followers: {e} - retrying")


async def listen_for_custom_json_operations(
    condenser_api_client: Client, start_block: int
):
    current_block = start_block
    if not current_block:
        current_block = condenser_api_client.get_dynamic_global_properties()[
            "head_block_number"
        ]
    block_client = get_client(automatic_node_selection=False, api_type="block_api")
    async_get_block = sync_to_async(block_client.get_block, thread_sensitive=False)
    async_get_dynamic_global_properties = sync_to_async(
        condenser_api_client.get_dynamic_global_properties, thread_sensitive=False
    )
    while True:
        start_time = timer()
        try:
            head_block = (await async_get_dynamic_global_properties())[
                "head_block_number"
            ]
            while (head_block - current_block) > 0:
                try:
                    block = await async_get_block({"block_num": current_block})
                    for op in (
                        (trx_id, op)
                        for trx_id, transaction in enumerate(
                            block["block"]["transactions"]
                        )
                        for op in transaction["operations"]
                    ):
                        if op[1]["type"] == "custom_json_operation":
                            yield {
                                "block": current_block,
                                "timestamp": block["block"]["timestamp"],
                                "trx_id": op[0],
                                "op": [
                                    "custom_json",
                                    op[1]["value"],
                                ],
                            }
                    current_block += 1
                    head_block = (await async_get_dynamic_global_properties())[
                        "head_block_number"
                    ]
                except RPCNodeException as e:
                    logging.warning(f"Hive API error {e}")

            end_time = timer()
            sleep_time = 3 - (end_time - start_time)
            if sleep_time > 0 and (head_block - current_block) <= 0:
                await asyncio.sleep(sleep_time)
        except RPCNodeException as e:
            logging.warning(f"Hive API error {e}")

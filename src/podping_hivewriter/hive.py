import asyncio
import itertools
import json
import logging
import os
from random import shuffle
from timeit import default_timer as timer
from typing import List, Optional, Set

import backoff
from lighthive.client import Client
from lighthive.exceptions import RPCNodeException
from podping_schemas.org.podcastindex.podping.hivewriter.podping_hive_transaction import (
    PodpingHiveTransaction,
)
from podping_schemas.org.podcastindex.podping.podping import Podping

from podping_hivewriter.async_wrapper import sync_to_async
from podping_hivewriter.models.internal_podping import CURRENT_PODPING_VERSION
from podping_hivewriter.models.medium import str_medium_map
from podping_hivewriter.models.reason import str_reason_map


def get_client(
    posting_keys: Optional[List[str]] = None,
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
                "https://anyx.io",
                "https://rpc.ecency.com",
                "https://hived.emre.sh",
                "https://rpc.ausbit.dev",
                "https://rpc.podping.org",
            ]
            shuffle(nodes)
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
        except KeyError:
            logging.warning(f"Unable to get account followers - retrying")
        except Exception as e:
            logging.warning(f"Unable to get account followers: {e} - retrying")
            client.circuit_breaker_cache[client.current_node] = True
            logging.warning(
                "Ignoring node %s for %d seconds",
                client.current_node,
                client.circuit_breaker_ttl,
            )
            client.next_node()


async def get_relevant_transactions_from_blockchain(
    condenser_api_client: Client, start_block: int, operation_id: str = None
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
                    while True:
                        try:
                            block = await async_get_block({"block_num": current_block})
                            for tx_num, transaction in enumerate(
                                block["block"]["transactions"]
                            ):
                                tx_id = block["block"]["transaction_ids"][tx_num]
                                podpings = []
                                for op in transaction["operations"]:
                                    if op["type"] == "custom_json_operation" and (
                                        not operation_id
                                        or op["value"]["id"] == operation_id
                                    ):
                                        data = json.loads(op["value"]["json"])
                                        if (
                                            "iris" in data
                                            and "version" in data
                                            and data["version"]
                                            == CURRENT_PODPING_VERSION
                                        ):
                                            podpings.append(
                                                Podping(
                                                    medium=str_medium_map[
                                                        data["medium"]
                                                    ],
                                                    reason=str_reason_map[
                                                        data["reason"]
                                                    ],
                                                    iris=data["iris"],
                                                    timestampNs=data["timestampNs"],
                                                    sessionId=data["sessionId"],
                                                )
                                            )
                                if len(podpings):
                                    yield PodpingHiveTransaction(
                                        podpings=podpings,
                                        hiveTxId=tx_id,
                                        hiveBlockNum=current_block,
                                    )
                            break
                        except KeyError as e:
                            pass
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

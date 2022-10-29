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
from lighthive.helpers.event_listener import EventListener
from podping_schemas.org.podcastindex.podping.hivewriter.podping_hive_transaction import (
    PodpingHiveTransaction,
)

from podping_hivewriter.async_wrapper import sync_to_async
from podping_hivewriter.models.medium import str_medium_map
from podping_hivewriter.models.reason import str_reason_map


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


async def get_relevant_transactions_from_blockchain(
    client: Client, start_block: int, filter_by: dict = None
):
    event_listener = EventListener(client, "head", start_block=start_block)
    _on = sync_to_async(event_listener.on, thread_sensitive=False)
    async for post in _on("custom_json", filter_by=filter_by):
        data = json.loads(post["op"][1]["json"])
        if "iris" in data:
            yield PodpingHiveTransaction(
                medium=str_medium_map[data["medium"]],
                reason=str_reason_map[data["reason"]],
                iris=data["iris"],
                hiveTxId=post["trx_id"],
                hiveBlockNum=post["block"],
            )

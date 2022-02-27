import asyncio
import logging
from timeit import default_timer as timer
from typing import List, Optional, Set

from lighthive.client import Client

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
        client = Client(
            keys=posting_keys,
            nodes=nodes,
            connect_timeout=connect_timeout,
            read_timeout=read_timeout,
            loglevel=loglevel,
            chain=chain,
            automatic_node_selection=automatic_node_selection,
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

    master_account = client.account(account_name)
    return set(master_account.following())


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
        head_block = (await async_get_dynamic_global_properties())["head_block_number"]
        while (head_block - current_block) > 0:
            block = await async_get_block({"block_num": current_block})
            for op in (
                (trx_id, op)
                for trx_id, transaction in enumerate(block["block"]["transactions"])
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

        end_time = timer()
        sleep_time = 3 - (end_time - start_time)
        if sleep_time > 0 and (head_block - current_block) <= 0:
            await asyncio.sleep(sleep_time)

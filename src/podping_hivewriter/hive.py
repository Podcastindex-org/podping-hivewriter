import logging
from itertools import cycle
from typing import List, Optional

from lighthive.client import Client
from lighthive.node_picker import compare_nodes




def get_client(
    posting_keys: Optional[List[str]] = None,
    nobroadcast: Optional[bool] = False,
    nodes=None,
    connect_timeout=3,
    read_timeout=30,
    loglevel=logging.ERROR,
    chain=None,
) -> Client:
    try:
        client = Client(
            keys=posting_keys,
            nodes=nodes,
            connect_timeout=connect_timeout,
            read_timeout=read_timeout,
            loglevel=loglevel,
            chain=chain,
            automatic_node_selection=False,
        )
        return client
    except Exception as ex:
        raise ex


async def get_automatic_node_selection(client: Client = None) -> Client:
    """Use the automatic async feature to find the fastests API"""
    if not client:
        client = Client()
    client._node_list = await compare_nodes(nodes=client.nodes, logger=client.logger)
    client.node_list = cycle(client._node_list)
    client.next_node()
    logging.info(f"Lighthive Fastest: {client.current_node}")
    return client

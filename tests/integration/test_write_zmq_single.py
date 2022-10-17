import asyncio
import json
import os
import random
import uuid
from ipaddress import IPv4Address
from platform import python_version as pv

import pytest
from plexo.ganglion.tcp_pair import GanglionZmqTcpPair
from plexo.plexus import Plexus

from podping_hivewriter.constants import LIVETEST_OPERATION_ID
from podping_hivewriter.hive import get_client, listen_for_custom_json_operations
from podping_hivewriter.models.hive_operation_id import HiveOperationId
from podping_hivewriter.models.medium import mediums, str_medium_map
from podping_hivewriter.models.reason import reasons, str_reason_map
from podping_hivewriter.neuron import (
    podping_hive_transaction_neuron,
    podping_write_neuron,
)
from podping_hivewriter.podping_hivewriter import PodpingHivewriter
from podping_hivewriter.podping_settings_manager import PodpingSettingsManager
from podping_hivewriter.schema.podping_hive_transaction import PodpingHiveTransaction
from podping_hivewriter.schema.podping_write import PodpingWrite


@pytest.mark.asyncio
@pytest.mark.timeout(600)
@pytest.mark.slow
async def test_write_zmq_single(event_loop):
    settings_manager = PodpingSettingsManager(ignore_updates=True)

    client = get_client()

    session_uuid = uuid.uuid4()
    session_uuid_str = str(session_uuid)

    test_name = "zmq_single"
    iri = f"https://example.com?t={test_name}&v={pv()}&s={session_uuid_str}"

    medium = str_medium_map[random.sample(sorted(mediums), 1)[0]]
    reason = str_reason_map[random.sample(sorted(reasons), 1)[0]]

    default_hive_operation_id = HiveOperationId(LIVETEST_OPERATION_ID, medium, reason)
    default_hive_operation_id_str = str(default_hive_operation_id)

    async def get_iri_from_blockchain(start_block: int):
        async for post in listen_for_custom_json_operations(client, start_block):
            if post["op"][1]["id"] == default_hive_operation_id_str:
                data = json.loads(post["op"][1]["json"])
                if "iris" in data and len(data["iris"]) == 1:
                    iri = data["iris"][0]
                    # Only look for IRIs from current session
                    if iri.endswith(session_uuid_str):
                        yield iri

    tx_queue: asyncio.Queue[PodpingHiveTransaction] = asyncio.Queue()

    async def _podping_hive_transaction_reaction(
        transaction: PodpingHiveTransaction, _, _2
    ):
        await tx_queue.put(transaction)

    host = "127.0.0.1"
    port = 9979
    podping_hivewriter = PodpingHivewriter(
        os.environ["PODPING_HIVE_ACCOUNT"],
        [os.environ["PODPING_HIVE_POSTING_KEY"]],
        settings_manager,
        medium=medium,
        reason=reason,
        listen_ip=host,
        listen_port=port,
        resource_test=False,
        operation_id=LIVETEST_OPERATION_ID,
    )
    await podping_hivewriter.wait_startup()

    tcp_pair_ganglion = GanglionZmqTcpPair(
        peer=(IPv4Address(host), port),
        relevant_neurons=(
            podping_hive_transaction_neuron,
            podping_write_neuron,
        ),
    )
    plexus = Plexus(ganglia=(tcp_pair_ganglion,))
    await plexus.adapt(
        podping_hive_transaction_neuron, reactants=(_podping_hive_transaction_reaction,)
    )
    await plexus.adapt(podping_write_neuron)

    podping_write = PodpingWrite(medium=medium, reason=reason, iri=iri)

    current_block = client.get_dynamic_global_properties()["head_block_number"]

    await plexus.transmit(podping_write)

    iri_found = False

    async for stream_iri in get_iri_from_blockchain(current_block):
        if stream_iri == iri:
            iri_found = True
            break

    assert iri_found
    podping_hivewriter.close()

    tx = await tx_queue.get()
    assert tx.medium == medium
    assert tx.reason == reason
    assert iri in tx.iris
    assert tx.hiveTxId is not None
    assert tx.hiveBlockNum is not None

# Not to be run with automated tests.
# Special use test for sending large amounts of traffic to a mirror/test net
import asyncio
import json
import logging
import os
import random
import uuid
from ipaddress import IPv4Address
from platform import python_version as pv
from random import randint

import pytest
import zmq
import zmq.asyncio
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

LOOP_COUNT = 100_000

@pytest.mark.asyncio
@pytest.mark.timeout(3600)
@pytest.mark.slow
async def test_write_zmq_multiple(event_loop):
    os.environ["PODPING_TESTNET"] = "true"
    os.environ["PODPING_TESTNET_NODE"] = "https://api.fake.openhive.network"
    os.environ[
        "PODPING_TESTNET_CHAINID"
    ] = "4200000000000000000000000000000000000000000000000000000000000000"
    settings_manager = PodpingSettingsManager(ignore_updates=True)

    client = get_client()

    session_uuid = uuid.uuid4()
    session_uuid_str = str(session_uuid)

    def get_test_iris(num_iris: int = 1_000):
        i = 0
        test_name = "zmq_multiple_flood_test"
        python_version = pv()
        while i < num_iris:
            yield (
                f"https://example.com?t={test_name}"
                f"&i={i}&v={python_version}&s={session_uuid_str}"
            )
            i += 1

    medium = str_medium_map[random.sample(sorted(mediums), 1)[0]]
    reason = str_reason_map[random.sample(sorted(reasons), 1)[0]]

    default_hive_operation_id = HiveOperationId(LIVETEST_OPERATION_ID, medium, reason)
    default_hive_operation_id_str = str(default_hive_operation_id)

    tx_queue: asyncio.Queue[PodpingHiveTransaction] = asyncio.Queue()

    async def _podping_hive_transaction_reaction(
        transaction: PodpingHiveTransaction, _, _2
    ):
        await tx_queue.put(transaction)

    host = "127.0.0.1"
    port = 9978 + randint(1, 10000)
    podping_hivewriter = PodpingHivewriter(
        os.environ["PODPING_HIVE_ACCOUNT"],
        [os.environ["PODPING_HIVE_POSTING_KEY"]],
        settings_manager,
        # medium=medium,
        # reason=reason,
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
    # TODO: confirm we receive a valid transaction after success
    await plexus.adapt(
        podping_hive_transaction_neuron, reactants=(_podping_hive_transaction_reaction,)
    )
    await plexus.adapt(podping_write_neuron)

    for iri in get_test_iris(LOOP_COUNT):
        medium = str_medium_map[random.sample(sorted(mediums), 1)[0]]
        reason = str_reason_map[random.sample(sorted(reasons), 1)[0]]
        podping_write = PodpingWrite(medium=medium, reason=reason, iri=iri)
        await asyncio.sleep(0.01 * randint(30, 100))
        await plexus.transmit(podping_write)

    # Sleep until all items in the queue are done processing
    num_iris_processing = await podping_hivewriter.num_operations_in_queue()
    while num_iris_processing > 0:
        await asyncio.sleep(0.01 * randint(0, 30))
        num_iris_processing = await podping_hivewriter.num_operations_in_queue()

    podping_hivewriter.close()
    assert True

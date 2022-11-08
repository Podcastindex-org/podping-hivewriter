import asyncio
import os
import random
import uuid
from ipaddress import IPv4Address
from platform import python_version as pv

import pytest
from plexo.ganglion.tcp_pair import GanglionZmqTcpPair
from plexo.plexus import Plexus
from podping_schemas.org.podcastindex.podping.hivewriter.podping_hive_transaction import (
    PodpingHiveTransaction,
)
from podping_schemas.org.podcastindex.podping.hivewriter.podping_write import (
    PodpingWrite,
)

from podping_hivewriter.constants import LIVETEST_OPERATION_ID
from podping_hivewriter.hive import get_relevant_transactions_from_blockchain
from podping_hivewriter.models.medium import mediums
from podping_hivewriter.models.reason import reasons
from podping_hivewriter.neuron import (
    podping_hive_transaction_neuron,
    podping_write_neuron,
)
from podping_hivewriter.podping_hivewriter import PodpingHivewriter
from podping_hivewriter.podping_settings_manager import PodpingSettingsManager


@pytest.mark.asyncio
@pytest.mark.timeout(900)
@pytest.mark.slow
async def test_write_zmq_simulcast(lighthive_client):
    """This test forces 7 separate posts to ensure we retry after exceeding the
    limit of posts per block (5)"""
    settings_manager = PodpingSettingsManager(ignore_updates=True)

    session_uuid = uuid.uuid4()
    session_uuid_str = str(session_uuid)

    # Ensure hive env vars are set from .env.test file or this will fail
    python_version = pv()
    test_iris = {
        (
            f"https://example.com?t=zmq_simulcast_{n}"
            f"&v={python_version}&s={session_uuid_str}",
            random.sample(sorted(mediums), 1)[0],
            random.sample(sorted(reasons), 1)[0],
        )
        for n in range(7)
    }
    tx_queue: asyncio.Queue[PodpingHiveTransaction] = asyncio.Queue()

    async def _podping_hive_transaction_reaction(
        transaction: PodpingHiveTransaction, _, _2
    ):
        await tx_queue.put(transaction)

    host = "127.0.0.1"
    port = 9979
    with PodpingHivewriter(
        os.environ["PODPING_HIVE_ACCOUNT"],
        [os.environ["PODPING_HIVE_POSTING_KEY"]],
        settings_manager,
        listen_ip=host,
        listen_port=port,
        resource_test=False,
        status=False,
        operation_id=LIVETEST_OPERATION_ID,
    ) as podping_hivewriter:
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
            podping_hive_transaction_neuron,
            reactants=(_podping_hive_transaction_reaction,),
        )
        await plexus.adapt(podping_write_neuron)

        op_period = settings_manager._settings.hive_operation_period

        current_block = lighthive_client.get_dynamic_global_properties()[
            "head_block_number"
        ]

        for iri, medium, reason in test_iris:
            podping_write = PodpingWrite(medium=medium, reason=reason, iri=iri)
            await plexus.transmit(podping_write)

        # Sleep until all items in the queue are done processing
        num_iris_processing = await podping_hivewriter.num_operations_in_queue()
        while num_iris_processing > 0:
            await asyncio.sleep(op_period)
            num_iris_processing = await podping_hivewriter.num_operations_in_queue()

    answer_iris = set()
    async for tx in get_relevant_transactions_from_blockchain(
        lighthive_client, current_block
    ):
        for iri in tx.iris:
            if iri.endswith(session_uuid_str):
                answer_iris.add((iri, tx.medium, tx.reason))
        assert tx.hiveTxId is not None
        assert tx.hiveBlockNum is not None

        if len(answer_iris) == len(test_iris):
            break

    assert answer_iris == test_iris

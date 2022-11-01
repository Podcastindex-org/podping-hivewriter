import asyncio
import os
import random
import uuid
from ipaddress import IPv4Address
from platform import python_version as pv
from random import randint

import pytest
from plexo.ganglion.tcp_pair import GanglionZmqTcpPair
from plexo.plexus import Plexus

from podping_hivewriter.constants import LIVETEST_OPERATION_ID
from podping_hivewriter.hive import get_relevant_transactions_from_blockchain
from podping_hivewriter.models.hive_operation_id import HiveOperationId
from podping_hivewriter.models.medium import mediums, str_medium_map
from podping_hivewriter.models.reason import reasons, str_reason_map
from podping_hivewriter.neuron import (
    podping_hive_transaction_neuron,
    podping_write_neuron,
)
from podping_hivewriter.podping_hivewriter import PodpingHivewriter
from podping_hivewriter.podping_settings_manager import PodpingSettingsManager
from podping_schemas.org.podcastindex.podping.hivewriter.podping_hive_transaction import (
    PodpingHiveTransaction,
)
from podping_schemas.org.podcastindex.podping.hivewriter.podping_write import (
    PodpingWrite,
)


@pytest.mark.asyncio
@pytest.mark.timeout(600)
@pytest.mark.slow
async def test_write_send_podping_multiple(lighthive_client):
    settings_manager = PodpingSettingsManager(ignore_updates=True)

    session_uuid = uuid.uuid4()
    session_uuid_str = str(session_uuid)

    num_iris = randint(2, 25)
    test_name = "send_podping_multiple"
    python_version = pv()
    test_iris = {
        f"https://example.com?t={test_name}&i={i}&v={python_version}&s={session_uuid_str}"
        for i in range(num_iris)
    }

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
    port = 9979
    with PodpingHivewriter(
        os.environ["PODPING_HIVE_ACCOUNT"],
        [os.environ["PODPING_HIVE_POSTING_KEY"]],
        settings_manager,
        medium=medium,
        reason=reason,
        listen_ip=host,
        listen_port=port,
        resource_test=False,
        operation_id=LIVETEST_OPERATION_ID,
        zmq_service=False,
    ) as podping_hivewriter:
        await podping_hivewriter.wait_startup()

        await podping_hivewriter.plexus.adapt(
            podping_hive_transaction_neuron,
            reactants=(_podping_hive_transaction_reaction,),
        )

        op_period = settings_manager._settings.hive_operation_period

        current_block = lighthive_client.get_dynamic_global_properties()[
            "head_block_number"
        ]

        for iri in test_iris:
            await podping_hivewriter.send_podping(medium=medium, reason=reason, iri=iri)

        # Sleep until all items in the queue are done processing
        num_iris_processing = await podping_hivewriter.num_operations_in_queue()
        while num_iris_processing > 0:
            await asyncio.sleep(op_period)
            num_iris_processing = await podping_hivewriter.num_operations_in_queue()

        answer_iris = set()
        async for tx in get_relevant_transactions_from_blockchain(
            lighthive_client, current_block, {"id": default_hive_operation_id_str}
        ):
            assert tx.medium == medium
            assert tx.reason == reason

            for iri in tx.iris:
                if iri.endswith(session_uuid_str):
                    answer_iris.add(iri)

            if len(answer_iris) == len(test_iris):
                break

    assert answer_iris == test_iris

    tx = await tx_queue.get()

    assert tx.medium == medium
    assert tx.reason == reason
    assert test_iris == set(tx.iris)
    assert tx.hiveTxId is not None
    assert tx.hiveBlockNum is not None

import asyncio
import os
import random
import uuid
from ipaddress import IPv4Address
from platform import python_version as pv

import pytest
from plexo.ganglion.tcp_pair import GanglionZmqTcpPair
from plexo.plexus import Plexus

from podping_hivewriter.constants import LIVETEST_OPERATION_ID
from podping_hivewriter.hive import get_relevant_transactions_from_blockchain
from podping_hivewriter.models.hive_operation_id import HiveOperationId
from podping_hivewriter.models.medium import medium_strings, str_medium_map
from podping_hivewriter.models.reason import reason_strings, str_reason_map
from podping_hivewriter.neuron import (
    podping_hive_transaction_neuron,
    podping_write_neuron,
)
from podping_hivewriter.podping_hivewriter import PodpingHivewriter
from podping_hivewriter.podping_settings_manager import PodpingSettingsManager
from podping_schemas.org.podcastindex.podping.hivewriter.podping_hive_transaction import (
    PodpingHiveTransaction,
)
from podping_schemas.org.podcastindex.podping.podping_write import (
    PodpingWrite,
)


@pytest.mark.asyncio
@pytest.mark.timeout(600)
@pytest.mark.slow
async def test_write_zmq_single(lighthive_client):
    settings_manager = PodpingSettingsManager(ignore_updates=True)

    session_uuid = uuid.uuid4()
    session_uuid_str = str(session_uuid)

    test_name = "zmq_single"
    iri = f"https://example.com?t={test_name}&v={pv()}&s={session_uuid_str}"

    medium = str_medium_map[random.sample(sorted(medium_strings), 1)[0]]
    reason = str_reason_map[random.sample(sorted(reason_strings), 1)[0]]

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

        podping_write = PodpingWrite(medium=medium, reason=reason, iri=iri)

        await plexus.transmit(podping_write)

        iri_found = False

        tx = await tx_queue.get()

        assert len(tx.podpings) == 1
        assert tx.podpings[0].medium == medium
        assert tx.podpings[0].reason == reason
        assert iri in tx.podpings[0].iris
        assert tx.hiveTxId is not None
        assert tx.hiveBlockNum is not None

        async for tx in get_relevant_transactions_from_blockchain(
            lighthive_client, tx.hiveBlockNum, default_hive_operation_id_str
        ):
            assert len(tx.podpings) == 1

            if iri in tx.podpings[0].iris:
                iri_found = True
                assert tx.podpings[0].medium == medium
                assert tx.podpings[0].reason == reason
                break

    assert iri_found

    plexus.close()

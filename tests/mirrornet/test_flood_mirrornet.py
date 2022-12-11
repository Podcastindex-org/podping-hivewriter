import asyncio
import logging
import os
import random
import uuid
from platform import python_version as pv
from random import randint

import pytest
from podping_schemas.org.podcastindex.podping.hivewriter.podping_hive_transaction import (
    PodpingHiveTransaction,
)
from podping_schemas.org.podcastindex.podping.podping_medium import PodpingMedium
from podping_schemas.org.podcastindex.podping.podping_reason import PodpingReason

from podping_hivewriter.constants import LIVETEST_OPERATION_ID
from podping_hivewriter.hive import get_relevant_transactions_from_blockchain
from podping_hivewriter.models.medium import mediums
from podping_hivewriter.models.reason import reasons
from podping_hivewriter.neuron import podping_hive_transaction_neuron
from podping_hivewriter.podping_hivewriter import PodpingHivewriter
from podping_hivewriter.podping_settings_manager import PodpingSettingsManager

TESTNET_NUM_IRIS = 1_000


@pytest.mark.asyncio
@pytest.mark.timeout(60000)
@pytest.mark.slow
async def test_write_send_podping_multiple_mirrornet(lighthive_client):
    os.environ["PODPING_TESTNET"] = "true"
    os.environ["PODPING_TESTNET_NODE"] = "https://api.fake.openhive.network"
    os.environ[
        "PODPING_TESTNET_CHAINID"
    ] = "4200000000000000000000000000000000000000000000000000000000000000"

    settings_manager = PodpingSettingsManager(ignore_updates=True)
    # settings_manager._settings.hive_operation_period = 60

    session_uuid = uuid.uuid4()
    session_uuid_str = str(session_uuid)

    def get_test_iris(num_iris: int = TESTNET_NUM_IRIS):
        i = 0
        python_version = pv()
        test_name = "send_testnet_flood"
        python_version = pv()
        while i < num_iris:
            yield (
                f"https://example.com?t={test_name}"
                f"&i_r={round(i,-2)}&i={i}&v={python_version}&s={session_uuid_str}"
            )
            i += 1

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
        # medium=medium,
        # reason=reason,
        listen_ip=host,
        listen_port=port,
        resource_test=False,
        status=False,
        operation_id=LIVETEST_OPERATION_ID,
        zmq_service=False,
    ) as podping_hivewriter:
        await podping_hivewriter.wait_startup()

        await podping_hivewriter.plexus.adapt(
            podping_hive_transaction_neuron,
            reactants=(_podping_hive_transaction_reaction,),
        )

        op_period = settings_manager._settings.hive_operation_period

        for iri in get_test_iris():
            medium: PodpingMedium = random.sample(sorted(mediums), 1)[0]
            reason: PodpingReason = random.sample(sorted(reasons), 1)[0]
            await podping_hivewriter.send_podping(medium=medium, reason=reason, iri=iri)
            await asyncio.sleep(0.0001 * randint(3, 50))

        await asyncio.sleep(op_period)
        # Sleep until all items in the queue are done processing
        num_iris_processing = await podping_hivewriter.num_operations_in_queue()
        while num_iris_processing > 0:
            logging.info(f"Processing: {num_iris_processing}")
            await asyncio.sleep(op_period)
            num_iris_processing = await podping_hivewriter.num_operations_in_queue()

        txs = []
        while not tx_queue.empty():
            txs.append(await tx_queue.get())

        start_block = min(tx.hiveBlockNum for tx in txs)
        logging.info(f"Startblock : {start_block}")
        answer_iris = set()
        async for tx in get_relevant_transactions_from_blockchain(
            lighthive_client, start_block
        ):
            for podping in tx.podpings:
                for iri in podping.iris:
                    if iri.endswith(session_uuid_str):
                        answer_iris.add(iri)
            if TESTNET_NUM_IRIS == len(answer_iris):
                break
    assert TESTNET_NUM_IRIS == len(answer_iris)

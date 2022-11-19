import asyncio
import os
import random
import uuid
from platform import python_version as pv

import pytest
from plexo.plexus import Plexus
from podping_schemas.org.podcastindex.podping.podping_medium import (
    PodpingMedium,
)
from podping_schemas.org.podcastindex.podping.podping_reason import (
    PodpingReason,
)

from podping_hivewriter.constants import LIVETEST_OPERATION_ID
from podping_hivewriter.hive import get_relevant_transactions_from_blockchain
from podping_hivewriter.models.hive_operation_id import HiveOperationId
from podping_hivewriter.models.medium import mediums
from podping_hivewriter.models.reason import reasons
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
async def test_write_dry_run_empty_tx(lighthive_client):
    settings_manager = PodpingSettingsManager(ignore_updates=True)

    session_uuid = uuid.uuid4()
    session_uuid_str = str(session_uuid)

    test_name = "dry_run_empty_tx"
    iri = f"https://example.com?t={test_name}&v={pv()}&s={session_uuid_str}"

    medium: PodpingMedium = random.sample(sorted(mediums), 1)[0]
    reason: PodpingReason = random.sample(sorted(reasons), 1)[0]

    tx_queue: asyncio.Queue[PodpingHiveTransaction] = asyncio.Queue()

    async def _podping_hive_transaction_reaction(
        transaction: PodpingHiveTransaction, _, _2
    ):
        await tx_queue.put(transaction)

    plexus = Plexus()
    await plexus.adapt(
        podping_hive_transaction_neuron,
        reactants=(_podping_hive_transaction_reaction,),
    )
    await plexus.adapt(podping_write_neuron)

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
        dry_run=True,
        operation_id=LIVETEST_OPERATION_ID,
        zmq_service=False,
        plexus=plexus,
    ) as podping_hivewriter:
        await podping_hivewriter.wait_startup()

        podping_write = PodpingWrite(medium=medium, reason=reason, iri=iri)

        await plexus.transmit(podping_write)

        tx = await tx_queue.get()

        assert len(tx.podpings) == 1
        assert tx.podpings[0].medium == medium
        assert tx.podpings[0].reason == reason
        assert iri in tx.podpings[0].iris
        assert tx.hiveTxId is "0"
        assert tx.hiveBlockNum is 0

    plexus.close()

# Not to be run with automated tests.
# Special use test for sending large amounts of traffic to a mirror/test net
import asyncio
import json
import logging
import os
import random
import uuid
from platform import python_version as pv
from random import randint

import pytest
import zmq
import zmq.asyncio

from podping_hivewriter.constants import LIVETEST_OPERATION_ID
from podping_hivewriter.hive import get_client, listen_for_custom_json_operations
from podping_hivewriter.models.hive_operation_id import HiveOperationId
from podping_hivewriter.models.medium import mediums, str_medium_map
from podping_hivewriter.models.reason import reasons, str_reason_map
from podping_hivewriter.podping_hivewriter import PodpingHivewriter
from podping_hivewriter.podping_settings_manager import PodpingSettingsManager


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

    def get_test_iris():
        num_iris = 100_000
        test_name = "zmq_multiple"
        python_version = pv()
        test_iris = {
            f"https://example.com?t={test_name}&i={i}&v={python_version}&s={session_uuid_str}"
            for i in range(num_iris)
        }
        return test_iris

    medium = str_medium_map[random.sample(sorted(mediums), 1)[0]]
    reason = str_reason_map[random.sample(sorted(reasons), 1)[0]]

    default_hive_operation_id = HiveOperationId(LIVETEST_OPERATION_ID, medium, reason)
    default_hive_operation_id_str = str(default_hive_operation_id)

    async def get_iri_from_blockchain(start_block: int):
        async for post in listen_for_custom_json_operations(client, start_block):
            if post["op"][1]["id"] == default_hive_operation_id_str:
                data = json.loads(post["op"][1]["json"])
                if "iris" in data:
                    for iri in data["iris"]:
                        # Only look for IRIs from current session
                        if iri.endswith(session_uuid_str):
                            yield iri

    host = "127.0.0.1"
    port = 9978 + randint(1,10000)
    podping_hivewriter = PodpingHivewriter(
        os.environ["PODPING_HIVE_ACCOUNT"],
        [os.environ["PODPING_HIVE_POSTING_KEY"]],
        settings_manager,
        medium=medium,
        reason=reason,
        listen_ip=host,
        listen_port=port,
        resource_test=True,
        operation_id=LIVETEST_OPERATION_ID,
    )
    await podping_hivewriter.wait_startup()
    context = zmq.asyncio.Context()
    socket = context.socket(zmq.REQ, io_loop=event_loop)
    socket.connect(f"tcp://{host}:{port}")

    op_period = settings_manager._settings.hive_operation_period

    test_iris = get_test_iris()
    for iri in test_iris:
        await socket.send_string(iri)
        response = await socket.recv_string()
        await asyncio.sleep(0.01 * randint(0, 30))
        assert response == "OK"

    # Sleep until all items in the queue are done processing
    num_iris_processing = await podping_hivewriter.num_operations_in_queue()
    while num_iris_processing > 0:
        await asyncio.sleep(op_period)
        num_iris_processing = await podping_hivewriter.num_operations_in_queue()
        logging.info(num_iris_processing)

    podping_hivewriter.close()

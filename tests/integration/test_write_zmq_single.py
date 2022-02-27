import json
import os
import random
import uuid
from platform import python_version as pv

import pytest
import zmq
import zmq.asyncio
from lighthive.client import Client

from podping_hivewriter.constants import LIVETEST_OPERATION_ID
from podping_hivewriter.hive import listen_for_custom_json_operations
from podping_hivewriter.models.hive_operation_id import HiveOperationId
from podping_hivewriter.models.medium import str_medium_map, mediums
from podping_hivewriter.models.reason import str_reason_map, reasons
from podping_hivewriter.podping_hivewriter import PodpingHivewriter
from podping_hivewriter.podping_settings_manager import PodpingSettingsManager


@pytest.mark.asyncio
@pytest.mark.timeout(600)
@pytest.mark.slow
async def test_write_zmq_single(event_loop):
    settings_manager = PodpingSettingsManager(ignore_updates=True)

    client = Client()

    session_uuid = uuid.uuid4()
    session_uuid_str = str(session_uuid)

    test_name = "zmq_single"
    iri = f"https://example.com?t={test_name}&v={pv()}&s={session_uuid_str}"

    medium = str_medium_map[random.sample(mediums, 1)[0]]
    reason = str_reason_map[random.sample(reasons, 1)[0]]

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
    context = zmq.asyncio.Context()
    socket = context.socket(zmq.REQ, io_loop=event_loop)
    socket.connect(f"tcp://{host}:{port}")
    current_block = client.get_dynamic_global_properties()["head_block_number"]

    await socket.send_string(iri)
    response = await socket.recv_string()

    assert response == "OK"

    iri_found = False

    async for stream_iri in get_iri_from_blockchain(current_block):
        if stream_iri == iri:
            iri_found = True
            break

    assert iri_found
    podping_hivewriter.close()

import asyncio
import json
import os
import uuid
from random import randint
from platform import python_version as pv

import pytest
import zmq
import zmq.asyncio
from lighthive.client import Client
from lighthive.helpers.event_listener import EventListener

from podping_hivewriter.async_wrapper import sync_to_async
from podping_hivewriter.constants import LIVETEST_OPERATION_ID
from podping_hivewriter.models.hive_operation_id import HiveOperationId
from podping_hivewriter.models.medium import Medium
from podping_hivewriter.models.reason import Reason
from podping_hivewriter.podping_hivewriter import PodpingHivewriter
from podping_hivewriter.podping_settings_manager import PodpingSettingsManager


@pytest.mark.asyncio
@pytest.mark.timeout(120)
@pytest.mark.slow
async def test_write_zmq_multiple_url(event_loop):
    settings_manager = PodpingSettingsManager(ignore_updates=True)

    client = Client()

    session_uuid = uuid.uuid4()
    session_uuid_str = str(session_uuid)

    num_urls = randint(2, 25)
    test_name = "zmq_multiple"
    python_version = pv()
    test_urls = {
        f"https://example.com?t={test_name}&i={i}&v={python_version}&s={session_uuid_str}"
        for i in range(num_urls)
    }

    default_hive_operation_id = HiveOperationId(
        LIVETEST_OPERATION_ID, Medium.podcast, Reason.update
    )
    default_hive_operation_id_str = str(default_hive_operation_id)

    async def get_url_from_blockchain(start_block: int):
        event_listener = EventListener(client, "head", start_block=start_block)
        _on = sync_to_async(event_listener.on, thread_sensitive=False)
        async for post in _on(
            "custom_json", filter_by={"id": default_hive_operation_id_str}
        ):
            data = json.loads(post["op"][1]["json"])
            if "urls" in data:
                for u in data["urls"]:
                    # Only look for URLs from current session
                    if u.endswith(session_uuid_str):
                        yield u

    host = "127.0.0.1"
    port = 9979
    podping_hivewriter = PodpingHivewriter(
        os.environ["PODPING_HIVE_ACCOUNT"],
        [os.environ["PODPING_HIVE_POSTING_KEY"]],
        settings_manager,
        listen_ip=host,
        listen_port=port,
        resource_test=False,
        operation_id=LIVETEST_OPERATION_ID,
    )
    await podping_hivewriter.wait_startup()
    context = zmq.asyncio.Context()
    socket = context.socket(zmq.REQ, io_loop=event_loop)
    socket.connect(f"tcp://{host}:{port}")

    op_period = settings_manager._settings.hive_operation_period

    current_block = client.get_dynamic_global_properties()["head_block_number"]

    for url in test_urls:
        await socket.send_string(url)
        response = await socket.recv_string()
        assert response == "OK"

    # Sleep until all items in the queue are done processing
    num_urls_processing = await podping_hivewriter.num_operations_in_queue()
    while num_urls_processing > 0:
        await asyncio.sleep(op_period)
        num_urls_processing = await podping_hivewriter.num_operations_in_queue()

    # Sleep to catch up because lighthive isn't async and blocks
    await asyncio.sleep(op_period * 30)

    answer_urls = set()
    async for stream_url in get_url_from_blockchain(current_block):
        answer_urls.add(stream_url)

        # If we're done, end early
        if len(answer_urls) == len(test_urls):
            break

    assert answer_urls == test_urls
    podping_hivewriter.close()

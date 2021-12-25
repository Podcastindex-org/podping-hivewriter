import asyncio
import json
import os
import uuid

import pytest
import zmq
import zmq.asyncio
from beem.blockchain import Blockchain

from podping_hivewriter.async_wrapper import sync_to_async
from podping_hivewriter.constants import LIVETEST_OPERATION_ID
from podping_hivewriter.hive import get_hive
from podping_hivewriter.podping_hivewriter import PodpingHivewriter
from podping_hivewriter.podping_settings_manager import PodpingSettingsManager


@pytest.mark.asyncio
@pytest.mark.timeout(120)
@pytest.mark.slow
async def test_write_zmq_single_url(event_loop):
    settings_manager = PodpingSettingsManager(ignore_updates=True)

    hive = await get_hive(settings_manager._settings.main_nodes)

    blockchain = Blockchain(mode="head", blockchain_instance=hive)
    start_block = blockchain.get_current_block_num()

    session_uuid = uuid.uuid4()
    session_uuid_str = str(session_uuid)

    test_name = "zmq_single"
    url = f"https://example.com?t={test_name}&s={session_uuid_str}"

    def _blockchain_stream(stop_block: int):
        # noinspection PyTypeChecker
        stream = blockchain.stream(
            opNames=["custom_json"],
            start=start_block,
            stop=stop_block,
            max_batch_size=None,
            raw_ops=False,
            only_ops=True,
            threading=False,
        )

        for post in (post for post in stream if post["id"] == LIVETEST_OPERATION_ID):
            yield post

    get_blockchain_stream = sync_to_async(_blockchain_stream, thread_sensitive=False)

    async def get_url_from_blockchain(stop_block: int):
        stream = get_blockchain_stream(stop_block)

        async for post in stream:
            data = json.loads(post["json"])
            if "urls" in data and len(data["urls"]) == 1:
                yield data["urls"][0]

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

    await socket.send_string(url)
    response = await socket.recv_string()

    assert response == "OK"

    # Sleep to catch up because beem isn't async and blocks
    await asyncio.sleep(op_period * 25)

    end_block = blockchain.get_current_block_num()

    url_found = False

    async for stream_url in get_url_from_blockchain(end_block):
        if stream_url == url:
            url_found = True
            break

    assert url_found
    podping_hivewriter.close()

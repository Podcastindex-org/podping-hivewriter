import asyncio
import json
import uuid

import pytest
import zmq
import zmq.asyncio
from beem.blockchain import Blockchain


from podping_hivewriter import config, run
from podping_hivewriter.config import Config
from podping_hivewriter.hive_wrapper import get_hive


@pytest.mark.asyncio
@pytest.mark.timeout(60)
@pytest.mark.slow
@pytest.mark.skip
async def test_write_single_url_zmq_req(event_loop):
    # Ensure use of testnet
    config.Config.test = True
    config.Config.ignore_updates = True
    hive = get_hive(Config.podping_settings.test_nodes, Config.posting_key)

    blockchain = Blockchain(mode="head", blockchain_instance=hive)
    current_block = blockchain.get_current_block_num()

    url = f"https://example.com?u={uuid.uuid4()}"

    async def get_url_from_blockchain():
        # noinspection PyTypeChecker
        stream = blockchain.stream(
            opNames=["custom_json"],
            start=current_block,
            max_batch_size=1,
            raw_ops=False,
            threading=True,
        )

        for post in stream:
            data = json.loads(post.get("json"))
            if "urls" in data:
                if len(data["urls"]) == 1:
                    yield data["urls"][0]

    podping_hivewriter, _ = run.run()

    context = zmq.asyncio.Context()
    socket = context.socket(zmq.REQ, io_loop=event_loop)
    socket.connect(f"tcp://127.0.0.1:{config.Config.zmq}")

    await socket.send_string(url)
    response = await socket.recv_string()

    assert response == "OK"

    # Sleep to catch up because beem isn't async and blocks
    # This is just longer than the amount of time url_q_worker waits for
    await asyncio.sleep(config.Config.podping_settings.hive_operation_period * 2)

    async for stream_url in get_url_from_blockchain():
        if stream_url == url:
            assert True
            break

    podping_hivewriter.close()

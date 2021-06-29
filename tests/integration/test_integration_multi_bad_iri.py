import asyncio
import json
import uuid
from random import random

import pytest
import zmq
import zmq.asyncio
from beem.blockchain import Blockchain

from podping_hivewriter import config, run
from podping_hivewriter.config import Config
from podping_hivewriter.hive_wrapper import get_hive

# Simulated multi podping writes with random gaps.


@pytest.mark.asyncio
@pytest.mark.timeout(240)
@pytest.mark.slow
async def test_write_multiple_bad_iri_zmq_req(event_loop):
    # Ensure use of Live Hive chain not the Test Net
    config.Config.test = True
    # Use the livechain
    config.Config.livetest = False
    # Don't try to update parameters
    config.Config.ignore_updates = True
    # Use different ports
    config.Config.zmq = 9979

    hive = get_hive(
        Config.podping_settings.main_nodes,
        Config.posting_key,
        use_testnet=config.Config.test,
    )

    blockchain = Blockchain(mode="head", blockchain_instance=hive)
    current_block = blockchain.get_current_block_num()

    num_urls = 10
    test_urls = []
    # 10 Good IRIs with some hebrew in them just to be fancy
    for n in range(num_urls):
        url = f"https://example.com?n={n}&h=אם-תרצו-אין-זו-אגדה&u={uuid.uuid4()}"
        test_urls.append(url)
    # 10 Bad IRIs with a : in the domain name
    for n in range(num_urls):
        url = f"https://examp:le.com?n={n}&h=אםתרצו-אין-זו-אגדה&u={uuid.uuid4()}"
        test_urls.append(url)

    async def get_url_from_blockchain(stop_block: int):
        # noinspection PyTypeChecker
        stream = blockchain.stream(
            opNames=["custom_json"],
            start=current_block,
            stop=stop_block,
            max_batch_size=None,
            raw_ops=False,
            only_ops=True,
            threading=False,
        )

        for post in stream:
            data = json.loads(post.get("json"))
            if "urls" in data:
                for url in data["urls"]:
                    yield url

    podping_hivewriter, _ = run.run()

    context = zmq.asyncio.Context()
    socket = context.socket(zmq.REQ, io_loop=event_loop)
    socket.connect(f"tcp://127.0.0.1:{config.Config.zmq}")

    all_responses = []
    for n in range(num_urls*2):
        await socket.send_string(test_urls[n])
        response = await socket.recv_string()
        all_responses.append(response)
        # assert response == "OK"

    answer_count = {i:all_responses.count(i) for i in all_responses}
    assert answer_count["OK"] == num_urls
    assert answer_count["Invalid IRI"] == num_urls

    # Sleep to catch up because beem isn't async and blocks
    # This is just longer than the amount of time url_q_worker waits for
    await asyncio.sleep(config.Config.podping_settings.hive_operation_period * 2)

    stop_block = blockchain.get_current_block_num()

    answer_urls = []
    async for stream_url in get_url_from_blockchain(stop_block):
        if stream_url in test_urls:
            answer_urls.append(stream_url)
            print(len(answer_urls))
            if len(answer_urls) == num_urls:
                assert True
                break

    podping_hivewriter.close()

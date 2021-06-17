import asyncio
import json
from typing import Set
import uuid
from timeit import default_timer as timer
from py import test

import pytest
import zmq
import zmq.asyncio
from beem.blockchain import Blockchain
from beem.account import Account

from podping_hivewriter import hive_writer, config


@pytest.mark.asyncio
@pytest.mark.slow
async def test_hive_startup():
    # Run the entire startup procedure and check returned hive object
    # Check on the main chain
    config.Config.test = False
    test_hive = await hive_writer.hive_startup()

    try:
        account = Account("podping", blockchain_instance=test_hive)
        print(account)
        assert True
    except Exception as ex:
        print(ex)
        assert False


@pytest.mark.asyncio
async def test_get_allowed_accounts():
    # Checks the allowed accounts checkup
    allowed_accounts = hive_writer.get_allowed_accounts()
    if type(allowed_accounts) == set and len(allowed_accounts) > 0:
        assert True
    else:
        assert False


@pytest.mark.asyncio
@pytest.mark.timeout(60)
@pytest.mark.slow
async def test_write_single_url_zmq_req(event_loop):
    # Ensure use of testnet
    config.Config.test = True

    hive = hive_writer.get_hive()

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
            threading=False,
        )

        for post in stream:
            data = json.loads(post.get("json"))
            if "urls" in data:
                if len(data["urls"]) == 1:
                    yield data["urls"][0]

    hive_writer.run(loop=event_loop)

    context = zmq.asyncio.Context()
    socket = context.socket(zmq.REQ, io_loop=event_loop)
    socket.connect(f"tcp://127.0.0.1:{config.Config.zmq}")

    start_time = timer()

    await socket.send_string(url)
    response = await socket.recv_string()

    assert response == "OK"

    # Sleep to catch up because beem isn't async and blocks
    # This is just longer than the amount of time url_q_worker waits for
    await asyncio.sleep(config.Config.podping_settings.hive_operation_period * 1.1)

    async for stream_url in get_url_from_blockchain():
        if stream_url == url:
            assert True
            break


@pytest.mark.asyncio
async def test_update_podping_settings(event_loop):
    # See if we can fetch data from podping
    # Must not use Testnet when looking for config data
    config.Config.podping_settings.control_account_check_period = 333333333
    old_settings = config.Config.podping_settings
    await hive_writer.update_podping_settings("podping")
    if old_settings != config.Config.podping_settings:
        print(config.Config.podping_settings)
        assert True
    else:
        assert False

import asyncio
import json
import uuid

import pytest
from beem.blockchain import Blockchain
from typer.testing import CliRunner

from podping_hivewriter.async_wrapper import sync_to_async
from podping_hivewriter.cli.podping import app
from podping_hivewriter.constants import LIVETEST_OPERATION_ID
from podping_hivewriter.hive import get_hive
from podping_hivewriter.models.hive_operation_id import HiveOperationId
from podping_hivewriter.models.medium import Medium
from podping_hivewriter.models.reason import Reason
from podping_hivewriter.podping_settings_manager import PodpingSettingsManager


@pytest.mark.asyncio
@pytest.mark.timeout(120)
@pytest.mark.slow
async def test_write_cli_single_url():
    runner = CliRunner()

    settings_manager = PodpingSettingsManager(ignore_updates=True)

    hive = await get_hive()

    blockchain = Blockchain(mode="head", blockchain_instance=hive)
    start_block = blockchain.get_current_block_num()

    session_uuid = uuid.uuid4()
    session_uuid_str = str(session_uuid)

    test_name = "cli_single"
    url = f"https://example.com?t={test_name}&s={session_uuid_str}"

    default_hive_operation_id = HiveOperationId(
        LIVETEST_OPERATION_ID, Medium.podcast, Reason.update
    )
    default_hive_operation_id_str = str(default_hive_operation_id)

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

        for post in (
            post for post in stream if post["id"] == default_hive_operation_id_str
        ):
            yield post

    get_blockchain_stream = sync_to_async(_blockchain_stream, thread_sensitive=False)

    async def get_url_from_blockchain(stop_block: int):
        stream = get_blockchain_stream(stop_block)

        async for post in stream:
            data = json.loads(post["json"])
            if "urls" in data and len(data["urls"]) == 1:
                yield data["urls"][0]

    args = ["--livetest", "--no-sanity-check", "--ignore-config-updates", "write", url]
    # Ensure hive env vars are set from .env.test file or this will fail
    result = runner.invoke(app, args)

    assert result.exit_code == 0

    op_period = settings_manager._settings.hive_operation_period

    # Sleep to catch up because beem isn't async and blocks
    await asyncio.sleep(op_period * 25)

    end_block = blockchain.get_current_block_num()

    url_found = False

    async for stream_url in get_url_from_blockchain(end_block):
        if stream_url == url:
            url_found = True
            break

    assert url_found

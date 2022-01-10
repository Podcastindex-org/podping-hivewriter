import asyncio
import json
import uuid
from random import randint
from platform import python_version as pv

import pytest
from lighthive.client import Client
from lighthive.helpers.event_listener import EventListener
from typer.testing import CliRunner

from podping_hivewriter.async_wrapper import sync_to_async
from podping_hivewriter.cli.podping import app
from podping_hivewriter.constants import LIVETEST_OPERATION_ID
from podping_hivewriter.models.hive_operation_id import HiveOperationId
from podping_hivewriter.models.medium import Medium
from podping_hivewriter.models.reason import Reason
from podping_hivewriter.podping_settings_manager import PodpingSettingsManager


@pytest.mark.asyncio
@pytest.mark.timeout(180)
@pytest.mark.slow
async def test_write_cli_multiple_url():
    runner = CliRunner()

    settings_manager = PodpingSettingsManager(ignore_updates=True)

    client = Client()

    session_uuid = uuid.uuid4()
    session_uuid_str = str(session_uuid)

    num_urls = randint(2, 25)
    test_name = "cli_multiple"
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

    args = [
        "--livetest",
        "--no-sanity-check",
        "--ignore-config-updates",
        "write",
        *test_urls,
    ]

    current_block = client.get_dynamic_global_properties()["head_block_number"]

    # Ensure hive env vars are set from .env.test file or this will fail
    result = runner.invoke(app, args)

    assert result.exit_code == 0

    op_period = settings_manager._settings.hive_operation_period

    # Sleep to catch up because beem isn't async and blocks
    await asyncio.sleep(op_period * 30)

    answer_urls = set()
    async for stream_url in get_url_from_blockchain(current_block - 5):
        answer_urls.add(stream_url)

        # If we're done, end early
        if len(answer_urls) == len(test_urls):
            break

    assert answer_urls == test_urls

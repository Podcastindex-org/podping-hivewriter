import asyncio
import json
import uuid
from platform import python_version as pv

import pytest
from lighthive.client import Client
from lighthive.helpers.event_listener import EventListener
from typer.testing import CliRunner

from podping_hivewriter.async_wrapper import sync_to_async
from podping_hivewriter.cli.podping import app
from podping_hivewriter.constants import (
    LIVETEST_OPERATION_ID,
    STARTUP_FAILED_INVALID_ACCOUNT,
    STARTUP_FAILED_INVALID_POSTING_KEY_EXIT_CODE,
)
from podping_hivewriter.models.hive_operation_id import HiveOperationId
from podping_hivewriter.models.medium import Medium
from podping_hivewriter.models.reason import Reason
from podping_hivewriter.podping_settings_manager import PodpingSettingsManager

from typer import BadParameter


@pytest.mark.asyncio
@pytest.mark.timeout(600)
@pytest.mark.slow
async def test_startup_checks_and_write_cli_single():
    runner = CliRunner()

    settings_manager = PodpingSettingsManager(ignore_updates=True)

    client = Client()

    session_uuid = uuid.uuid4()
    session_uuid_str = str(session_uuid)

    test_name = "cli_single"
    iri = f"https://example.com?t={test_name}&v={pv()}&s={session_uuid_str}"

    default_hive_operation_id = HiveOperationId(
        LIVETEST_OPERATION_ID, Medium.podcast, Reason.update
    )
    default_hive_operation_id_str = str(default_hive_operation_id)

    async def get_iri_from_blockchain(start_block: int):
        event_listener = EventListener(client, "head", start_block=start_block)
        _on = sync_to_async(event_listener.on, thread_sensitive=False)
        async for post in _on(
            "custom_json", filter_by={"id": default_hive_operation_id_str}
        ):
            data = json.loads(post["op"][1]["json"])
            if "iris" in data and len(data["iris"]) == 1:
                yield data["iris"][0]

    args = ["--livetest", "write", iri]

    current_block = client.get_dynamic_global_properties()["head_block_number"]

    # Ensure hive env vars are set from .env.test file or this will fail
    result = runner.invoke(app, args)

    assert result.exit_code == 0

    # Sleep to catch up because beem isn't async and blocks
    await asyncio.sleep(3 * 25)

    iri_found = False

    async for stream_iri in get_iri_from_blockchain(current_block - 5):
        if stream_iri == iri:
            iri_found = True
            break

    del settings_manager
    assert iri_found


@pytest.mark.asyncio
async def test_startup_failures():
    """Deliberately force failure in startup of cli"""
    runner = CliRunner()

    session_uuid = uuid.uuid4()
    session_uuid_str = str(session_uuid)

    test_name = "cli_fail"
    iri = f"https://example.com?t={test_name}&v={pv()}&s={session_uuid_str}"

    # This will fail, bad hive account name
    args = ["--livetest", "--hive-account", "_podping", "write", iri]
    result = runner.invoke(app, args)

    assert result.exit_code == STARTUP_FAILED_INVALID_ACCOUNT

    args = ["--livetest", "--hive-posting-key", "not_a_valid_key", "write", iri]
    result = runner.invoke(app, args)

    assert result.exit_code == STARTUP_FAILED_INVALID_POSTING_KEY_EXIT_CODE

    args = ["--livetest", "--debug", "--medium", "wrong_medium" "write", iri]
    result = runner.invoke(app, args)

    assert result.exit_code == BadParameter.exit_code

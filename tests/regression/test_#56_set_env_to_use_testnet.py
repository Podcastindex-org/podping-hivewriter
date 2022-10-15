import json
import os
import uuid
from platform import python_version as pv

import pytest
from typer.testing import CliRunner

from podping_hivewriter.cli.podping import app
from podping_hivewriter.constants import LIVETEST_OPERATION_ID
from podping_hivewriter.hive import get_client, listen_for_custom_json_operations
from podping_hivewriter.models.hive_operation_id import HiveOperationId
from podping_hivewriter.models.medium import Medium
from podping_hivewriter.models.reason import Reason
from podping_hivewriter.podping_settings_manager import PodpingSettingsManager


@pytest.mark.asyncio
@pytest.mark.timeout(600)
@pytest.mark.slow
async def test_use_testnet_startup_checks_and_write_cli_single():
    """Uses a testnet if one is available"""
    runner = CliRunner()

    os.environ["PODPING_TESTNET"] = "true"
    os.environ["PODPING_TESTNET_NODE"] = "https://api.fake.openhive.network"
    os.environ[
        "PODPING_TESTNET_CHAINID"
    ] = "4200000000000000000000000000000000000000000000000000000000000000"

    client = get_client()
    try:
        props = client.get_dynamic_global_properties()
    except Exception:
        # If we can't connect to the fakenet / testnet then just pass the test
        assert True
        return

    assert props

    session_uuid = uuid.uuid4()
    session_uuid_str = str(session_uuid)

    test_name = "use_testnet_startup_checks_and_write_cli_single"
    iri = f"https://example.com?t={test_name}&v={pv()}&s={session_uuid_str}"

    default_hive_operation_id = HiveOperationId(
        LIVETEST_OPERATION_ID, Medium.podcast, Reason.update
    )
    default_hive_operation_id_str = str(default_hive_operation_id)

    async def get_iri_from_blockchain(start_block: int):
        async for post in listen_for_custom_json_operations(client, start_block):
            if post["op"][1]["id"] == default_hive_operation_id_str:
                data = json.loads(post["op"][1]["json"])
                if "iris" in data and len(data["iris"]) == 1:
                    yield data["iris"][0]

    args = ["--livetest", "--hive-operation-period", "30", "write", iri]

    current_block = client.get_dynamic_global_properties()["head_block_number"]

    # Ensure hive env vars are set from .env.test file or this will fail
    result = runner.invoke(app, args)

    assert result.exit_code == 0

    iri_found = False

    async for stream_iri in get_iri_from_blockchain(current_block):
        if stream_iri == iri:
            iri_found = True
            break

    assert iri_found

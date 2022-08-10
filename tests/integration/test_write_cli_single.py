import json
import random
import uuid
from platform import python_version as pv

import pytest
from lighthive.client import Client
from typer.testing import CliRunner

from podping_hivewriter.cli.podping import app
from podping_hivewriter.constants import LIVETEST_OPERATION_ID
from podping_hivewriter.hive import listen_for_custom_json_operations
from podping_hivewriter.models.hive_operation_id import HiveOperationId
from podping_hivewriter.models.medium import str_medium_map, mediums
from podping_hivewriter.models.reason import str_reason_map, reasons


@pytest.mark.asyncio
@pytest.mark.timeout(600)
@pytest.mark.slow
async def test_write_cli_single():
    runner = CliRunner()
    client = Client()

    session_uuid = uuid.uuid4()
    session_uuid_str = str(session_uuid)

    test_name = "cli_single"
    iri = f"https://example.com?t={test_name}&v={pv()}&s={session_uuid_str}"

    medium = str_medium_map[random.sample(sorted(mediums), 1)[0]]
    reason = str_reason_map[random.sample(sorted(reasons), 1)[0]]

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
                        yield data["iris"][0]

    args = [
        "--medium",
        str(medium),
        "--reason",
        str(reason),
        "--livetest",
        "--no-sanity-check",
        "--ignore-config-updates",
        "write",
        iri,
    ]

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

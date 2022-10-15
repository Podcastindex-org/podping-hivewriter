import json
import random
import uuid
from platform import python_version as pv
from random import randint

import pytest
from typer.testing import CliRunner

from podping_hivewriter.cli.podping import app
from podping_hivewriter.constants import LIVETEST_OPERATION_ID
from podping_hivewriter.hive import get_client, listen_for_custom_json_operations
from podping_hivewriter.models.hive_operation_id import HiveOperationId
from podping_hivewriter.models.medium import mediums, str_medium_map
from podping_hivewriter.models.reason import reasons, str_reason_map


@pytest.mark.asyncio
@pytest.mark.timeout(600)
@pytest.mark.slow
async def test_write_cli_multiple():
    runner = CliRunner()

    client = get_client()

    session_uuid = uuid.uuid4()
    session_uuid_str = str(session_uuid)

    num_iris = randint(2, 25)
    test_name = "cli_multiple"
    python_version = pv()
    test_iris = {
        f"https://example.com?t={test_name}&i={i}&v={python_version}&s={session_uuid_str}"
        for i in range(num_iris)
    }

    medium = str_medium_map[random.sample(sorted(mediums), 1)[0]]
    reason = str_reason_map[random.sample(sorted(reasons), 1)[0]]

    default_hive_operation_id = HiveOperationId(LIVETEST_OPERATION_ID, medium, reason)
    default_hive_operation_id_str = str(default_hive_operation_id)

    async def get_iri_from_blockchain(start_block: int):
        async for post in listen_for_custom_json_operations(client, start_block):
            if post["op"][1]["id"] == default_hive_operation_id_str:
                data = json.loads(post["op"][1]["json"])
                if "iris" in data:
                    for iri in data["iris"]:
                        # Only look for IRIs from current session
                        if iri.endswith(session_uuid_str):
                            yield iri

    args = [
        "--medium",
        str(medium),
        "--reason",
        str(reason),
        "--livetest",
        "--no-sanity-check",
        "--ignore-config-updates",
        "write",
        *test_iris,
    ]

    current_block = client.get_dynamic_global_properties()["head_block_number"]

    # Ensure hive env vars are set from .env.test file or this will fail
    result = runner.invoke(app, args)

    assert result.exit_code == 0

    answer_iris = set()
    async for stream_iri in get_iri_from_blockchain(current_block):
        answer_iris.add(stream_iri)

        # If we're done, end early
        if len(answer_iris) == len(test_iris):
            break

    assert answer_iris == test_iris

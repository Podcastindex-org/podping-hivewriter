import random
import uuid
from platform import python_version as pv
from random import randint

import pytest
from typer.testing import CliRunner

from podping_hivewriter.cli.podping import app
from podping_hivewriter.constants import LIVETEST_OPERATION_ID
from podping_hivewriter.hive import get_relevant_transactions_from_blockchain
from podping_hivewriter.models.hive_operation_id import HiveOperationId
from podping_hivewriter.models.medium import medium_strings, str_medium_map
from podping_hivewriter.models.reason import reason_strings, str_reason_map


@pytest.mark.asyncio
@pytest.mark.timeout(600)
@pytest.mark.slow
async def test_write_cli_multiple(lighthive_client):
    runner = CliRunner()

    session_uuid = uuid.uuid4()
    session_uuid_str = str(session_uuid)

    num_iris = randint(2, 25)
    test_name = "cli_multiple"
    python_version = pv()
    test_iris = {
        f"https://example.com?t={test_name}&i={i}&v={python_version}&s={session_uuid_str}"
        for i in range(num_iris)
    }

    medium = str_medium_map[random.sample(sorted(medium_strings), 1)[0]]
    reason = str_reason_map[random.sample(sorted(reason_strings), 1)[0]]

    default_hive_operation_id = HiveOperationId(LIVETEST_OPERATION_ID, medium, reason)
    default_hive_operation_id_str = str(default_hive_operation_id)

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

    current_block = lighthive_client.get_dynamic_global_properties()[
        "head_block_number"
    ]

    # Ensure hive env vars are set from .env.test file or this will fail
    result = runner.invoke(app, args)

    assert result.exit_code == 0

    answer_iris = set()
    async for tx in get_relevant_transactions_from_blockchain(
        lighthive_client, current_block, default_hive_operation_id_str
    ):
        for podping in tx.podpings:
            assert podping.medium == medium
            assert podping.reason == reason

            for iri in podping.iris:
                if iri.endswith(session_uuid_str):
                    answer_iris.add(iri)

        if len(test_iris) == len(answer_iris):
            break

    assert test_iris == answer_iris

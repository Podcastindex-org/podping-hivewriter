import random
import uuid
from platform import python_version as pv

import pytest
from typer.testing import CliRunner

from podping_hivewriter.cli.podping import app
from podping_hivewriter.constants import LIVETEST_OPERATION_ID
from podping_hivewriter.hive import get_relevant_transactions_from_blockchain
from podping_hivewriter.models.hive_operation_id import HiveOperationId
from podping_hivewriter.models.medium import mediums, str_medium_map
from podping_hivewriter.models.reason import reasons, str_reason_map


@pytest.mark.asyncio
@pytest.mark.timeout(600)
@pytest.mark.slow
async def test_write_cli_single(lighthive_client):
    runner = CliRunner()

    session_uuid = uuid.uuid4()
    session_uuid_str = str(session_uuid)

    test_name = "cli_single"
    iri = f"https://example.com?t={test_name}&v={pv()}&s={session_uuid_str}"

    medium = str_medium_map[random.sample(sorted(mediums), 1)[0]]
    reason = str_reason_map[random.sample(sorted(reasons), 1)[0]]

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
        iri,
    ]

    current_block = lighthive_client.get_dynamic_global_properties()[
        "head_block_number"
    ]

    # Ensure hive env vars are set from .env.test file or this will fail
    result = runner.invoke(app, args)

    assert result.exit_code == 0
    iri_found = False

    async for tx in get_relevant_transactions_from_blockchain(
        lighthive_client, current_block, default_hive_operation_id_str
    ):
        if iri in tx.iris:
            iri_found = True
            assert tx.medium == medium
            assert tx.reason == reason
            break

    assert iri_found

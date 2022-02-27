import asyncio
import json
import random
from timeit import default_timer as timer
import uuid
from platform import python_version as pv

import pytest
from lighthive.client import Client
from typer.testing import CliRunner

from podping_hivewriter.cli.podping import app
from podping_hivewriter.hive import listen_for_custom_json_operations
from podping_hivewriter.models.medium import str_medium_map, mediums
from podping_hivewriter.models.reason import str_reason_map, reasons


@pytest.mark.asyncio
@pytest.mark.timeout(900)
@pytest.mark.slow
async def test_write_cli_single_simulcast():
    """This test forces 7 separate posts to ensure we retry after exceeding the
    limit of posts per block (5)"""
    runner = CliRunner()
    start = timer()

    client = Client()

    session_uuid = uuid.uuid4()
    session_uuid_str = str(session_uuid)

    async def _run_cli_once(_app, _args):
        print(f"Timer: {timer()-start}")
        result = runner.invoke(_app, _args)
        return result

    async def get_iri_from_blockchain(start_block: int):
        async for post in listen_for_custom_json_operations(client, start_block):
            data = json.loads(post["op"][1]["json"])
            if "iris" in data and len(data["iris"]) == 1:
                iri = data["iris"][0]
                # Only look for IRIs from current session
                if iri.endswith(session_uuid_str):
                    yield iri

    # Ensure hive env vars are set from .env.test file or this will fail

    python_version = pv()
    tasks = []
    test_iris = {
        f"https://example.com?t=cli_simulcast_{n}"
        f"&v={python_version}&s={session_uuid_str}"
        for n in range(7)
    }
    for iri in test_iris:
        medium = str_medium_map[random.sample(mediums, 1)[0]]
        reason = str_reason_map[random.sample(reasons, 1)[0]]
        args = [
            "--medium",
            str(medium),
            "--reason",
            str(reason),
            "--livetest",
            "--no-sanity-check",
            "--ignore-config-updates",
            "--debug",
            "write",
            iri,
        ]
        tasks.append(_run_cli_once(app, args))

    current_block = client.get_dynamic_global_properties()["head_block_number"]

    results = await asyncio.gather(*tasks)

    all_ok = all(r.exit_code == 0 for r in results)
    assert all_ok

    answer_iris = set()
    async for stream_iri in get_iri_from_blockchain(current_block):
        answer_iris.add(stream_iri)

        # If we're done, end early
        if len(answer_iris) == len(test_iris):
            break

    assert answer_iris == test_iris


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    coro = test_write_cli_single_simulcast()
    loop.run_until_complete(coro)

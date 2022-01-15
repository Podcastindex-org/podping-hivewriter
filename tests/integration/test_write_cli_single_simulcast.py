import asyncio
import json
from timeit import default_timer as timer
import uuid
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
@pytest.mark.timeout(900)
@pytest.mark.slow
async def test_write_cli_single_simulcast():
    """This test forces 6 separate posts to ensure we retry after exceeding the
    limit of posts per block (5)"""
    runner = CliRunner()
    start = timer()
    settings_manager = PodpingSettingsManager(ignore_updates=True)

    client = Client()

    session_uuid = uuid.uuid4()
    session_uuid_str = str(session_uuid)

    default_hive_operation_id = HiveOperationId(
        LIVETEST_OPERATION_ID, Medium.podcast, Reason.update
    )
    default_hive_operation_id_str = str(default_hive_operation_id)

    async def _run_cli_once(_app, _args):
        print(f"Timer: {timer()-start}")
        result = runner.invoke(_app, _args)
        return result

    async def get_iri_from_blockchain(start_block: int):
        event_listener = EventListener(client, "head", start_block=start_block)
        _on = sync_to_async(event_listener.on, thread_sensitive=False)
        async for post in _on(
            "custom_json", filter_by={"id": default_hive_operation_id_str}
        ):
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
        for n in range(6)
    }
    for iri in test_iris:
        args = [
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

    op_period = settings_manager._settings.hive_operation_period

    # Sleep to catch up because beem isn't async and blocks
    await asyncio.sleep(op_period * 25)

    answer_iris = set()
    async for stream_iri in get_iri_from_blockchain(current_block - 5):
        answer_iris.add(stream_iri)

        # If we're done, end early
        if len(answer_iris) == len(test_iris):
            break

    assert answer_iris == test_iris


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    coro = test_write_cli_single_simulcast()
    loop.run_until_complete(coro)

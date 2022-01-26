import asyncio

from typing import List

from podping_hivewriter.models.medium import Medium
from podping_hivewriter.models.reason import Reason
from podping_hivewriter.podping_hivewriter import PodpingHivewriter
from podping_hivewriter.podping_settings_manager import PodpingSettingsManager


def send_podpings(
    iris: List[str],
    server_account: str,
    posting_keys: List[str],
    medium: str = "podcast",
    reason: str = "update",
    dry_run: bool = False,
    resource_test: bool = False,
):
    """Take in a list of iris, validate and send them"""
    with PodpingHivewriter(
        server_account=server_account,
        posting_keys=posting_keys,
        settings_manager=PodpingSettingsManager(ignore_updates=True),
        dry_run=dry_run,
        resource_test=resource_test,
        daemon=False,
    ) as pp:
        coro = pp.failure_retry(
            iri_set=set(iris),
            medium=medium,
            reason=reason,
        )
        # If the loop isn't running, RuntimeError is raised.  Run normally
        loop = asyncio.get_event_loop()
        loop.run_until_complete(coro)
    return


async def send_podpings_async(
    iris: List[str],
    server_account: str,
    posting_keys: List[str],
    medium: str = "podcast",
    reason: str = "update",
    dry_run: bool = False,
    resource_test: bool = False,
):
    """Take in a list of iris and send them (async)"""
    with PodpingHivewriter(
        server_account=server_account,
        posting_keys=posting_keys,
        settings_manager=PodpingSettingsManager(ignore_updates=True),
        dry_run=dry_run,
        resource_test=resource_test,
        daemon=False,
    ) as pp:
        _ = await pp.failure_retry(
            iri_set=set(iris),
            medium=medium,
            reason=reason,
        )

    return

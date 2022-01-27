import asyncio
import logging
from typing import List

from pydantic import ValidationError

from podping_hivewriter.models.medium import Medium
from podping_hivewriter.models.podping import Podping
from podping_hivewriter.models.reason import Reason
from podping_hivewriter.podping_hivewriter import PodpingHivewriter
from podping_hivewriter.podping_settings_manager import PodpingSettingsManager



def _validate(
    iris: List[str],
    server_account: str,
    posting_keys: List[str],
    medium: Medium = Medium.podcast,
    reason: Reason = Reason.update,
) -> bool:
    """Validate incoming podping data returns True if all OK"""
    try:
        iri_set = set(iris)
        payload = Podping(medium=medium, reason=reason, iris=list(iri_set))
        return True
    except ValidationError as ex:
        logging.error(f"Failed to send {len(iri_set)} IRIs")
        logging.error(f"{ex}")
        raise ex
    except Exception:
        raise


def publish(
    iris: List[str],
    server_account: str,
    posting_keys: List[str],
    medium: Medium = Medium.podcast,
    reason: Reason = Reason.update,
    dry_run: bool = False,
    resource_test: bool = False,
):
    """Take in a list of iris, validate and send them"""
    _validate(iris, server_account, posting_keys, medium, reason)


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


async def publish_async(
    iris: List[str],
    server_account: str,
    posting_keys: List[str],
    medium: Medium = Medium.podcast,
    reason: Reason = Reason.update,
    dry_run: bool = False,
    resource_test: bool = False,
):
    """Take in a list of iris and send them (async)"""
    _validate(iris, server_account, posting_keys, medium, reason)

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

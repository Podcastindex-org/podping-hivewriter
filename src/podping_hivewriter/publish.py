import asyncio
import logging
from typing import List

from pydantic import ValidationError
from podping_hivewriter.constants import LIVETEST_OPERATION_ID, PODPING_OPERATION_ID

from podping_hivewriter.exceptions import BadStartupData
from podping_hivewriter.hive import validate_account_info
from podping_hivewriter.models.medium import Medium
from podping_hivewriter.models.podping import Podping
from podping_hivewriter.models.reason import Reason
from podping_hivewriter.podping_hivewriter import PodpingHivewriter
from podping_hivewriter.podping_settings_manager import PodpingSettingsManager


def _get_operation_id(livetest: bool) -> str:
    """return the opertaion id"""
    if livetest:
        return LIVETEST_OPERATION_ID
    else:
        return PODPING_OPERATION_ID


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
        _ = Podping(medium=medium, reason=reason, iris=list(iri_set))
        validate_account_info(hive_account=server_account, posting_keys=posting_keys)
        return True
    except ValidationError as ex:
        logging.error(f"Failed to send {len(iri_set)} IRIs")
        logging.error(f"Validation Error: {ex}")
        raise ValidationError(ex)
    except BadStartupData as ex:
        logging.error(f"Failed to send {len(iri_set)} IRIs")
        logging.error(f"Bad Startup Data: {ex}")
        raise BadStartupData(ex)
    except Exception as ex:
        raise ex


def publish(
    iris: List[str],
    server_account: str,
    posting_keys: List[str],
    livetest: bool = False,
    medium: Medium = Medium.podcast,
    reason: Reason = Reason.update,
    dry_run: bool = False,
    resource_test: bool = False,
):
    """Take in a list of iris, validate and publish them as a Podping

    :param List[str] iris: List of of individual iri's
    """
    _validate(iris, server_account, posting_keys, medium, reason)
    operation_id = _get_operation_id(livetest)

    with PodpingHivewriter(
        server_account=server_account,
        posting_keys=posting_keys,
        settings_manager=PodpingSettingsManager(ignore_updates=True),
        dry_run=dry_run,
        resource_test=resource_test,
        operation_id=operation_id,
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
    livetest: bool = False,
    medium: Medium = Medium.podcast,
    reason: Reason = Reason.update,
    dry_run: bool = False,
    resource_test: bool = False,
):
    """Take in a list of iris and send them (async)"""
    _validate(iris, server_account, posting_keys, medium, reason)
    operation_id = _get_operation_id(livetest)

    with PodpingHivewriter(
        server_account=server_account,
        posting_keys=posting_keys,
        settings_manager=PodpingSettingsManager(ignore_updates=True),
        dry_run=dry_run,
        resource_test=resource_test,
        operation_id=operation_id,
        daemon=False,
    ) as pp:
        _ = await pp.failure_retry(
            iri_set=set(iris),
            medium=medium,
            reason=reason,
        )

    return

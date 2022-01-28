import asyncio
import logging
from typing import List

from pydantic import Field, ValidationError
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
    server_account: str,
    posting_keys: List[str],
    iris: List[str] = None,
    medium: Medium = Medium.podcast,
    reason: Reason = Reason.update,
) -> bool:

    """Validate incoming podping data returns True if all OK"""
    try:
        if not iris:
            iris = ["https://example.com/dummy.rss"]
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
    _validate(server_account, posting_keys, iris, medium, reason)
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
    _validate(server_account, posting_keys, iris, medium, reason)
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


class LoopPodpingHivewriter(PodpingHivewriter):
    """Maintain a PodpingHivewriter object for easy re-use in a long running script"""

    def __init__(
        self,
        server_account: str,
        posting_keys: List[str],
        ignore_updates: bool = False,
        medium: Medium = ...,
        reason: Reason = ...,
        operation_id="pp",
        livetest=True,
        resource_test=True,
        dry_run=False,
        daemon=True,
        status=True,
        zero_mq=False
    ):
        settings_manager = PodpingSettingsManager(ignore_updates=ignore_updates)
        _validate(server_account, posting_keys, medium=medium, reason=reason)
        operation_id = _get_operation_id(livetest)
        super().__init__(
            server_account,
            posting_keys,
            settings_manager,
            medium,
            reason,
            operation_id=operation_id,
            resource_test=resource_test,
            dry_run=dry_run,
            daemon=daemon,
            status=status,
            zero_mq=zero_mq
        )


# async def batch_publish_startup_async(
#     server_account: str,
#     posting_keys: List[str],
#     livetest: bool = False,
#     medium: Medium = Medium.podcast,
#     reason: Reason = Reason.update,
#     dry_run: bool = False,
#     resource_test: bool = False,
# ) -> PodpingHivewriter:
#     iris = []
#     _validate(iris, server_account, posting_keys, medium, reason)
#     operation_id = _get_operation_id(livetest)
#     pp =  PodpingHivewriter(
#         server_account=server_account,
#         posting_keys=posting_keys,
#         settings_manager=PodpingSettingsManager(ignore_updates=True),
#         dry_run=dry_run,
#         resource_test=resource_test,
#         operation_id=operation_id,
#         daemon=True,
#     )
#     await pp.iri_queue.put()

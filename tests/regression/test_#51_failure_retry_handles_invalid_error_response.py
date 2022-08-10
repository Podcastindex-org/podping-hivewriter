import os
import random
import uuid
from platform import python_version as pv

import lighthive
import pytest

from lighthive.client import Client
from lighthive.exceptions import RPCNodeException

from podping_hivewriter import podping_hivewriter
from podping_hivewriter.constants import LIVETEST_OPERATION_ID
from podping_hivewriter.models.medium import str_medium_map, mediums
from podping_hivewriter.models.reason import str_reason_map, reasons
from podping_hivewriter.podping_hivewriter import PodpingHivewriter
from podping_hivewriter.podping_settings_manager import PodpingSettingsManager


@pytest.mark.asyncio
async def test_failure_retry_handles_invalid_error_response(
    event_loop, mocker, monkeypatch
):
    settings_manager = PodpingSettingsManager(ignore_updates=True)

    logging_warning_stub = mocker.stub(name="logging_warning_stub")
    logging_exception_stub = mocker.stub(name="logging_exception_stub")

    def mock_broadcast(*args, **kwargs):
        raise RPCNodeException(
            "mock_broadcast exception", code=42, raw_body={"foo": "bar"}
        )

    mocker.patch.object(podping_hivewriter.itertools, "repeat", return_value=range(1))
    monkeypatch.setattr(podping_hivewriter.logging, "warning", logging_warning_stub)
    monkeypatch.setattr(podping_hivewriter.logging, "exception", logging_exception_stub)
    monkeypatch.setattr(lighthive.client.Client, "broadcast", mock_broadcast)
    lighthive_client_next_node_spy = mocker.spy(lighthive.client.Client, "next_node")

    session_uuid = uuid.uuid4()
    session_uuid_str = str(session_uuid)

    test_name = "failure_retry_handles_invalid_error_response"
    iri = f"https://example.com?t={test_name}&v={pv()}&s={session_uuid_str}"

    medium = str_medium_map[random.sample(sorted(mediums), 1)[0]]
    reason = str_reason_map[random.sample(sorted(reasons), 1)[0]]

    writer = PodpingHivewriter(
        os.environ["PODPING_HIVE_ACCOUNT"],
        [os.environ["PODPING_HIVE_POSTING_KEY"]],
        settings_manager,
        medium=medium,
        reason=reason,
        daemon=False,
        resource_test=False,
        operation_id=LIVETEST_OPERATION_ID,
    )

    await writer.wait_startup()

    lighthive_client_next_node_spy.reset_mock()

    failure_count = await writer.failure_retry({iri}, medium, reason)

    writer.close()

    logging_warning_stub.assert_called_once()
    lighthive_client_next_node_spy.assert_called_once()
    assert logging_exception_stub.call_count == 2
    assert failure_count == 1

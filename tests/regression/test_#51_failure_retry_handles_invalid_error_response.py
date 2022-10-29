import os
import random
import uuid
from platform import python_version as pv

import lighthive
import pytest
from lighthive.exceptions import RPCNodeException

from podping_hivewriter import podping_hivewriter
from podping_hivewriter.constants import LIVETEST_OPERATION_ID
from podping_hivewriter.exceptions import NotEnoughResourceCredits
from podping_hivewriter.models.medium import mediums, str_medium_map
from podping_hivewriter.models.reason import reasons, str_reason_map
from podping_hivewriter.podping_hivewriter import PodpingHivewriter
from podping_hivewriter.podping_settings_manager import PodpingSettingsManager


@pytest.mark.asyncio
async def test_failure_retry_handles_invalid_error_response(mocker, monkeypatch):
    settings_manager = PodpingSettingsManager(ignore_updates=True)

    logging_warning_stub = mocker.stub(name="logging_warning_stub")
    logging_error_stub = mocker.stub(name="logging_error_stub")

    def mock_broadcast(*args, **kwargs):
        raise RPCNodeException(
            "mock_broadcast exception", code=42, raw_body={"foo": "bar"}
        )

    monkeypatch.setattr(podping_hivewriter.logging, "warning", logging_warning_stub)
    monkeypatch.setattr(podping_hivewriter.logging, "error", logging_error_stub)
    monkeypatch.setattr(lighthive.client.Client, "broadcast_sync", mock_broadcast)

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

    mocker.patch.object(podping_hivewriter.itertools, "repeat", return_value=range(1))
    logging_warning_stub.reset_mock()

    failure_count, response = await writer.failure_retry({iri}, medium, reason)

    writer.close()

    assert logging_warning_stub.call_count == 2
    assert logging_error_stub.call_count == 4
    assert failure_count == 1
    assert response is None


@pytest.mark.asyncio
async def test_failure_retry_handles_not_enough_resource_credits(mocker, monkeypatch):
    settings_manager = PodpingSettingsManager(ignore_updates=True)

    logging_warning_stub = mocker.stub(name="logging_warning_stub")
    logging_error_stub = mocker.stub(name="logging_error_stub")

    def mock_broadcast(*args, **kwargs):
        raise NotEnoughResourceCredits("testing")

    monkeypatch.setattr(podping_hivewriter.logging, "warning", logging_warning_stub)
    monkeypatch.setattr(podping_hivewriter.logging, "error", logging_error_stub)
    monkeypatch.setattr(lighthive.client.Client, "broadcast_sync", mock_broadcast)

    session_uuid = uuid.uuid4()
    session_uuid_str = str(session_uuid)

    test_name = "failure_retry_handles_not_enough_resource_credits"
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

    mocker.patch.object(podping_hivewriter.itertools, "repeat", return_value=range(1))
    logging_warning_stub.reset_mock()

    failure_count, response = await writer.failure_retry({iri}, medium, reason)

    writer.close()

    logging_warning_stub.assert_called_with("Sleeping for 10s")
    assert logging_warning_stub.call_count == 2
    assert logging_error_stub.call_count == 1
    assert failure_count == 1
    assert response is None

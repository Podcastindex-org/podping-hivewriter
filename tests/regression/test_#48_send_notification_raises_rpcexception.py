import os
import random
import uuid
from platform import python_version as pv

import lighthive
import pytest
from lighthive.client import Client
from lighthive.exceptions import RPCNodeException

from podping_hivewriter.constants import LIVETEST_OPERATION_ID
from podping_hivewriter.exceptions import (
    NotEnoughResourceCredits,
    TooManyCustomJsonsPerBlock,
)
from podping_hivewriter.models.medium import mediums, str_medium_map
from podping_hivewriter.models.reason import reasons, str_reason_map
from podping_hivewriter.podping_hivewriter import PodpingHivewriter
from podping_hivewriter.podping_settings_manager import PodpingSettingsManager


@pytest.mark.asyncio
async def test_send_notification_raises_rpcexception_invalid_body(
    event_loop, monkeypatch
):
    settings_manager = PodpingSettingsManager(ignore_updates=True)

    def mock_broadcast(*args, **kwargs):
        raise RPCNodeException(
            "mock_broadcast exception", code=42, raw_body={"foo": "bar"}
        )

    monkeypatch.setattr(lighthive.client.Client, "broadcast", mock_broadcast)

    session_uuid = uuid.uuid4()
    session_uuid_str = str(session_uuid)

    test_name = "test_send_notification_raises_rpcexception_invalid_body"
    iri = f"https://example.com?t={test_name}&v={pv()}&s={session_uuid_str}"

    medium = str_medium_map[random.sample(sorted(mediums), 1)[0]]
    reason = str_reason_map[random.sample(sorted(reasons), 1)[0]]

    podping_hivewriter = PodpingHivewriter(
        os.environ["PODPING_HIVE_ACCOUNT"],
        [os.environ["PODPING_HIVE_POSTING_KEY"]],
        settings_manager,
        medium=medium,
        reason=reason,
        daemon=False,
        resource_test=False,
        operation_id=LIVETEST_OPERATION_ID,
    )

    await podping_hivewriter.wait_startup()

    with pytest.raises(RPCNodeException):
        await podping_hivewriter.send_notification_iri(iri, medium, reason)

    podping_hivewriter.close()


@pytest.mark.asyncio
async def test_send_notification_raises_rpcexception_valid_body(
    event_loop, monkeypatch
):
    settings_manager = PodpingSettingsManager(ignore_updates=True)

    def mock_broadcast(*args, **kwargs):
        raise RPCNodeException(
            "mock_broadcast exception",
            code=42,
            raw_body={"error": {"message": "nonsense"}},
        )

    monkeypatch.setattr(lighthive.client.Client, "broadcast", mock_broadcast)

    session_uuid = uuid.uuid4()
    session_uuid_str = str(session_uuid)

    test_name = "test_send_notification_raises_rpcexception_valid_body"
    iri = f"https://example.com?t={test_name}&v={pv()}&s={session_uuid_str}"

    medium = str_medium_map[random.sample(sorted(mediums), 1)[0]]
    reason = str_reason_map[random.sample(sorted(reasons), 1)[0]]

    podping_hivewriter = PodpingHivewriter(
        os.environ["PODPING_HIVE_ACCOUNT"],
        [os.environ["PODPING_HIVE_POSTING_KEY"]],
        settings_manager,
        medium=medium,
        reason=reason,
        daemon=False,
        resource_test=False,
        operation_id=LIVETEST_OPERATION_ID,
    )

    await podping_hivewriter.wait_startup()

    with pytest.raises(RPCNodeException):
        await podping_hivewriter.send_notification_iri(iri, medium, reason)

    podping_hivewriter.close()


@pytest.mark.asyncio
async def test_send_notification_raises_too_many_custom_jsons_per_block(
    event_loop, monkeypatch
):
    settings_manager = PodpingSettingsManager(ignore_updates=True)

    def mock_broadcast(*args, **kwargs):
        raise RPCNodeException(
            "mock_broadcast exception",
            code=42,
            raw_body={"error": {"message": "plugin exception foobar custom json bizz"}},
        )

    monkeypatch.setattr(lighthive.client.Client, "broadcast", mock_broadcast)

    session_uuid = uuid.uuid4()
    session_uuid_str = str(session_uuid)

    test_name = "test_send_notification_raises_too_many_custom_jsons_per_block"
    iri = f"https://example.com?t={test_name}&v={pv()}&s={session_uuid_str}"

    medium = str_medium_map[random.sample(sorted(mediums), 1)[0]]
    reason = str_reason_map[random.sample(sorted(reasons), 1)[0]]

    podping_hivewriter = PodpingHivewriter(
        os.environ["PODPING_HIVE_ACCOUNT"],
        [os.environ["PODPING_HIVE_POSTING_KEY"]],
        settings_manager,
        medium=medium,
        reason=reason,
        daemon=False,
        resource_test=False,
        operation_id=LIVETEST_OPERATION_ID,
    )

    await podping_hivewriter.wait_startup()

    with pytest.raises(TooManyCustomJsonsPerBlock):
        await podping_hivewriter.send_notification_iri(iri, medium, reason)

    podping_hivewriter.close()


@pytest.mark.asyncio
async def test_send_notification_raises_not_enough_resource_credits(
    event_loop, monkeypatch
):
    settings_manager = PodpingSettingsManager(ignore_updates=True)

    def mock_broadcast(*args, **kwargs):
        raise RPCNodeException(
            "mock_broadcast exception",
            code=42,
            raw_body={"error": {"message": "payer has not enough RC mana bizz"}},
        )

    monkeypatch.setattr(lighthive.client.Client, "broadcast", mock_broadcast)

    session_uuid = uuid.uuid4()
    session_uuid_str = str(session_uuid)

    test_name = "test_send_notification_raises_not_enough_resource_credits"
    iri = f"https://example.com?t={test_name}&v={pv()}&s={session_uuid_str}"

    medium = str_medium_map[random.sample(sorted(mediums), 1)[0]]
    reason = str_reason_map[random.sample(sorted(reasons), 1)[0]]

    podping_hivewriter = PodpingHivewriter(
        os.environ["PODPING_HIVE_ACCOUNT"],
        [os.environ["PODPING_HIVE_POSTING_KEY"]],
        settings_manager,
        medium=medium,
        reason=reason,
        daemon=False,
        resource_test=False,
        operation_id=LIVETEST_OPERATION_ID,
    )

    await podping_hivewriter.wait_startup()

    with pytest.raises(NotEnoughResourceCredits):
        await podping_hivewriter.send_notification_iri(iri, medium, reason)

    podping_hivewriter.close()

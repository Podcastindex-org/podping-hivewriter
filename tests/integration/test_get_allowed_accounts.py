import logging
import pytest

from podping_hivewriter.models.podping_settings import PodpingSettings
from podping_hivewriter.podping_hivewriter import get_allowed_accounts

from lighthive.client import Client
import nest_asyncio
from podping_hivewriter.async_wrapper import sync_to_async


@pytest.mark.asyncio
async def test_get_allowed_accounts():
    # Checks the allowed accounts checkup
    settings = PodpingSettings()
    allowed_accounts = get_allowed_accounts(settings.main_nodes)

    assert type(allowed_accounts) == set and len(allowed_accounts) > 0


@pytest.mark.asyncio
async def test_automatic_node_selection():
    nest_asyncio.apply()
    client = Client(automatic_node_selection=True, loglevel=logging.DEBUG)
    nodes = client.nodes
    current_node = client.current_node
    sorted_nodes = client.node_list
    raw_nodes = client._raw_node_list
    assert True
import asyncio
from datetime import datetime
import json
import logging
from sys import getsizeof
from timeit import default_timer as timer
from typing import Set, Tuple
import uuid

import beem
import zmq
import zmq.asyncio
from beem.account import Account
from beem.exceptions import AccountDoesNotExistsException, MissingKeyError
from beemapi.exceptions import UnhandledRPCError
from beem.nodelist import NodeList
from podping_hivewriter.podping_hivewriter import PodpingHivewriter

from pydantic import ValidationError

from podping_hivewriter.config import Config
from podping_hivewriter.models.podping_settings import PodpingSettings
from podping_hivewriter.podping_config import (
    get_podping_settings,
    get_time_sorted_node_list,
    get_hive,
)

from random import randint


async def update_podping_settings(acc_name: str) -> None:
    """Take newly found settings and put them into Config"""
    if Config.ignore_updates:
        return
    try:
        podping_settings = await get_podping_settings(acc_name, Config.posting_key)
    except ValidationError as e:
        logging.warning(f"Problem with podping control settings: {e}")
    else:
        if Config.podping_settings != podping_settings:
            logging.info("Configuration override from Podping Hive")
            Config.podping_settings = podping_settings


async def update_podping_settings_worker(acc_name: str) -> None:
    """Worker to check for changed settings every (period)"""
    while True:
        await update_podping_settings(acc_name)
        await asyncio.sleep(Config.podping_settings.control_account_check_period)


def run():
    logging.basicConfig(
        level=logging.INFO,
        format=f"%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )

    loop = asyncio.get_event_loop()

    Config.setup()

    if not Config.server_account:
        logging.error(
            "No Hive account passed: "
            "HIVE_SERVER_ACCOUNT environment var must be set."
        )

    if not Config.posting_key:
        logging.error(
            "No Hive Posting Key passed: "
            "HIVE_POSTING_KEY environment var must be set."
        )

    if not Config.test or Config.livetest:
        nodes = Config.podping_settings.test_nodes
    else:
        nodes = Config.podping_settings.main_nodes

    if Config.livetest:
        operation_id = "podping-livetest"
    else:
        operation_id = "podping"

    if Config.url:
        with PodpingHivewriter(
            Config.server_account,
            Config.posting_key,
            nodes,
            operation_id=operation_id,
            resource_test=False,
            daemon=False,
            use_testnet=Config.test,
        ) as podping_hivewriter:
            asyncio.run(podping_hivewriter.failure_retry({Config.url}))
        return

    podping_hivewriter = PodpingHivewriter(
        Config.server_account,
        Config.posting_key,
        nodes,
        operation_id=operation_id,
        use_testnet=Config.test,
    )

    podping_settings_task = None

    if not Config.ignore_updates:
        podping_settings_task = asyncio.create_task(
            update_podping_settings_worker(Config.podping_settings.control_account)
        )

    if not loop.is_running():  # pragma: no cover
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            loop.close()
    else:
        return podping_hivewriter, podping_settings_task


if __name__ == "__main__":
    run()

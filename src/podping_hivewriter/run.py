import asyncio
import logging

from podping_hivewriter.config import Config
from podping_hivewriter.constants import LIVETEST_OPERATION_ID, PODPING_OPERATION_ID
from podping_hivewriter.podping_hivewriter import PodpingHivewriter
from podping_hivewriter.podping_settings import (
    PodpingSettingsManager,
)


def run():
    logging.basicConfig(
        level=logging.INFO,
        format=f"%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )

    loop = asyncio.get_event_loop()

    if not Config.server_account:
        logging.error(
            "No Hive account passed: "
            "HIVE_SERVER_ACCOUNT environment var must be set."
        )

    if not Config.posting_keys:
        logging.error(
            "No Hive Posting Key passed: "
            "HIVE_POSTING_KEY environment var must be set."
        )

    if Config.livetest:
        operation_id = LIVETEST_OPERATION_ID
    else:
        operation_id = PODPING_OPERATION_ID

    settings_manager = PodpingSettingsManager(Config.ignore_updates)

    if Config.url:
        with PodpingHivewriter(
            Config.server_account,
            Config.posting_keys,
            settings_manager,
            operation_id=operation_id,
            resource_test=False,
            daemon=False,
        ) as podping_hivewriter:
            asyncio.run(podping_hivewriter.failure_retry({Config.url}))
        return

    podping_hivewriter = PodpingHivewriter(
        Config.server_account,
        Config.posting_keys,
        settings_manager,
        operation_id=operation_id,
    )

    if not loop.is_running():  # pragma: no cover
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            loop.close()
    else:
        return podping_hivewriter


if __name__ == "__main__":
    run()

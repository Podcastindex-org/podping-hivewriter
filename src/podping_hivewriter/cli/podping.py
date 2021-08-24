import asyncio
import logging
from typing import Optional, List

import typer

from podping_hivewriter import __version__
from podping_hivewriter.constants import LIVETEST_OPERATION_ID, PODPING_OPERATION_ID
from podping_hivewriter.podping_hivewriter import PodpingHivewriter
from podping_hivewriter.podping_settings import (
    PodpingSettingsManager,
)


def version_callback(value: bool):
    if value:
        typer.echo(__version__)
        raise typer.Exit()


app = typer.Typer()


@app.command()
def write(
    hive_account: str = typer.Option(
        ...,
        envvar=["PODPING_HIVE_ACCOUNT", "HIVE_ACCOUNT", "HIVE_SERVER_ACCOUNT"],
        help="Hive account used to post",
    ),
    hive_posting_key: str = typer.Option(
        ...,
        envvar=["PODPING_HIVE_POSTING_KEY", "HIVE_POSTING_KEY"],
        help="Hive account used to post",
    ),
    iri: List[str] = typer.Option(
        ...,
        envvar=["PODPING_IRI"],
        help="IRI to post to Hive. Can pass multiple. "
        "The environment variable currently only accepts one value",
    ),
    sanity_check: Optional[bool] = typer.Option(
        True,
        envvar="PODPING_SANITY_CHECK",
        help="By default, podping will test for available resources and the ability to "
        "post to the Hive chain on the given hive account at startup by posting "
        "startup information. Disabling this will result in a faster startup, "
        "time, but may result in unexpected errors.",
    ),
    livetest: Optional[bool] = typer.Option(
        False,
        envvar="PODPING_LIVETEST",
        help="Use live Hive chain but write with id=podping-livetest. "
        "Enable this if you want to validate posting to Hive "
        "without notifying podping watchers. Used internally for end-to-end tests.",
    ),
    ignore_config_updates: Optional[bool] = typer.Option(
        False,
        envvar="PODPING_IGNORE_CONFIG_UPDATES",
        help="By default, podping will periodically pull new settings from the "
        "configured Hive control account, allowing real time updates to adapt "
        "to changes in the Hive network. This lets you ignore these updates if needed.",
    ),
):
    logging.basicConfig(
        level=logging.INFO,
        format=f"%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )

    if livetest:
        operation_id = LIVETEST_OPERATION_ID
    else:
        operation_id = PODPING_OPERATION_ID

    settings_manager = PodpingSettingsManager(ignore_config_updates)

    with PodpingHivewriter(
        hive_account,
        [hive_posting_key],
        settings_manager,
        operation_id=operation_id,
        resource_test=sanity_check,
        daemon=False,
    ) as podping_hivewriter:
        asyncio.run(podping_hivewriter.failure_retry(set(iri)))
    typer.Exit()


@app.command()
def server(
    hive_account: str = typer.Option(
        ...,
        envvar=["PODPING_HIVE_ACCOUNT", "HIVE_ACCOUNT", "HIVE_SERVER_ACCOUNT"],
        help="Hive account used to post",
    ),
    hive_posting_key: str = typer.Option(
        ...,
        envvar=["PODPING_HIVE_POSTING_KEY", "HIVE_POSTING_KEY"],
        help="Hive account used to post",
    ),
    sanity_check: Optional[bool] = typer.Option(
        True,
        envvar="PODPING_SANITY_CHECK",
        help="By default, podping will test for available resources and the ability to "
        "post to the Hive chain on the given hive account at startup by posting "
        "startup information. Disabling this will result in a faster startup, "
        "time, but may result in unexpected errors.",
    ),
    livetest: Optional[bool] = typer.Option(
        False,
        envvar="PODPING_LIVETEST",
        help="Use live Hive chain but write with id=podping-livetest. "
        "Enable this if you want to validate posting to Hive "
        "without notifying podping watchers. Used internally for end-to-end tests.",
    ),
    ignore_config_updates: Optional[bool] = typer.Option(
        False,
        envvar="PODPING_IGNORE_CONFIG_UPDATES",
        help="By default, podping will periodically pull new settings from the "
        "configured Hive control account, allowing real time updates to adapt "
        "to changes in the Hive network. This lets you ignore these updates if needed.",
    ),
):
    logging.basicConfig(
        level=logging.INFO,
        format=f"%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )

    logging.info(f"podping {__version__} starting up in server mode")

    loop = asyncio.get_event_loop()

    if livetest:
        operation_id = LIVETEST_OPERATION_ID
    else:
        operation_id = PODPING_OPERATION_ID

    settings_manager = PodpingSettingsManager(ignore_config_updates)

    _podping_hivewriter = PodpingHivewriter(
        hive_account,
        [hive_posting_key],
        settings_manager,
        operation_id=operation_id,
        resource_test=sanity_check,
    )

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()
        typer.Exit()


@app.callback()
def callback(
    _: Optional[bool] = typer.Option(
        None, "--version", callback=version_callback, is_eager=True
    ),
):
    pass


if __name__ == "__main__":
    app()

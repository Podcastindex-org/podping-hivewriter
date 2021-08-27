import asyncio
import logging
from typing import Optional, List

import rfc3987
import typer

from podping_hivewriter import __version__
from podping_hivewriter.constants import LIVETEST_OPERATION_ID, PODPING_OPERATION_ID
from podping_hivewriter.podping_hivewriter import PodpingHivewriter
from podping_hivewriter.podping_settings_manager import PodpingSettingsManager


def iris_callback(iris: List[str]) -> List[str]:
    for iri in iris:
        if not rfc3987.match(iri, "IRI"):
            raise typer.BadParameter(
                """IRI is not valid. Must match rfc3987.
            Example: https://www.example.com/feed.xml
            Example (non-ascii): https://www.example.com/pódcast.xml
            Example (non-http): ipns://example.com/feed.xml"""
            )
    return iris


def version_callback(value: bool):
    if value:
        typer.echo(__version__)
        raise typer.Exit()


app = typer.Typer()


class Config:
    hive_account: str
    hive_posting_key: str
    sanity_check: bool
    livetest: bool
    dry_run: bool
    ignore_config_updates: bool
    debug: bool

    operation_id: str


def exit_cli(_):
    typer.Exit()


@app.command()
def write(
    iris: List[str] = typer.Argument(
        ...,
        metavar="IRI...",
        # TODO: "Typer" bug here with envvar and multiple values?  Can't get it to work
        envvar="PODPING_IRI",
        callback=iris_callback,
        help="One or more whitepace-separated IRIs to post to Hive. "
        "This will fail if you try to send too many at once.",
    ),
):
    settings_manager = PodpingSettingsManager(Config.ignore_config_updates)

    with PodpingHivewriter(
        Config.hive_account,
        [Config.hive_posting_key],
        settings_manager,
        operation_id=Config.operation_id,
        resource_test=Config.sanity_check,
        daemon=False,
        dry_run=Config.dry_run,
    ) as podping_hivewriter:
        coro = podping_hivewriter.failure_retry(set(iris))
        try:
            # Try to get an existing loop in case of running from other program
            # Mostly used for pytest
            loop = asyncio.get_running_loop()
            task = asyncio.ensure_future(coro, loop=loop)
            # Since we can't asynchronously wait, exit after finished
            task.add_done_callback(exit_cli)
        except RuntimeError as _:
            # If the loop isn't running, RuntimeError is raised.  Run normally
            loop = asyncio.get_event_loop()
            loop.run_until_complete(coro)
            typer.Exit()


@app.command()
def server(
    listen_ip: str = typer.Argument(
        "localhost",
        envvar="PODPING_LISTEN_IP",
        # TODO: Need validation here
        # callback=listen_ip_callback,
        help="IP to listen on. Should accept any ZeroMQ-compatible host string. "
        "WARNING: DO NOT run this on a publicly accessible host. "
        "There currently is NO authentication required to submit to the server. "
        "Set to * or 0.0.0.0 for all interfaces. IPv6 not currently supported.",
    ),
    listen_port: int = typer.Argument(
        9999,
        envvar="PODPING_LISTEN_PORT",
        # callback=iris_callback,
        help="Port to listen on.",
    ),
    status: Optional[bool] = typer.Option(
        True,
        help="Periodically prints a status message. "
        "Runs every diagnostic_report_period defined in podping_settings",
    ),
    i_know_what_im_doing: Optional[bool] = typer.Option(
        False,
        "--i-know-what-im-doing",
        help="Set this if you really want to listen on all interfaces.",
    ),
):
    logging.info(f"podping {__version__} starting up in server mode")
    if listen_ip in {"*", "0.0.0.0"} and not i_know_what_im_doing:  # nosec
        raise typer.BadParameter(
            "The listen-ip is configured to listen on all interfaces. "
            "Please read all server command line options."
        )

    settings_manager = PodpingSettingsManager(Config.ignore_config_updates)

    _podping_hivewriter = PodpingHivewriter(
        Config.hive_account,
        [Config.hive_posting_key],
        settings_manager,
        listen_ip=listen_ip,
        listen_port=listen_port,
        operation_id=Config.operation_id,
        resource_test=Config.sanity_check,
        dry_run=Config.dry_run,
        daemon=True,
        status=status,
    )

    try:
        # Try to get an existing loop in case of running from other program
        # Mostly used for pytest
        loop = asyncio.get_running_loop()
    except RuntimeError as _:
        # If the loop isn't running, RuntimeError is raised.  Run normally
        loop = asyncio.get_event_loop()
        loop.run_forever()
    except KeyboardInterrupt:
        typer.Exit()


@app.callback()
def callback(
    hive_account: str = typer.Option(
        ...,
        envvar=["PODPING_HIVE_ACCOUNT", "HIVE_ACCOUNT", "HIVE_SERVER_ACCOUNT"],
        help="Hive account used to post",
        prompt=True,
    ),
    hive_posting_key: str = typer.Option(
        ...,
        envvar=["PODPING_HIVE_POSTING_KEY", "HIVE_POSTING_KEY"],
        help="Hive account used to post",
        prompt=True,
        confirmation_prompt=True,
        hide_input=True,
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
    dry_run: Optional[bool] = typer.Option(
        False,
        envvar="PODPING_DRY_RUN",
        help="Run through all posting logic without posting to the chain.",
    ),
    ignore_config_updates: Optional[bool] = typer.Option(
        False,
        envvar="PODPING_IGNORE_CONFIG_UPDATES",
        help="By default, podping will periodically pull new settings from the "
        "configured Hive control account, allowing real time updates to adapt "
        "to changes in the Hive network. This lets you ignore these updates if needed.",
    ),
    debug: Optional[bool] = typer.Option(
        False,
        envvar="PODPING_DEBUG",
        help="Print debug log messages",
    ),
    _: Optional[bool] = typer.Option(
        None, "--version", callback=version_callback, is_eager=True
    ),
):
    Config.hive_account = hive_account
    Config.hive_posting_key = hive_posting_key
    Config.sanity_check = sanity_check
    Config.livetest = livetest
    Config.dry_run = dry_run
    Config.ignore_config_updates = ignore_config_updates
    Config.debug = debug

    logging.basicConfig(
        level=logging.INFO if not debug else logging.DEBUG,
        format=f"%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )

    if Config.livetest:
        Config.operation_id = LIVETEST_OPERATION_ID
    else:
        Config.operation_id = PODPING_OPERATION_ID


if __name__ == "__main__":
    app()
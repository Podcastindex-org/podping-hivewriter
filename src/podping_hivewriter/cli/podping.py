import asyncio
import logging
import sys
from typing import List, Optional

import rfc3987
import typer
from lighthive.broadcast.base58 import Base58

from podping_hivewriter import __version__
from podping_hivewriter.constants import (
    LIVETEST_OPERATION_ID,
    PODPING_OPERATION_ID,
    EXIT_CODE_INVALID_ACCOUNT,
    EXIT_CODE_INVALID_POSTING_KEY,
)
from podping_hivewriter.hive import get_client
from podping_hivewriter.models.medium import Medium, mediums, str_medium_map
from podping_hivewriter.models.reason import Reason, reasons, str_reason_map
from podping_hivewriter.podping_hivewriter import PodpingHivewriter
from podping_hivewriter.podping_settings_manager import PodpingSettingsManager


def is_base58(sb: str) -> bool:
    try:
        _ = Base58(sb)
        return True

    except Exception:
        return False


def medium_callback(medium: str) -> str:
    if medium not in mediums:
        raise typer.BadParameter(
            f"Medium be one of the following: {str(', '.join(mediums))}"
        )
    return medium


def reason_callback(reason: str) -> str:
    if reason not in reasons:
        raise typer.BadParameter(
            f"Reason must be one of the following: {str(', '.join(reasons))}"
        )
    return reason


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
    medium: Medium
    reason: Reason
    sanity_check: bool
    livetest: bool
    dry_run: bool
    status: bool
    ignore_config_updates: bool
    hive_operation_period: bool
    i_know_what_im_doing: bool
    debug: bool
    testnet: bool
    testnet_node: str
    testnet_chainid: str

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
    """
    Write one or more IRIs to the Hive blockchain without running a server.


    Example writing three IRIs:
    ```
    podping --hive-account <your-hive-account> --hive-posting-key <your-posting-key> --no-sanity-check write https://www.example.com/feed.xml https://www.example.com/pódcast.xml ipns://example.com/feed.xml

    2021-08-30T00:14:35-0500 | INFO | Hive account: @podping.test
    2021-08-30T00:14:35-0500 | INFO | Received 3 IRIs
    2021-08-30T00:14:37-0500 | INFO | Transaction sent: c9cbaace76ec365052c11ec4a3726e4ed3a7c54d - JSON size: 170
    ```

    Adding a Medium and Reason:
    ```
    podping --hive-account <your-hive-account> --hive-posting-key <your-posting-key> --no-dry-run --no-sanity-check write https://3speak.tv/rss/podping.xml --medium video --reason update
    ```


    Or add `--dry-run` to test functionality without broadcasting:
    ```
    podping --hive-account <your-hive-account> --hive-posting-key <your-posting-key> --dry-run --no-sanity-check write https://www.example.com/feed.xml

    2021-08-30T00:15:59-0500 | INFO | Hive account: @podping.test
    2021-08-30T00:15:59-0500 | INFO | Received 1 IRIs
    2021-08-30T00:16:00-0500 | INFO | Not broadcasting anything!
    2021-08-30T00:16:01-0500 | INFO | Transaction sent: 00eae43df4a202d94ef6cb797c05f39fbb50631b - JSON size: 97
    ```
    """
    settings_manager = PodpingSettingsManager(
        ignore_updates=Config.ignore_config_updates,
        hive_operation_period=Config.hive_operation_period,
    )

    with PodpingHivewriter(
        Config.hive_account,
        [Config.hive_posting_key],
        settings_manager,
        medium=Config.medium,
        reason=Config.reason,
        operation_id=Config.operation_id,
        resource_test=Config.sanity_check,
        daemon=False,
        dry_run=Config.dry_run,
    ) as podping_hivewriter:
        coro = podping_hivewriter.failure_retry(
            set(iris), medium=Config.medium, reason=Config.reason
        )
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
        "127.0.0.1",
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
):
    """
    Run a Podping server.  Listens for IRIs on the given address/port with ZeroMQ and
    submits them to the Hive blockchain in batches.

    Example with default localhost:9999 settings:
    ```
    podping --hive-account <your-hive-account> --hive-posting-key <your-posting-key> server

    2022-01-17T13:16:43+0200 | INFO | podping 1.1.0a1 starting up in server mode
    2022-01-17T13:16:44+0200 | INFO | Podping startup sequence initiated, please stand by, full bozo checks in operation...
    2022-01-17T13:16:45+0200 | INFO | Testing Account Resource Credits - before 99.73%
    2022-01-17T13:16:48+0200 | INFO | Calculating Account Resource Credits for 100 pings: 8.55% | Capacity: 1,169
    2022-01-17T13:16:49+0200 | INFO | Configuration override from Podping Hive: hive_operation_period=30 max_url_list_bytes=8000 diagnostic_report_period=180 control_account='podping' control_account_check_period=180 test_nodes=('https://testnet.openhive.network',)
    2022-01-17T13:16:51+0200 | INFO | Lighthive Node: https://api.hive.blog
    2022-01-17T13:16:51+0200 | INFO | JSON size: 179
    2022-01-17T13:16:51+0200 | INFO | Startup of Podping status: SUCCESS! Hit the BOOST Button.
    2022-01-17T13:16:53+0200 | INFO | Lighthive Fastest: https://api.deathwing.me
    2022-01-17T13:16:53+0200 | INFO | Hive account: @podping.bol
    2022-01-17T13:16:53+0200 | INFO | Running ZeroMQ server on 127.0.0.1:9999
    2022-01-17T13:16:54+0200 | INFO | Lighthive Fastest: https://api.deathwing.me
    2022-01-17T13:16:54+0200 | INFO | Status - Uptime: 0:00:10 | IRIs Received: 0 | IRIs Deduped: 0 | IRIs Sent: 0 | last_node: https://api.deathwing.me
    ```
    """

    try:
        import zmq
    except ImportError:
        raise typer.Exit(
            "Error: Missing pyzmq. Please reinstall podping with the server flag. "
            "Example: pipx install podping-hivewriter[server]"
        )

    logging.info(f"podping {__version__} starting up in server mode")

    if listen_ip in {"*", "0.0.0.0"} and not Config.i_know_what_im_doing:  # nosec
        raise typer.BadParameter(
            "The listen-ip is configured to listen on all interfaces. "
            "Please read all server command line options."
        )

    if listen_ip == "localhost":
        # ZMQ doesn't like the localhost string, force it to ipv4
        listen_ip = "127.0.0.1"

    settings_manager = PodpingSettingsManager(
        ignore_updates=Config.ignore_config_updates,
        hive_operation_period=Config.hive_operation_period,
    )

    _podping_hivewriter = PodpingHivewriter(
        Config.hive_account,
        [Config.hive_posting_key],
        settings_manager,
        medium=Config.medium,
        reason=Config.reason,
        listen_ip=listen_ip,
        listen_port=listen_port,
        operation_id=Config.operation_id,
        resource_test=Config.sanity_check,
        dry_run=Config.dry_run,
        daemon=True,
        status=Config.status,
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
    medium: str = typer.Option(
        str(Medium.podcast),
        envvar=["PODPING_MEDIUM"],
        callback=medium_callback,
        autocompletion=lambda: list(mediums),
        help=f"The medium of the feed being updated. If used in combination with the 'server', this sets the default "
        f"medium only. Must be one of the following: {str(' '.join(mediums))}",
    ),
    reason: str = typer.Option(
        str(Reason.update),
        envvar=["PODPING_REASON"],
        callback=reason_callback,
        autocompletion=lambda: list(reasons),
        help=f"The reason the feed is being updated. If used in combination with the 'server', this sets the default "
        f"reason only. Must be one of the following: {str(' '.join(reasons))}",
    ),
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
    status: Optional[bool] = typer.Option(
        True,
        envvar="PODPING_STATUS",
        help="Periodically prints a status message. "
        "Runs every diagnostic_report_period defined in podping_settings",
    ),
    hive_operation_period: Optional[int] = typer.Option(
        3,
        envvar="PODPING_HIVE_OPERATION_PERIOD",
        help="By default the Hivewriter will wait a few seconds gathering IRIs "
        "before sending the next batch. This balances resource usage against "
        "speed. If this is set here, the setting will override any settings "
        "sent by a config update.",
    ),
    ignore_config_updates: Optional[bool] = typer.Option(
        False,
        envvar="PODPING_IGNORE_CONFIG_UPDATES",
        help="By default, podping will periodically pull new settings from the "
        "configured Hive control account, allowing real time updates to adapt "
        "to changes in the Hive network. This lets you ignore these updates if needed.",
    ),
    i_know_what_im_doing: Optional[bool] = typer.Option(
        False,
        "--i-know-what-im-doing",
        envvar="PODPING_I_KNOW_WHAT_IM_DOING",
        help="Set this if you really want to listen on all interfaces.",
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
    Config.medium = str_medium_map[medium]
    Config.reason = str_reason_map[reason]
    Config.sanity_check = sanity_check
    Config.livetest = livetest
    Config.dry_run = dry_run
    Config.status = status
    Config.ignore_config_updates = ignore_config_updates
    Config.hive_operation_period = hive_operation_period
    Config.i_know_what_im_doing = i_know_what_im_doing
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

    # Check the account exists
    posting_keys = [hive_posting_key]
    client = get_client(posting_keys=posting_keys)
    account_exists = client.get_accounts([hive_account])
    if not account_exists:
        logging.error(
            f"Hive account @{hive_account} does not exist, "
            f"check ENV vars and try again"
        )
        logging.error("Exiting")
        sys.exit(EXIT_CODE_INVALID_ACCOUNT)

    if not is_base58(hive_posting_key):
        logging.error("Startup of Podping status: FAILED!")
        logging.error(
            "Posting Key not valid Base58 - check ENV vars and try again",
        )
        logging.error("Exiting")
        sys.exit(EXIT_CODE_INVALID_POSTING_KEY)


if __name__ == "__main__":
    app()

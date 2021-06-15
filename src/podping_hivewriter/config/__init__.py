import argparse
from asyncio import Queue
import logging

from pydantic import BaseModel
import os
from ipaddress import IPv4Address, IPv6Address, AddressValueError
from enum import Enum

from dataclasses import dataclass, field

# Testnet instead of main Hive
# BOL: Switching off TestNet, we should test on Hive for now.


# ---------------------------------------------------------------
# COMMAND LINE
# ---------------------------------------------------------------
from typing import List, Set

app_description = """ PodPing - Runs as a server and writes a stream of URLs to the
Hive Blockchain or sends a single URL to Hive (--url option)
Defaults to running the --zmq 9999 and binding only to localhost"""


my_parser = argparse.ArgumentParser(
    prog="hive-writer",
    usage="%(prog)s [options]",
    description=app_description,
    epilog="",
)


group_noise = my_parser.add_mutually_exclusive_group()
group_noise.add_argument("-q", "--quiet", action="store_true", help="Minimal output")
group_noise.add_argument("-v", "--verbose", action="store_true", help="Lots of output")


group_action_type = my_parser.add_mutually_exclusive_group()
group_action_type.add_argument(
    "-z",
    "--zmq",
    action="store",
    type=int,
    required=False,
    metavar="",
    default=9999,
    help="<IP:port> for ZMQ to listen on for each new url, returns, "
    "if IP is given, listens on that IP, otherwise only listens on localhost",
)

my_parser.add_argument(
    "-b",
    "--bindall",
    action="store_true",
    help="If given, bind the ZMQ listening port to *, if not given default binds ZMQ to localhost",
)

group_action_type.add_argument(
    "-u",
    "--url",
    action="store",
    type=str,
    required=False,
    metavar="",
    default=None,
    help="<url> Takes in a single URL and sends a single podping to Hive, "
    "needs HIVE_SERVER_ACCOUNT and HIVE_POSTING_KEY ENV variables set",
)

my_parser.add_argument(
    "-t", "--test", action="store_true", required=False, help="Use a test net API"
)

my_parser.add_argument(
    "-e",
    "--errors",
    action="store",
    type=int,
    required=False,
    metavar="",
    default=None,
    help="Deliberately force error rate of <int>%%",
)

args, _ = my_parser.parse_known_args()
my_args = vars(args)


class NotificationReasons(Enum):
    FEED_UPDATED = (1,)
    NEW_FEED = (2,)
    HOST_CHANGE = (3,)
    GOING_LIVE = 4


class PodpingSettings(BaseModel):
    """Dataclass for settings we will fetch from Hive"""

    hive_operation_period: int = 3
    max_url_list_bytes: int = 6000
    control_account: str = "podping"
    control_account_check_period: int = 60
    test_nodes: List[str] = ["https://testnet.openhive.network"]


class Config:
    """The Config Class"""

    # TEST_NODE = ["https://testnet.openhive.network"]
    CURRENT_PODPING_VERSION = 2
    podping_settings = PodpingSettings()

    # HIVE_OPERATION_PERIOD = 3  # 1 Hive operation per this period seconds
    # MAX_URL_LIST_BYTES = 7000  # Upper limit on custom_json is 8092 bytes

    # This is a global signal to shut down until RC's recover
    # Stores the RC cost of each operation to calculate an average
    # HALT_TIME = [1,2,3]
    HALT_TIME = [0, 1, 1, 1, 1, 1, 1, 1, 3, 6, 9, 15, 15, 15, 15, 15, 15, 15]

    # ---------------------------------------------------------------
    # START OF STARTUP SEQUENCE
    # ---------------------------------------------------------------
    # GLOBAL:
    server_account: str = os.getenv("HIVE_SERVER_ACCOUNT")
    posting_key: str = [os.getenv("HIVE_POSTING_KEY")]

    url: str = my_args["url"]
    zmq: str = my_args["zmq"]
    errors = my_args["errors"]
    bind_all = my_args["bindall"]

    # FROM ENV or from command line.
    test = os.getenv("USE_TEST_NODE", "False").lower() in ("true", "1", "t")
    if my_args["test"]:
        test = True

    @classmethod
    def setup(cls):
        """Setup the config"""

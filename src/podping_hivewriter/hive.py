import logging
import sys
from typing import List, Optional, Set

from lighthive.broadcast.base58 import Base58
from lighthive.broadcast.key_objects import PrivateKey
from lighthive.client import Client

from podping_hivewriter.constants import (
    STARTUP_FAILED_INVALID_ACCOUNT,
    STARTUP_FAILED_INVALID_POSTING_KEY_EXIT_CODE,
)


def get_client(
    posting_keys: Optional[List[str]] = None,
    nodes=None,
    connect_timeout=3,
    read_timeout=30,
    loglevel=logging.ERROR,
    chain=None,
) -> Client:
    try:
        client = Client(
            keys=posting_keys,
            nodes=nodes,
            connect_timeout=connect_timeout,
            read_timeout=read_timeout,
            loglevel=loglevel,
            chain=chain,
            automatic_node_selection=False,
        )
        return client
    except Exception as ex:
        raise ex


def get_allowed_accounts(
    client: Client = None, account_name: str = "podping"
) -> Set[str]:
    """get a list of all accounts allowed to post by acc_name (podping)
    and only react to these accounts"""

    if not client:
        client = get_client()

    master_account = client.account(account_name)
    return set(master_account.following())


def is_base58(sb: str) -> bool:
    try:
        _ = Base58(sb)
        return True

    except Exception:
        return False


def validate_account_info(hive_account: str, hive_posting_key: str):
    """Performs all the checks for a hive account and posting key"""

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
        sys.exit(STARTUP_FAILED_INVALID_ACCOUNT)

    if not is_base58(hive_posting_key):
        logging.error("Startup of Podping status: FAILED!")
        logging.error(
            "Posting Key not valid Base58 - check ENV vars and try again",
        )
        logging.error("Exiting")
        sys.exit(STARTUP_FAILED_INVALID_POSTING_KEY_EXIT_CODE)

    account = client.account(hive_account)
    public_keys = [a[0] for a in account.raw_data["posting"]["key_auths"]]
    try:
        private_key = PrivateKey(hive_posting_key)
        if not str(private_key.pubkey) in public_keys:
            logging.error("Startup of Podping status: FAILED!")
            logging.error(
                f"Posting Key doesn't match @{hive_account} - "
                f"check ENV vars and try again",
            )
            logging.error("Exiting")
            sys.exit(STARTUP_FAILED_INVALID_POSTING_KEY_EXIT_CODE)
    except Exception:
        logging.error("Startup of Podping status: FAILED!")
        logging.error(
            f"Some other error with keys for @{hive_account} - "
            f"check ENV vars and try again",
        )
        logging.error("Exiting")
        sys.exit(STARTUP_FAILED_INVALID_POSTING_KEY_EXIT_CODE)

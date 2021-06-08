import json
import logging
import threading
import time
from functools import partial
from queue import Empty
from random import randint
from sys import getsizeof
from typing import Set, Tuple

import zmq
import beem
from beem.account import Account
from beem.exceptions import AccountDoesNotExistsException, MissingKeyError
from beemapi.exceptions import UnhandledRPCError

from config import Config

logging.basicConfig(
    level=logging.INFO,
    format=f"%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s",
)


def startup_sequence(ignore_errors=False, resource_test=True) -> beem.Hive:
    """Run though a startup sequence connect to Hive and check env variables
    Exit with error unless ignore_errors passed as True
    Defaults to sending two startup resource_test posts and checking resources"""
    error_messages = []
    # Set up Hive with error checking
    logging.info(
        "Podping startup sequence initiated, please stand by, "
        "full bozo checks in operation..."
    )
    if not Config.server_account:
        error_messages.append(
            "No Hive account passed: HIVE_SERVER_ACCOUNT environment var must be set."
        )
        logging.error(error_messages[-1])

    if not Config.posting_key:
        error_messages.append(
            "No Hive Posting Key passed: HIVE_POSTING_KEY environment var must be set."
        )
        logging.error(error_messages[-1])

    try:
        if Config.test:
            hive = beem.Hive(keys=Config.posting_key, node=Config.TEST_NODE)
            logging.info("---------------> Using Test Node " + Config.TEST_NODE[0])
        else:
            hive = beem.Hive(keys=Config.posting_key)
            logging.info("---------------> Using Main Hive Chain ")

    except Exception as ex:
        error_messages.append(f"{ex} occurred {ex.__class__}")
        error_messages.append(f"Can not connect to Hive, probably bad key")
        logging.error(error_messages[-1])
        error_messages.append("I'm sorry, Dave, I'm afraid I can't do that")
        logging.error(error_messages[-1])
        exit_message = " - ".join(error_messages)
        raise SystemExit(exit_message)

    acc = None
    try:
        acc = Account(Config.server_account, blockchain_instance=hive, lazy=True)
        allowed = get_allowed_accounts()
        if Config.server_account not in allowed:
            error_messages.append(
                f"Account @{Config.server_account} not authorised to send Podpings"
            )
            logging.error(error_messages[-1])

    except AccountDoesNotExistsException:
        error_messages.append(
            f"Hive account @{Config.server_account} does not exist, "
            f"check ENV vars and try again AccountDoesNotExistsException"
        )
        logging.error(error_messages[-1])
    except Exception as ex:
        error_messages.append(f"{ex} occurred {ex.__class__}")
        logging.error(error_messages[-1])

    if resource_test:
        if acc:
            try:  # Now post two custom json to test.
                manabar = acc.get_rc_manabar()
                logging.info(
                    f"Testing Account Resource Credits"
                    f' - before {manabar.get("current_pct"):.2f}%'
                )
                custom_json = {
                    "server_account": Config.server_account,
                    "USE_TEST_NODE": Config.test,
                    "message": "Podping startup initiated",
                }
                error_message, success = send_notification(
                    custom_json, hive, "podping-startup"
                )

                if not success:
                    error_messages.append(error_message)
                logging.info("Testing Account Resource Credits.... 5s")
                time.sleep(2)
                manabar_after = acc.get_rc_manabar()
                logging.info(
                    f"Testing Account Resource Credits"
                    f' - after {manabar_after.get("current_pct"):.2f}%'
                )
                cost = manabar.get("current_mana") - manabar_after.get("current_mana")
                if cost == 0:  # skip this test if we're going to get ZeroDivision
                    capacity = 1000000
                else:
                    capacity = manabar_after.get("current_mana") / cost
                logging.info(f"Capacity for further podpings : {capacity:.1f}")
                custom_json["v"] = Config.CURRENT_PODPING_VERSION
                custom_json["capacity"] = f"{capacity:.1f}"
                custom_json["message"] = "Podping startup complete"
                error_message, success = send_notification(
                    custom_json, hive, "podping-startup"
                )
                if not success:
                    error_messages.append(error_message)

            except Exception as ex:
                error_messages.append(f"{ex} occurred {ex.__class__}")
                logging.error(error_messages[-1])

    if error_messages:
        error_messages.append("I'm sorry, Dave, I'm afraid I can't do that")
        logging.error(
            "Startup of Podping status: I'm sorry, Dave, I'm afraid I can't do that."
        )
        exit_message = " - ".join(error_messages)
        if not Config.test or ignore_errors:
            raise SystemExit(exit_message)

    logging.info("Startup of Podping status: SUCCESS! Hit the BOOST Button.")
    return hive

    # ---------------------------------------------------------------
    # END OF STARTUP SEQUENCE
    # ---------------------------------------------------------------


def url_in(url):
    """Send a URL and I'll post it to Hive"""
    Config.url_q.put(url)
    return "Sent", True


def get_allowed_accounts(acc_name="podping") -> Set[str]:
    """get a list of all accounts allowed to post by acc_name (podping)
    and only react to these accounts"""
    # Ignores test node.
    h = beem.Hive(node="https://api.hive.blog")
    master_account = Account(acc_name, blockchain_instance=h, lazy=True)
    return set(master_account.get_following())


def send_notification(
    data, hive: beem.Hive, operation_id="podping"
) -> Tuple[str, bool]:
    """Sends a custom_json to Hive
    Expects two env variables, Hive account name and posting key
    HIVE_SERVER_ACCOUNT
    HIVE_POSTING_KEY
    """
    num_urls = 0

    if type(data) == set:
        num_urls = len(data)
        size_of_urls = len("".join(data).encode("UTF-8"))
        custom_json = {
            "v": Config.CURRENT_PODPING_VERSION,
            "num_urls": num_urls,
            "r": Config.NOTIFICATION_REASONS["feed_update"],
            "urls": list(data),
        }
    elif type(data) == str:
        num_urls = 1
        size_of_urls = len(data.encode("UTF-8"))
        custom_json = {
            "v": Config.CURRENT_PODPING_VERSION,
            "num_urls": 1,
            "r": Config.NOTIFICATION_REASONS["feed_update"],
            "url": data,
        }
    elif type(data) == dict:
        size_of_urls = getsizeof(data)
        custom_json = data
    else:
        logging.error(f"Unknown data type: {data}")
        return f"Unknown data type: {data}", False

    try:
        # Artificially create errors <-----------------------------------
        if operation_id == "podping" and Config.errors:
            r = randint(1, 100)
            if r <= Config.errors:
                raise Exception(
                    f"Infinite Improbability Error level of {r}% : "
                    f"Threshold set at {Config.errors}%"
                )

        # Assert Exception:o.json.length() <= HIVE_CUSTOM_OP_DATA_MAX_LENGTH:
        # Operation JSON must be less than 8192 bytes.
        size_of_json = len(json.dumps(custom_json).encode("UTF-8"))
        tx = hive.custom_json(
            id=operation_id,
            json_data=custom_json,
            required_posting_auths=[Config.server_account],
        )
        trx_id = tx["trx_id"]
        logging.info(
            f"Transaction sent: {trx_id} - Num urls: {num_urls}"
            f" - Size of Urls: {size_of_urls} - Json size: {size_of_json}"
        )
        logging.info(f"Overhead: {size_of_json - size_of_urls}")
        return trx_id, True

    except MissingKeyError:
        error_message = f"The provided key for @{Config.server_account} is not valid "
        logging.error(error_message)
        return error_message, False
    except UnhandledRPCError as ex:
        error_message = f"{ex} occurred: {ex.__class__}"
        logging.error(error_message)
        trx_id = error_message
        return trx_id, False

    except Exception as ex:
        error_message = f"{ex} occurred {ex.__class__}"
        logging.error(error_message)
        trx_id = error_message
        return trx_id, False


def send_notification_worker(hive: beem.Hive):
    """Opens and watches a queue and sends notifications to Hive one by one"""
    while True:
        url_set = Config.hive_q.get()
        start = time.perf_counter()
        trx_id, failure_count = failure_retry(url_set, hive)
        # Limit the rate to 1 post every 2 seconds, this will mostly avoid
        # multiple updates in a single Hive block.
        duration = time.perf_counter() - start
        # if duration < 2.0:
        #     time.sleep(2.0-duration)
        Config.hive_q.task_done()
        logging.info(
            f"Task time: {duration:0.2f} - Queue size: " + str(Config.hive_q.qsize())
        )
        logging.info(f"Finished a task: {trx_id} - {failure_count}")


def url_q_worker():
    while True:
        url_set = set()
        start = time.perf_counter()
        duration = 0
        url_set_bytes = 0
        while (
            duration < Config.HIVE_OPERATION_PERIOD
            and url_set_bytes < Config.MAX_URL_LIST_BYTES
        ):
            #  get next URL from Q
            logging.debug(f"Duration: {duration:.3f} - WAITING - Queue: {len(url_set)}")
            try:
                url = Config.url_q.get(timeout=Config.HIVE_OPERATION_PERIOD)
                url_set.add(url)
                duration = time.perf_counter() - start
                logging.info(
                    f"Duration: {duration:.3f} - URL in queue: {url}"
                    f" - URL List: {len(url_set)}"
                )
                Config.url_q.task_done()
                url_set_bytes = len("".join(url_set).encode("UTF-8"))
            except Empty:
                break
            except Exception as ex:
                logging.error(f"{ex} occurred")

        if len(url_set):
            Config.hive_q.put(url_set)
            logging.info(f"Size of Urls: {url_set_bytes}")


# def url_in(url):
#     """ Send a URL and I'll post it to Hive """
#     custom_json = {'url': url}
#     hive_q.put( (send_notification, custom_json ))


def failure_retry(url_set, hive: beem.Hive, failure_count=0) -> Tuple[str, int]:
    if failure_count >= len(Config.HALT_TIME):
        # Give up.
        error_message = (
            f"I'm sorry Dave, I'm afraid I can't do that. "
            f"Too many tries {failure_count}"
        )
        logging.error(error_message)
        raise SystemExit(error_message)

    if failure_count > 0:
        logging.error(f"Waiting {Config.HALT_TIME[failure_count]}s")
        time.sleep(Config.HALT_TIME[failure_count])
        logging.info(f"RETRYING num_urls: {len(url_set)}")
    else:
        if type(url_set) == set:
            logging.info(f"Received num_urls: {len(url_set)}")
        elif type(url_set) == str:
            logging.info(f"One URL Received: {url_set}")
        else:
            logging.info(f"{url_set}")

    trx_id, success = send_notification(url_set, hive)
    if success:
        return trx_id, failure_count
    else:
        return failure_retry(url_set, hive, failure_count + 1)


def main() -> None:
    """Main man what counts..."""
    Config.setup()

    if Config.url:
        url = Config.url
        hive = startup_sequence(resource_test=False)
        if hive:
            failure_retry(url, hive)
        return

    hive = startup_sequence(resource_test=True)

    # Adding a Queue system to the Hive send_notification section
    threading.Thread(
        target=partial(send_notification_worker, hive), daemon=True
    ).start()

    # Adding a Queue system for holding URLs and sending them out
    threading.Thread(target=url_q_worker, daemon=True).start()

    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind(f"tcp://*:{Config.zmq}")
    while True:
        url_bytes: bytes = socket.recv_string()
        url: str = url_bytes.decode("utf-8")
        Config.url_q.put(url)
        ans = "OK"
        socket.send(ans.encode("utf-8"))

    # else:
    #     logging.error(
    #         "You've got to specify --socket or --zmq otherwise I can't listen!"
    #     )


if __name__ == "__main__":
    """Hit it!"""
    main()

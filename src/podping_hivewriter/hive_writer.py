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

from pydantic import ValidationError

from podping_hivewriter.config import Config
from podping_hivewriter.podping_config import (
    get_podping_settings,
    get_time_sorted_node_list,
)

from random import randint


class Pings:
    total_urls_recv = 0
    total_urls_sent = 0
    total_urls_recv_deduped = 0


def get_hive() -> beem.Hive:
    """Get the main Hive conneciton object"""
    posting_key = Config.posting_key
    nodes = Config.nodes_in_use
    if Config.test:
        hive = beem.Hive(keys=posting_key, node=nodes)
        logging.info(f"---------------> Using Test Nodes: {nodes}")
    else:
        hive = beem.Hive(node=nodes, keys=posting_key, nobroadcast=Config.nobroadcast)
        logging.info("---------------> Using Main Hive Chain ")
    return hive


async def hive_startup(ignore_errors=False, resource_test=True) -> beem.Hive:
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
        hive = get_hive()
        await update_podping_settings(Config.podping_settings.control_account)

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
                    "uuid": str(uuid.uuid4()),
                    "hive": repr(hive),
                }
                error_message, success = send_notification(
                    custom_json, hive, "podping-startup"
                )

                if not success:
                    error_messages.append(error_message)
                logging.info("Testing Account Resource Credits.... 5s")
                await asyncio.sleep(2)
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
                custom_json["hive"] = repr(hive)
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
        for err in error_message:
            logging.error(err)
        if not Config.test or ignore_errors:
            raise SystemExit(exit_message)

    logging.info("Startup of Podping status: SUCCESS! Hit the BOOST Button.")
    logging.info(
        f"---------------> {Config.server_account} <- Hive Account will be used"
    )

    return hive


def get_allowed_accounts(acc_name: str = "podping") -> Set[str]:
    """get a list of all accounts allowed to post by acc_name (podping)
    and only react to these accounts"""
    # Ignores test node.
    allowed = None
    for node in Config.podping_settings.main_nodes:
        try:
            hive = beem.Hive(node=Config.podping_settings.main_nodes)
            master_account = Account(acc_name, blockchain_instance=hive, lazy=True)
            allowed = set(master_account.get_following())
            break
        except Exception as e:
            logging.error(
                f"Allowed Account: {master_account} - Failure on Node: {node}"
            )
    return allowed

    # nodelist = NodeList()
    # nodelist.update_nodes()
    # nodes = nodelist.get_hive_nodes()
    # nodes.append("https://api.ha.deathwig.me")
    # # nodes = Config.podping_settings.main_nodes

    # for node in nodes:
    #     start = timer()
    #     h = beem.Hive(node=node)
    #     print(h)
    #     master_account = Account(acc_name, blockchain_instance=h, lazy=True)
    #     allowed = set(master_account.get_following())
    #     print(allowed)
    #     print(timer() - start)
    # return allowed


def send_notification(
    data, hive: beem.Hive, operation_id="podping", reason=1
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
            "r": reason,
            "urls": list(data),
        }
    elif type(data) == str:
        num_urls = 1
        size_of_urls = len(data.encode("UTF-8"))
        custom_json = {
            "v": Config.CURRENT_PODPING_VERSION,
            "num_urls": 1,
            "r": reason,
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
        Pings.total_urls_sent += num_urls
        logging.info(f"Overhead: {size_of_json - size_of_urls}")
        return trx_id, True

    except MissingKeyError:
        error_message = f"The provided key for @{Config.server_account} is not valid "
        logging.warning(repr(hive))
        logging.error(error_message)
        return error_message, False
    except UnhandledRPCError as ex:
        error_message = f"{ex} occurred: {ex.__class__}"
        logging.warning(repr(hive))
        logging.error(error_message)
        trx_id = error_message
        return trx_id, False

    except Exception as ex:
        error_message = f"{ex} occurred {ex.__class__}"
        logging.warning(repr(hive))
        logging.error(error_message)
        trx_id = error_message
        return trx_id, False


async def send_notification_worker(
    hive_queue: "asyncio.Queue[Set[str]]", hive: beem.Hive
):
    """Opens and watches a queue and sends notifications to Hive one by one"""

    async def rotate_node_list() -> Tuple[str, ...]:
        """Returns a rotated node list shifting primary node to end of list"""
        return tuple(list(Config.nodes_in_use)[1:] + list(Config.nodes_in_use)[:1])

    async def new_hive_object() -> beem.Hive:
        """Changes the hive object to use the nodes currently in Config"""
        new_node_list = await rotate_node_list()
        Config.nodes_in_use = new_node_list
        hive = beem.Hive(
            node=Config.nodes_in_use,
            keys=Config.posting_key,
            nobroadcast=Config.nobroadcast,
        )
        logging.info(f"New Hive Nodes in use: {hive}")
        return hive


    ### Alecks I have no idea how to make this run inside this function
    async def periodic_new_hive_object() -> beem.Hive:
        """Task to run in a loop that changes the order of nodes every x seconds"""
        asyncio.sleep(300)
        hive = await new_hive_object()
        return hive


    while True:
        try:
            url_set = await hive_queue.get()
        except asyncio.CancelledError:
            raise
        except RuntimeError:
            return
        start = timer()
        trx_id, failure_count = await failure_retry(url_set, hive)
        if failure_count > 0:
            # Rotate the node list and
            hive = await new_hive_object()

        duration = timer() - start
        hive_queue.task_done()
        logging.info(f"Task time: {duration:0.2f} - Queue size: {hive_queue.qsize()}")
        logging.info(f"Finished a task: {trx_id} - {failure_count}")


async def url_q_worker(
    url_queue: "asyncio.Queue[str]", hive_queue: "asyncio.Queue[Set[str]]"
):
    async def get_from_queue():
        try:
            return await url_queue.get()
        except RuntimeError:
            return

    while True:
        url_set: Set[str] = set()
        start = timer()
        duration = 0
        urls_size_without_commas = 0
        urls_size_total = 0

        # Wait until we have enough URLs to fit in the payload
        # or get into the current Hive block
        while (
            duration < Config.podping_settings.hive_operation_period
            and urls_size_total < Config.podping_settings.max_url_list_bytes
        ):
            #  get next URL from Q
            logging.debug(f"Duration: {duration:.3f} - WAITING - Queue: {len(url_set)}")
            try:
                url = await asyncio.wait_for(
                    get_from_queue(),
                    timeout=Config.podping_settings.hive_operation_period,
                )
                url_set.add(url)
                url_queue.task_done()

                logging.info(
                    f"Duration: {duration:.3f} - URL in queue: {url}"
                    f" - URL List: {len(url_set)}"
                )

                # byte size of URL in JSON is URL + 2 quotes
                urls_size_without_commas += len(url.encode("UTF-8")) + 2

                # Size of payload in bytes is
                # length of URLs in bytes + the number of commas + 2 square brackets
                # Assuming it's a JSON list eg ["https://...","https://"..."]
                urls_size_total = urls_size_without_commas + len(url_set) - 1 + 2
            except asyncio.TimeoutError:
                pass
            except asyncio.CancelledError:
                raise
            except RuntimeError:
                return
            except Exception as ex:
                logging.error(f"{ex} occurred")
            finally:
                # Always get the time of the loop
                duration = timer() - start

        try:
            if len(url_set):
                await hive_queue.put(url_set)
                Pings.total_urls_recv_deduped += len(url_set)
                logging.info(f"Size of Urls: {urls_size_total}")
        except asyncio.CancelledError:
            raise
        except RuntimeError:
            return
        except Exception as ex:
            logging.error(f"{ex} occurred")


async def failure_retry(
    url_set: Set[str], hive: beem.Hive, failure_count=0
) -> Tuple[str, int]:
    if failure_count >= len(Config.HALT_TIME):
        # Give up.
        error_message = (
            f"I'm sorry Dave, I'm afraid I can't do that. "
            f"Too many tries {failure_count}"
        )

        # Need code here to dump all URL's we've
        # received but not sent out to a file or the stdout

        logging.warning(repr(hive))
        logging.error(error_message)
        raise SystemExit(error_message)

    if failure_count > 0:
        logging.warning(repr(hive))
        logging.error(f"Waiting {Config.HALT_TIME[failure_count]}s")
        await asyncio.sleep(Config.HALT_TIME[failure_count])
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
        return await failure_retry(url_set, hive, failure_count + 1)


async def zmq_response_loop(url_queue: "asyncio.Queue[str]", loop=None):
    if not loop:
        loop = asyncio.get_event_loop()

    context = zmq.asyncio.Context()
    socket = context.socket(zmq.REP, io_loop=loop)
    if Config.bind_all:
        socket.bind(f"tcp://*:{Config.zmq}")
    else:
        socket.bind(f"tcp://127.0.0.1:{Config.zmq}")

    while True:
        try:
            url: str = await socket.recv_string()
            await url_queue.put(url)
            Pings.total_urls_recv += 1
            ans = "OK"
            await socket.send_string(ans)
        except asyncio.CancelledError:
            socket.close()
            raise


async def url_only_startup(url: str):
    hive = await hive_startup(resource_test=False)

    await failure_retry(set(url), hive)


def task_startup(hive: beem.Hive, loop=None):
    if not loop:  # pragma: no cover
        loop = asyncio.get_event_loop()

    # Adding a Queue system to the Hive send_notification section
    hive_queue: "asyncio.Queue[Set[str]]" = asyncio.Queue(loop=loop)
    # Move the URL Q into a proper Q
    url_queue: "asyncio.Queue[str]" = asyncio.Queue(loop=loop)

    loop.create_task(
        update_podping_settings_worker(Config.podping_settings.control_account)
    )
    loop.create_task(send_notification_worker(hive_queue, hive))
    loop.create_task(url_q_worker(url_queue, hive_queue))
    loop.create_task(zmq_response_loop(url_queue, loop))
    # hive = loop.create_future(
    #     output_hive_status_worker(hive, url_queue, hive_queue)
    # )
    # I want this coroutine running in the loop every hour (or however often)
    # to be able to "return" a new 'hive' object on which I've changed the
    # order of the API nodes based on timing.
    loop.create_task(output_hive_status_worker(hive, url_queue, hive_queue))


def loop_running_startup_task(hive_task: asyncio.Task):
    hive = hive_task.result()
    task_startup(hive)


async def update_podping_settings(acc_name: str) -> None:
    """Take newly found settings and put them into Config"""
    try:
        podping_settings = await get_podping_settings(
            acc_name, Config.podping_settings.main_nodes
        )
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


def output_hive_status(
    hive: beem.Hive,
    url_queue: "asyncio.Queue[str]",
    hive_queue: "asyncio.Queue[Set[str]]",
) -> None:
    """Output the name of the current hive node
    on a regular basis"""
    up_time = datetime.utcnow() - Config.startup_datetime
    logging.info("--------------------------------------------------------")
    logging.info(f"Using Hive Node: {hive}")
    logging.info(f"Up Time: {up_time}")
    logging.info(
        f"Urls Recived: {Pings.total_urls_recv} - "
        f"Urls Deduped: {Pings.total_urls_recv_deduped} - "
        f"Urls Sent: {Pings.total_urls_sent}"
    )
    # logging.info(f"URL Queue: {url_queue.qsize()} - Hive Queue: {hive_queue.qsize()}")
    logging.info("--------------------------------------------------------")


async def output_hive_status_worker(
    hive: beem.Hive,
    url_queue: "asyncio.Queue[str]",
    hive_queue: "asyncio.Queue[Set[str]]",
):
    """Worker to output the name of the current hive node
    on a regular basis"""

    while True:
        output_hive_status(hive, url_queue, hive_queue)
        # Right here I would change the hive object but I am stuck learning
        # Futures which I think is the way to do this!
        # hive = beem.Hive(node=node_list, keys=Config.posting_key)
        await asyncio.sleep(Config.podping_settings.diagnostic_report_period)


def run(loop=None):
    logging.basicConfig(
        level=logging.INFO,
        format=f"%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s",
    )

    if not loop:  # pragma: no cover
        loop = asyncio.new_event_loop()

    Config.setup()

    if Config.url:
        if loop.is_running():
            loop.create_task(url_only_startup(Config.url))
        else:
            asyncio.run(url_only_startup(Config.url))
        return

    if not loop.is_running():  # pragma: no cover
        try:
            hive = asyncio.run(hive_startup(resource_test=True))
            task_startup(hive, loop)
            loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            loop.close()
    else:
        hive_task = loop.create_task(hive_startup(resource_test=True))
        hive_task.add_done_callback(loop_running_startup_task)


if __name__ == "__main__":
    run()

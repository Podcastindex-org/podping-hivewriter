import asyncio
import itertools
import json
import logging
import re
import sys
import uuid
from datetime import datetime, timedelta
from timeit import default_timer as timer
from typing import List, Optional, Set, Tuple, Union

import rfc3987
from lighthive.datastructures import Operation
from lighthive.exceptions import RPCNodeException

from podping_hivewriter import __version__ as podping_hivewriter_version
from podping_hivewriter.async_context import AsyncContext
from podping_hivewriter.async_wrapper import sync_to_async
from podping_hivewriter.constants import (
    EXIT_CODE_INVALID_POSTING_KEY,
    EXIT_CODE_UNKNOWN,
    HIVE_CUSTOM_OP_DATA_MAX_LENGTH,
    STARTUP_OPERATION_ID,
    EXIT_CODE_STARTUP_ERROR,
    EXIT_CODE_STARTUP_RC_EXHAUSTED,
    EXIT_CODE_STARTUP_TOO_MANY_POSTS,
)
from podping_hivewriter.exceptions import (
    NotEnoughResourceCredits,
    PodpingCustomJsonPayloadExceeded,
    TooManyCustomJsonsPerBlock,
)
from podping_hivewriter.hive import get_allowed_accounts, get_client
from podping_hivewriter.models.hive_operation_id import HiveOperationId
from podping_hivewriter.models.iri_batch import IRIBatch
from podping_hivewriter.models.medium import Medium
from podping_hivewriter.models.podping import Podping
from podping_hivewriter.models.reason import Reason
from podping_hivewriter.podping_settings_manager import PodpingSettingsManager


class PodpingHivewriter(AsyncContext):
    def __init__(
        self,
        server_account: str,
        posting_keys: List[str],
        settings_manager: PodpingSettingsManager,
        medium: Medium = Medium.podcast,
        reason: Reason = Reason.update,
        listen_ip: str = "127.0.0.1",
        listen_port: int = 9999,
        operation_id="pp",
        resource_test=True,
        dry_run=False,
        daemon=True,
        status=True,
    ):
        super().__init__()

        self.server_account: str = server_account
        self.required_posting_auths = [self.server_account]
        self.settings_manager = settings_manager
        self.medium = medium
        self.reason = reason
        self.listen_ip = listen_ip
        self.listen_port = listen_port
        self.posting_keys: List[str] = posting_keys
        self.operation_id: str = operation_id
        self.resource_test: bool = resource_test
        self.dry_run: bool = dry_run
        self.daemon: bool = daemon
        self.status: bool = status

        self.lighthive_client = get_client(
            posting_keys=posting_keys,
            loglevel=logging.ERROR,
        )

        self._async_hive_broadcast = sync_to_async(
            self.lighthive_client.broadcast, thread_sensitive=False
        )

        self.total_iris_recv = 0
        self.total_iris_sent = 0
        self.total_iris_recv_deduped = 0

        self._iris_in_flight = 0
        self._iris_in_flight_lock = asyncio.Lock()

        self.iri_batch_queue: "asyncio.Queue[IRIBatch]" = asyncio.Queue()
        self.iri_queue: "asyncio.Queue[str]" = asyncio.Queue()

        self.startup_datetime = datetime.utcnow()
        self.startup_time = timer()

        self._startup_done = False
        asyncio.ensure_future(self._startup())

    async def _startup(self):

        try:
            settings = await self.settings_manager.get_settings()
            allowed = get_allowed_accounts(
                self.lighthive_client, settings.control_account
            )
            # TODO: Should we periodically check if the account is allowed
            #  and shut down if not?
            if self.server_account not in allowed:
                logging.error(
                    f"Account @{self.server_account} not authorised to send Podpings"
                )

        except Exception as ex:
            logging.exception("Unknown error occurred in _startup", stack_info=True)
            raise ex

        if self.resource_test and not self.dry_run:
            await self.test_hive_resources()

        logging.info(f"Hive account: @{self.server_account}")

        if self.daemon:
            self._add_task(asyncio.create_task(self._zmq_response_loop()))
            self._add_task(asyncio.create_task(self._iri_batch_loop()))
            self._add_task(asyncio.create_task(self._iri_batch_handler_loop()))
            if self.status:
                self._add_task(asyncio.create_task(self._hive_status_loop()))

        self._startup_done = True

    async def test_hive_resources(self):
        logging.info(
            "Podping startup sequence initiated, please stand by, "
            "full bozo checks in operation..."
        )

        # noinspection PyBroadException
        try:
            # post custom json to test.
            custom_json = {
                "server_account": self.server_account,
                "message": "Podping startup initiated",
                "uuid": str(uuid.uuid4()),
                "hive": str(self.lighthive_client.current_node),
            }

            startup_hive_operation_id = self.operation_id + STARTUP_OPERATION_ID

            self.construct_operation(custom_json, startup_hive_operation_id)

            custom_json["v"] = podping_hivewriter_version
            custom_json["message"] = "Podping startup complete"
            custom_json["hive"] = str(self.lighthive_client.current_node)

            startup_notification_attempts_max = len(self.lighthive_client.node_list)
            # Retry startup notification for every node before giving up
            for i in range(startup_notification_attempts_max):
                try:
                    await self.send_notification(custom_json, startup_hive_operation_id)
                    break
                except RPCNodeException:
                    if i == startup_notification_attempts_max - 1:
                        raise

            logging.info("Startup of Podping status: SUCCESS! Hit the BOOST Button.")

        except ValueError as ex:
            if str(ex) == "Error loading Base58 object":
                logging.exception(
                    "Startup of Podping status: FAILED!  Invalid posting key",
                    stack_info=True,
                )
                logging.error("Exiting")
                sys.exit(EXIT_CODE_INVALID_POSTING_KEY)
            else:
                logging.exception(
                    "Startup of Podping status: FAILED!  Unknown error", stack_info=True
                )
                logging.error("Exiting")
                sys.exit(EXIT_CODE_UNKNOWN)
        except NotEnoughResourceCredits:
            logging.exception(
                "Startup of Podping status: FAILED!  "
                "Not enough resource credits to post",
                stack_info=True,
            )
            logging.error("Exiting")
            sys.exit(EXIT_CODE_STARTUP_RC_EXHAUSTED)
        except TooManyCustomJsonsPerBlock:
            logging.exception(
                "Startup of Podping status: FAILED!  "
                "The given Hive account is is posting too quickly",
                stack_info=True,
            )
            logging.error("Exiting")
            sys.exit(EXIT_CODE_STARTUP_TOO_MANY_POSTS)
        except RPCNodeException:
            logging.exception(
                "Startup of Podping status: FAILED!  "
                "Unable to send startup notification",
                stack_info=True,
            )
            logging.error("Exiting")
            sys.exit(EXIT_CODE_STARTUP_ERROR)
        except Exception:
            logging.exception(
                "Startup of Podping status: FAILED!  Unknown error", stack_info=True
            )
            logging.error("Exiting")
            sys.exit(EXIT_CODE_UNKNOWN)

    async def wait_startup(self):
        settings = await self.settings_manager.get_settings()
        while not self._startup_done:
            await asyncio.sleep(settings.hive_operation_period)

    async def _hive_status_loop(self):
        while True:
            try:
                await self.output_hive_status()
                settings = await self.settings_manager.get_settings()
                await asyncio.sleep(settings.diagnostic_report_period)
            except asyncio.CancelledError:
                raise
            except Exception:
                logging.exception("Unknown in _hive_status_loop", stack_info=True)

    async def _iri_batch_handler_loop(self):
        """Opens and watches a queue and sends notifications to Hive one by one"""
        while True:
            try:
                iri_batch = await self.iri_batch_queue.get()

                start = timer()
                failure_count = await self.failure_retry(
                    iri_batch.iri_set, medium=self.medium, reason=self.reason
                )
                duration = timer() - start

                self.iri_batch_queue.task_done()
                async with self._iris_in_flight_lock:
                    self._iris_in_flight -= len(iri_batch.iri_set)

                last_node = self.lighthive_client.current_node
                logging.info(
                    f"Batch send time: {duration:0.2f} | "
                    f"Failures: {failure_count} - IRI batch_id {iri_batch.batch_id} | "
                    f"IRIs in batch: {len(iri_batch.iri_set)} | "
                    f"last_node: {last_node}"
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                logging.exception("Unknown in _iri_batch_handler_loop", stack_info=True)
                raise

    async def _iri_batch_loop(self):
        async def get_from_queue():
            try:
                return await self.iri_queue.get()
            except RuntimeError:
                return

        settings = await self.settings_manager.get_settings()

        while True:
            iri_set: Set[str] = set()
            start = timer()
            duration = 0
            iris_size_without_commas = 0
            iris_size_total = 0
            batch_id = uuid.uuid4()

            # Wait until we have enough IRIs to fit in the payload
            # or get into the current Hive block
            while (
                duration < settings.hive_operation_period
                and iris_size_total < settings.max_url_list_bytes
            ):
                try:
                    iri = await asyncio.wait_for(
                        get_from_queue(),
                        timeout=settings.hive_operation_period,
                    )
                    iri_set.add(iri)
                    self.iri_queue.task_done()

                    logging.debug(
                        f"_iri_batch_loop - Duration: {duration:.3f} - "
                        f"IRI in queue: {iri} - "
                        f"IRI batch_id {batch_id} - "
                        f"Num IRIs: {len(iri_set)}"
                    )

                    # byte size of IRI in JSON is IRI + 2 quotes
                    iris_size_without_commas += len(iri.encode("UTF-8")) + 2

                    # Size of payload in bytes is
                    # length of IRIs in bytes + the number of commas + 2 square brackets
                    # Assuming it's a JSON list eg ["https://...","https://"..."]
                    iris_size_total = iris_size_without_commas + len(iri_set) - 1 + 2
                except asyncio.TimeoutError:
                    pass
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logging.exception(
                        "Unknown error in _iri_batch_loop", stack_info=True
                    )
                    raise
                finally:
                    # Always get the time of the loop
                    duration = timer() - start

            try:
                if len(iri_set):
                    iri_batch = IRIBatch(batch_id=batch_id, iri_set=iri_set)
                    await self.iri_batch_queue.put(iri_batch)
                    self.total_iris_recv_deduped += len(iri_set)
                    logging.info(
                        f"IRI batch_id {batch_id} - Size of IRIs: {iris_size_total}"
                    )
            except asyncio.CancelledError:
                raise
            except Exception:
                logging.exception("Unknown error in _iri_batch_loop", stack_info=True)
                raise

    async def _zmq_response_loop(self):
        import zmq.asyncio

        context = zmq.asyncio.Context()
        socket = context.socket(zmq.REP)
        # TODO: Check IPv6 support
        socket.bind(f"tcp://{self.listen_ip}:{self.listen_port}")

        logging.info(f"Running ZeroMQ server on {self.listen_ip}:{self.listen_port}")

        while True:
            try:
                iri: str = await socket.recv_string()
                if rfc3987.match(iri, "IRI"):
                    await self.iri_queue.put(iri)
                    async with self._iris_in_flight_lock:
                        self._iris_in_flight += 1
                    self.total_iris_recv += 1
                    await socket.send_string("OK")
                else:
                    await socket.send_string("Invalid IRI")
            except asyncio.CancelledError:
                socket.close()
                raise
            except Exception:
                logging.exception(
                    "Unknown error in _zmq_response_loop", stack_info=True
                )
                raise

    async def num_operations_in_queue(self) -> int:
        async with self._iris_in_flight_lock:
            return self._iris_in_flight

    async def output_hive_status(self) -> None:
        """Output the name of the current hive node
        on a regular basis"""
        up_time = timedelta(seconds=int(timer() - self.startup_time))
        last_node = self.lighthive_client.current_node
        logging.info(
            f"Status - Uptime: {up_time} | "
            f"IRIs Received: {self.total_iris_recv} | "
            f"IRIs Deduped: {self.total_iris_recv_deduped} | "
            f"IRIs Sent: {self.total_iris_sent} | "
            f"last_node: {last_node}"
        )

    def construct_operation(
        self, payload: dict, hive_operation_id: Union[HiveOperationId, str]
    ) -> Tuple[Operation, int]:
        """Builed the operation for the blockchain"""
        payload_json = json.dumps(payload, separators=(",", ":"))
        size_of_json = len(payload_json)
        if size_of_json > HIVE_CUSTOM_OP_DATA_MAX_LENGTH:
            raise PodpingCustomJsonPayloadExceeded("Max custom_json payload exceeded")

        op = Operation(
            "custom_json",
            {
                "required_auths": [],
                "required_posting_auths": self.required_posting_auths,
                "id": str(hive_operation_id),
                "json": payload_json,
            },
        )
        return op, size_of_json

    async def send_notification(
        self, payload: dict, hive_operation_id: Union[HiveOperationId, str]
    ) -> None:
        """Build and send an operation to the blockchain"""
        try:
            op, size_of_json = self.construct_operation(payload, hive_operation_id)
            # if you want to FORCE the error condition for >5 operations
            # in one block, uncomment this line.
            # op = [op] * 6

            await self._async_hive_broadcast(op=op, dry_run=self.dry_run)

            logging.info(f"Lighthive Node: {self.lighthive_client.current_node}")
            logging.info(f"JSON size: {size_of_json}")
        except RPCNodeException as ex:
            logging.error(f"send_notification error: {ex}")
            try:
                if re.match(
                    r"plugin exception.*custom json.*",
                    ex.raw_body["error"]["message"],
                ):
                    raise TooManyCustomJsonsPerBlock()
                if re.match(
                    r".*not enough RC mana.*",
                    ex.raw_body["error"]["message"],
                ):
                    logging.error(ex.raw_body["error"]["message"])
                    raise NotEnoughResourceCredits()
                else:
                    raise ex
            except (KeyError, AttributeError):
                logging.error("Unexpected error format from Hive")
                raise ex
        except PodpingCustomJsonPayloadExceeded:
            raise
        except Exception:
            logging.exception("Unknown error in send_notification", stack_info=True)
            raise

    async def send_notification_iri(
        self,
        iri: str,
        medium: Optional[Medium],
        reason: Optional[Reason],
    ) -> None:
        payload = Podping(
            medium=medium or self.medium, reason=reason or self.reason, iris=[iri]
        )

        hive_operation_id = HiveOperationId(self.operation_id, medium, reason)

        await self.send_notification(payload.dict(), hive_operation_id)

        self.total_iris_sent += 1

    async def send_notification_iris(
        self,
        iris: Set[str],
        medium: Optional[Medium],
        reason: Optional[Reason],
    ) -> None:
        num_iris = len(iris)
        payload = Podping(
            medium=medium or self.medium, reason=reason or self.reason, iris=list(iris)
        )

        hive_operation_id = HiveOperationId(self.operation_id, medium, reason)

        await self.send_notification(payload.dict(), hive_operation_id)

        self.total_iris_sent += num_iris

    async def failure_retry(
        self,
        iri_set: Set[str],
        medium: Optional[Medium],
        reason: Optional[Reason],
    ) -> int:
        await self.wait_startup()
        failure_count = 0

        for _ in itertools.repeat(None):
            # Sleep a maximum of 5 minutes, 3 additional seconds for every retry
            if failure_count > 0:
                logging.info(
                    f"FAILURE COUNT: {failure_count} - RETRYING {len(iri_set)} IRIs"
                )
            else:
                logging.info(f"Received {len(iri_set)} IRIs")

            # noinspection PyBroadException
            try:
                await self.send_notification_iris(
                    iris=iri_set,
                    medium=medium or self.medium,
                    reason=reason or self.reason,
                )
                if failure_count > 0:
                    logging.info(f"FAILURE CLEARED after {failure_count} retries")
                return failure_count
            except RPCNodeException as ex:
                logging.error(f"Failed to send {len(iri_set)} IRIs")
                try:
                    # Test if we have a well-formed Hive error message
                    logging.error(ex)
                    if (
                        ex.raw_body["error"]["data"]["name"]
                        == "tx_missing_posting_auth"
                    ):
                        if logging.DEBUG >= logging.root.level:
                            for iri in iri_set:
                                logging.debug(iri)
                        logging.error(
                            f"Terminating: exit code: "
                            f"{EXIT_CODE_INVALID_POSTING_KEY}"
                        )
                        sys.exit(EXIT_CODE_INVALID_POSTING_KEY)
                except (KeyError, AttributeError):
                    logging.warning("Malformed error response")
            except NotEnoughResourceCredits as ex:
                logging.warning(ex)
                # 10s + exponential back off: need time for RC delegation
                # script to kick in
                sleep_for = 10 * 2**failure_count
                logging.warning(f"Sleeping for {sleep_for}s")
                await asyncio.sleep(sleep_for)
            except TooManyCustomJsonsPerBlock as ex:
                logging.warning(ex)
                # Wait for the next block to retry
                sleep_for = (
                    await self.settings_manager.get_settings()
                ).hive_operation_period
                logging.warning(f"Sleeping for {sleep_for}s")
                await asyncio.sleep(sleep_for)
            except Exception:
                logging.info(f"Current node: {self.lighthive_client.current_node}")
                logging.info(self.lighthive_client.nodes)
                logging.exception("Unknown error in failure_retry", stack_info=True)
                logging.error(f"Failed to send {len(iri_set)} IRIs")
                if logging.DEBUG >= logging.root.level:
                    for iri in iri_set:
                        logging.debug(iri)
                sys.exit(EXIT_CODE_UNKNOWN)
            finally:
                failure_count += 1

        return failure_count

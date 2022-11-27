import asyncio
import itertools
import json
import logging
import re
import sys
import uuid
from datetime import datetime, timedelta, timezone
from functools import partial
from timeit import default_timer as timer
from typing import List, Optional, Set, Tuple, Union, Dict, Iterable

import rfc3987
from lighthive.client import Client
from lighthive.datastructures import Operation
from lighthive.exceptions import RPCNodeException
from plexo.ganglion.tcp_pair import GanglionZmqTcpPair
from plexo.plexus import Plexus
from podping_schemas.org.podcastindex.podping.podping import Podping
from podping_schemas.org.podcastindex.podping.podping_medium import (
    PodpingMedium,
)
from podping_schemas.org.podcastindex.podping.podping_reason import (
    PodpingReason,
)

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
from podping_hivewriter.hive import get_client
from podping_hivewriter.models.hive_operation_id import HiveOperationId
from podping_hivewriter.models.iri_batch import IRIBatch
from podping_hivewriter.models.lighthive_broadcast_response import (
    LighthiveBroadcastResponse,
)
from podping_hivewriter.models.medium import mediums
from podping_hivewriter.models.internal_podping import InternalPodping
from podping_hivewriter.models.reason import reasons
from podping_hivewriter.neuron import (
    podping_hive_transaction_neuron,
    podping_write_neuron,
    podping_write_error_neuron,
)
from podping_hivewriter.podping_settings_manager import PodpingSettingsManager
from podping_schemas.org.podcastindex.podping.hivewriter.podping_hive_transaction import (
    PodpingHiveTransaction,
)
from podping_schemas.org.podcastindex.podping.podping_write import (
    PodpingWrite,
)
from podping_schemas.org.podcastindex.podping.podping_write_error import (
    PodpingWriteError,
    PodpingWriteErrorType,
)


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


def current_timestamp() -> float:
    # returns floating point timestamp in seconds
    return datetime.utcnow().replace(tzinfo=timezone.utc).timestamp()


def current_timestamp_nanoseconds() -> float:
    return current_timestamp() * 1e9


class PodpingHivewriter(AsyncContext):
    def __init__(
        self,
        server_account: str,
        posting_keys: List[str],
        settings_manager: PodpingSettingsManager,
        medium: PodpingMedium = PodpingMedium.podcast,
        reason: PodpingReason = PodpingReason.update,
        listen_ip: str = "127.0.0.1",
        listen_port: int = 9999,
        operation_id="pp",
        resource_test=True,
        dry_run=False,
        zmq_service=True,
        status=True,
        client: Client = None,
        plexus: Plexus = None,
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
        self.zmq_service: bool = zmq_service
        self.status: bool = status
        self.external_plexus = True if plexus else False
        self.plexus = plexus if plexus else Plexus()

        self.session_id = uuid.uuid4().int & (1 << 64) - 1

        self.lighthive_client = client or get_client(
            posting_keys=posting_keys,
            loglevel=logging.ERROR,
        )

        self._async_hive_broadcast = sync_to_async(
            self.lighthive_client.broadcast_sync, thread_sensitive=False
        )

        self.total_iris_recv = 0
        self.total_iris_sent = 0
        self.total_iris_recv_deduped = 0

        self.iri_batch_queue: "asyncio.PriorityQueue[IRIBatch]" = (
            asyncio.PriorityQueue()
        )
        self.unprocessed_iri_queue: asyncio.Queue[PodpingWrite] = asyncio.Queue(1000)
        self.iri_queues: Dict[
            Tuple[PodpingMedium, PodpingReason], asyncio.Queue[str]
        ] = {pair: asyncio.Queue() for pair in itertools.product(mediums, reasons)}

        self.startup_datetime = datetime.utcnow()
        self.startup_time = timer()

        self._startup_done = False
        asyncio.ensure_future(self._startup())

    def close(self):
        super().close()
        if not self.external_plexus:
            self.plexus.close()

    async def _startup(self):
        if self.resource_test and not self.dry_run:
            await self.test_hive_resources()

        logging.info(f"Hive account: @{self.server_account}")

        await self.plexus.adapt(podping_hive_transaction_neuron)
        await self.plexus.adapt(
            podping_write_neuron,
            reactants=(
                partial(
                    self._podping_write_reactant,
                    self.plexus,
                    self.unprocessed_iri_queue,
                ),
            ),
        )
        await self.plexus.adapt(podping_write_error_neuron)

        if self.zmq_service:
            tcp_pair_ganglion = GanglionZmqTcpPair(
                bind_interface=self.listen_ip,
                port=self.listen_port,
                relevant_neurons=(
                    podping_hive_transaction_neuron,
                    podping_write_neuron,
                    podping_write_error_neuron,
                ),
            )
            # tcp_pair_ganglion.socket.setsockopt(zmq.RCVHWM, 500)
            await self.plexus.infuse_ganglion(tcp_pair_ganglion)

        for (medium, reason), iri_queue in self.iri_queues.items():
            self._add_task(
                asyncio.create_task(
                    self._iri_batch_loop(
                        medium, reason, iri_queue, self.iri_batch_queue
                    )
                )
            )
        self._add_task(
            asyncio.create_task(self._iri_batch_handler_loop(self.iri_batch_queue))
        )
        self._add_task(
            asyncio.create_task(
                self._unprocessed_iri_queue_handler(
                    self.settings_manager,
                    self.iri_batch_queue,
                    self.unprocessed_iri_queue,
                    self.iri_queues,
                )
            )
        )
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
                "sessionId": self.session_id,
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
                    await self.broadcast_dict(custom_json, startup_hive_operation_id)
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
        settings = self.settings_manager.get_settings()
        while not self._startup_done:
            await asyncio.sleep(settings.hive_operation_period)

    async def _hive_status_loop(self):
        while True:
            try:
                await self.output_hive_status()
                settings = self.settings_manager.get_settings()
                await asyncio.sleep(settings.diagnostic_report_period)
            except asyncio.CancelledError:
                raise
            except Exception:
                logging.exception("Unknown in _hive_status_loop", stack_info=True)

    async def _iri_batch_handler_loop(
        self,
        iri_batch_queue: "asyncio.Queue[IRIBatch]",
    ):
        """Opens and watches a queue and sends notifications to Hive one by one"""

        session_id = self.session_id

        while True:
            try:
                settings = self.settings_manager.get_settings()

                start_time = timer()
                num_in_batch = 0
                batches = []
                # Limited to 5 custom json operation per block
                while not iri_batch_queue.empty() and num_in_batch < 5:
                    iri_batch = await iri_batch_queue.get()
                    batches.append(iri_batch)
                    iri_batch_queue.task_done()
                    logging.debug(
                        f"Handling Podping ({iri_batch.timestampNs}, {session_id})"
                    )
                    num_in_batch += 1

                if len(batches) > 0:
                    broadcast_start_time = timer()
                    failure_count, response = await self.broadcast_iri_batches_retry(
                        batches
                    )
                    broadcast_duration = timer() - broadcast_start_time

                    podpings = [
                        Podping(
                            medium=iri_batch.medium,
                            reason=iri_batch.reason,
                            iris=list(iri_batch.iri_set),
                            timestampNs=iri_batch.timestampNs,
                            sessionId=self.session_id,
                        )
                        for iri_batch in batches
                    ]

                    num_iris = sum(len(iri_batch.iri_set) for iri_batch in batches)

                    last_node = self.lighthive_client.current_node
                    if response:
                        for podping in podpings:
                            logging.info(
                                f"Podping ({podping.timestampNs}, {session_id}) | "
                                f"Hive txid: {response.hive_tx_id}"
                            )
                        logging.info(
                            f"TX send time: {broadcast_duration:0.2f} | "
                            f"Failures: {failure_count} | "
                            f"IRIs in TX: {num_iris} | "
                            f"Hive txid: {response.hive_tx_id} | "
                            f"Hive block num: {response.hive_block_num} | "
                            f"last_node: {last_node}"
                        )

                        await self.plexus.transmit(
                            PodpingHiveTransaction(
                                podpings=podpings,
                                hiveTxId=response.hive_tx_id,
                                hiveBlockNum=response.hive_block_num,
                            )
                        )

                        logging.debug(f"Transmitted TX: {response.hive_tx_id}")

                end_time = timer()
                sleep_time = settings.hive_operation_period - (end_time - start_time)
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
            except asyncio.CancelledError:
                raise
            except Exception:
                logging.exception(
                    "Unknown in _iri_batch_handler_loop",
                    stack_info=True,
                )
                raise

    async def _iri_batch_loop(
        self,
        medium: PodpingMedium,
        reason: PodpingReason,
        iri_queue: "asyncio.Queue[str]",
        iri_batch_queue: "asyncio.PriorityQueue[IRIBatch]",
    ):
        async def get_from_queue():
            try:
                return await iri_queue.get()
            except RuntimeError:
                return

        priority = 1

        if reason == PodpingReason.live:
            priority = -1
        elif reason == PodpingReason.liveEnd:
            priority = 0

        session_id = self.session_id

        while True:
            settings = self.settings_manager.get_settings()

            iri_set: Set[str] = set()
            start = timer()
            duration = 0
            iris_size_without_commas = 0
            iris_size_total = 0
            podping_timestamp = int(current_timestamp_nanoseconds())

            # Wait until we have enough IRIs to fit in the payload
            # or get into the current Hive block
            while (
                duration < settings.hive_operation_period
                or iri_batch_queue.qsize() >= 5
            ) and iris_size_total < settings.max_url_list_bytes:
                try:
                    iri = await asyncio.wait_for(
                        get_from_queue(),
                        timeout=settings.hive_operation_period,
                    )
                    iri_set.add(iri)
                    iri_queue.task_done()

                    logging.debug(
                        f"_iri_batch_loop | "
                        f"Podping ({podping_timestamp}, {session_id}) | "
                        f"Medium: {medium} - Reason: {reason} | "
                        f"Duration: {duration:.3f} | "
                        f"IRI in queue: {iri}"
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
                        f"Unknown error in _iri_batch_loop | "
                        f"Podping ({podping_timestamp}, {session_id}) | "
                        f"Medium: {medium} - Reason: {reason}",
                        stack_info=True,
                    )
                    raise
                finally:
                    # Always get the time of the loop
                    duration = timer() - start

            try:
                if len(iri_set):
                    iri_batch = IRIBatch(
                        medium=medium,
                        reason=reason,
                        iri_set=iri_set,
                        priority=priority,
                        timestampNs=podping_timestamp,
                    )
                    await iri_batch_queue.put(iri_batch)
                    self.total_iris_recv_deduped += len(iri_set)
                    logging.info(
                        f"Podping ({podping_timestamp}, {session_id}) | "
                        f"Medium: {medium} - Reason: {reason} | "
                        f"Size of IRIs: {iris_size_total}"
                    )
            except asyncio.CancelledError:
                raise
            except Exception:
                logging.exception(
                    f"Unknown error in _iri_batch_loop | "
                    f"Podping ({podping_timestamp}, {session_id}) | "
                    f"Medium: {medium} - Reason: {reason}",
                    stack_info=True,
                )
                raise

    async def _unprocessed_iri_queue_handler(
        self,
        settings_manager: PodpingSettingsManager,
        iri_batch_queue: "asyncio.PriorityQueue[IRIBatch]",
        unprocessed_iri_queue: "asyncio.Queue[PodpingWrite]",
        iri_queues: "Dict[Tuple[PodpingMedium, PodpingReason], asyncio.Queue[str]]",
    ):
        while True:
            try:
                podping_write: PodpingWrite = await unprocessed_iri_queue.get()
                queue = iri_queues[(podping_write.medium, podping_write.reason)]
                await queue.put(podping_write.iri)
                unprocessed_iri_queue.task_done()
                self.total_iris_recv += 1

                qsize = iri_batch_queue.qsize()

                if qsize >= 10:
                    logging.debug(
                        f"_unprocessed_iri_queue_handler | "
                        f"unprocessed_iri_queue size: {unprocessed_iri_queue.qsize()}"
                    )
                    logging.debug(
                        f"_unprocessed_iri_queue_handler | "
                        f"iri_batch_queue size: {qsize}"
                    )
                    op_period = settings_manager.get_settings().hive_operation_period
                    logging.debug(
                        f"_unprocessed_iri_queue_handler | "
                        f"Sleeping for {op_period}s"
                    )
                    await asyncio.sleep(op_period)
            except asyncio.TimeoutError:
                pass
            except asyncio.CancelledError:
                raise
            except Exception:
                logging.exception(
                    f"Unknown error in _unprocessed_iri_queue_handler",
                    stack_info=True,
                )
                raise

    @staticmethod
    async def _podping_write_reactant(
        plexus: Plexus,
        unprocessed_iri_queue: "asyncio.Queue[PodpingWrite]",
        podping_write: PodpingWrite,
        _,
        _2,
    ):
        if rfc3987.match(podping_write.iri, "IRI"):
            await unprocessed_iri_queue.put(podping_write)
        else:
            podping_write_error = PodpingWriteError(
                podpingWrite=podping_write,
                errorType=PodpingWriteErrorType.invalidIri,
            )
            await plexus.transmit(podping_write_error)

    async def send_podping(
        self,
        iri: str,
        medium: Optional[PodpingMedium],
        reason: Optional[PodpingReason],
    ):
        podping_write = PodpingWrite(
            medium=medium or self.medium,
            reason=reason or self.reason,
            iri=iri,
        )

        await self.plexus.transmit(podping_write)

    async def num_operations_in_queue(self) -> int:
        return (
            sum(queue.qsize() for queue in self.iri_queues.values())
            + self.iri_batch_queue.qsize()
        )

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

    def construct_operations(
        self,
        payload_operation_ids: Iterable[Tuple[dict, Union[HiveOperationId, str]]],
    ) -> List[Operation]:
        """Build the operation for the blockchain"""

        operations: List[Operation] = []

        for payload, hive_operation_id in payload_operation_ids:
            payload_json = json.dumps(payload, separators=(",", ":"))
            size_of_json = len(payload_json)
            if size_of_json > HIVE_CUSTOM_OP_DATA_MAX_LENGTH:
                raise PodpingCustomJsonPayloadExceeded(
                    "Max custom_json payload exceeded"
                )

            op = Operation(
                "custom_json",
                {
                    "required_auths": [],
                    "required_posting_auths": self.required_posting_auths,
                    "id": str(hive_operation_id),
                    "json": payload_json,
                },
            )

            operations.append(op)

        return operations

    def construct_operation(
        self, payload: dict, hive_operation_id: Union[HiveOperationId, str]
    ) -> Operation:
        return self.construct_operations(((payload, hive_operation_id),))[0]

    async def broadcast_dicts(
        self,
        payload_operation_ids: Iterable[Tuple[dict, Union[HiveOperationId, str]]],
    ) -> LighthiveBroadcastResponse:
        """Build and send an operation to the blockchain"""
        try:
            ops = self.construct_operations(payload_operation_ids)
            # if you want to FORCE the error condition for >5 operations
            # in one block, uncomment this line.
            # op = [op] * 6

            broadcast_task = asyncio.create_task(
                self._async_hive_broadcast(op=ops, dry_run=self.dry_run)
            )

            logging.info(f"Lighthive Node: {self.lighthive_client.current_node}")

            return LighthiveBroadcastResponse(await broadcast_task)
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
        except KeyError:
            if self.dry_run:
                return LighthiveBroadcastResponse(
                    {"id": "0", "block_num": 0, "trx_num": 0, "expired": False}
                )
            else:
                logging.exception("Unknown error in send_notification", stack_info=True)
                raise
        except Exception:
            logging.exception("Unknown error in send_notification", stack_info=True)
            raise

    async def broadcast_dict(
        self, payload: dict, hive_operation_id: Union[HiveOperationId, str]
    ) -> LighthiveBroadcastResponse:
        return await self.broadcast_dicts(((payload, hive_operation_id),))

    async def broadcast_iri_batches(
        self,
        iri_batches: Iterable[IRIBatch],
    ) -> LighthiveBroadcastResponse:
        num_iris = sum(len(iri_batch.iri_set) for iri_batch in iri_batches)
        payload_operation_ids = (
            (
                InternalPodping(
                    medium=iri_batch.medium,
                    reason=iri_batch.reason,
                    iris=list(iri_batch.iri_set),
                    timestampNs=iri_batch.timestampNs,
                    sessionId=self.session_id,
                ).dict(),
                HiveOperationId(self.operation_id, iri_batch.medium, iri_batch.reason),
            )
            for iri_batch in iri_batches
        )

        response = await self.broadcast_dicts(payload_operation_ids)

        self.total_iris_sent += num_iris

        return response

    async def broadcast_iri(
        self,
        iri: str,
        medium: Optional[PodpingMedium],
        reason: Optional[PodpingReason],
    ) -> LighthiveBroadcastResponse:
        payload = InternalPodping(
            medium=medium or self.medium,
            reason=reason or self.reason,
            iris=[iri],
            timestampNs=int(current_timestamp_nanoseconds()),
            sessionId=self.session_id,
        )

        hive_operation_id = HiveOperationId(self.operation_id, medium, reason)

        response = await self.broadcast_dict(payload.dict(), hive_operation_id)

        self.total_iris_sent += 1

        return response

    async def broadcast_iris(
        self,
        iri_set: Set[str],
        medium: Optional[PodpingMedium],
        reason: Optional[PodpingReason],
    ) -> LighthiveBroadcastResponse:
        num_iris = len(iri_set)
        timestamp = int(current_timestamp_nanoseconds())
        payload_dict = InternalPodping(
            medium=medium or self.medium,
            reason=reason or self.reason,
            iris=list(iri_set),
            timestampNs=timestamp,
            sessionId=self.session_id,
        ).dict()

        hive_operation_id = HiveOperationId(self.operation_id, medium, reason)

        response = await self.broadcast_dict(payload_dict, hive_operation_id)

        self.total_iris_sent += num_iris

        return response

    async def broadcast_iri_batches_retry(
        self,
        iri_batches: Iterable[IRIBatch],
    ) -> Tuple[int, Optional[LighthiveBroadcastResponse]]:
        await self.wait_startup()
        failure_count = 0

        for _ in itertools.repeat(None):
            num_iris = sum(len(iri_batch.iri_set) for iri_batch in iri_batches)
            if failure_count > 0:
                logging.info(
                    f"FAILURE COUNT: {failure_count} - RETRYING {num_iris} IRIs"
                )
            else:
                logging.info(f"Received {num_iris} IRIs")

            # noinspection PyBroadException
            try:
                response = await self.broadcast_iri_batches(iri_batches=iri_batches)
                if failure_count > 0:
                    logging.info(f"FAILURE CLEARED after {failure_count} retries")
                return failure_count, response
            except RPCNodeException as ex:
                logging.error(f"Failed to send {num_iris} IRIs")
                try:
                    # Test if we have a well-formed Hive error message
                    logging.error(ex)
                    if (
                        ex.raw_body["error"]["data"]["name"]
                        == "tx_missing_posting_auth"
                    ):
                        if logging.DEBUG >= logging.root.level:
                            for iri in itertools.chain.from_iterable(
                                iri_batch.iri_set for iri_batch in iri_batches
                            ):
                                logging.debug(iri)
                        logging.error(
                            f"Terminating: exit code: "
                            f"{EXIT_CODE_INVALID_POSTING_KEY}"
                        )
                        sys.exit(EXIT_CODE_INVALID_POSTING_KEY)
                except (KeyError, AttributeError):
                    logging.warning("Malformed error response")
                    self.lighthive_client.circuit_breaker_cache[
                        self.lighthive_client.current_node
                    ] = True
                    logging.warning(
                        "Ignoring node %s for %d seconds",
                        self.lighthive_client.current_node,
                        self.lighthive_client.circuit_breaker_ttl,
                    )
                    self.lighthive_client.next_node()
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
                sleep_for = (self.settings_manager.get_settings()).hive_operation_period
                logging.warning(f"Sleeping for {sleep_for}s")
                await asyncio.sleep(sleep_for)
            except Exception:
                logging.info(f"Current node: {self.lighthive_client.current_node}")
                logging.info(self.lighthive_client.nodes)
                logging.exception("Unknown error in failure_retry", stack_info=True)
                logging.error(f"Failed to send {num_iris} IRIs")
                if logging.DEBUG >= logging.root.level:
                    for iri in itertools.chain.from_iterable(
                        iri_batch.iri_set for iri_batch in iri_batches
                    ):
                        logging.debug(iri)
                sys.exit(EXIT_CODE_UNKNOWN)
            finally:
                failure_count += 1

        return failure_count, None

    async def broadcast_iris_retry(
        self,
        iri_set: Set[str],
        medium: Optional[PodpingMedium],
        reason: Optional[PodpingReason],
    ) -> Tuple[int, Optional[LighthiveBroadcastResponse]]:
        return await self.broadcast_iri_batches_retry(
            (
                IRIBatch(
                    iri_set=iri_set,
                    medium=medium or self.medium,
                    reason=reason or self.reason,
                    priority=0,
                    timestampNs=int(current_timestamp_nanoseconds()),
                ),
            )
        )

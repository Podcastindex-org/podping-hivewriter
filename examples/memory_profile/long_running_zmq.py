import asyncio
import linecache
import logging
import os
import random
import uuid
from ipaddress import IPv4Address

from plexo.ganglion.tcp_pair import GanglionZmqTcpPair
from plexo.plexus import Plexus
from podping_schemas.org.podcastindex.podping.hivewriter.podping_hive_transaction import (
    PodpingHiveTransaction,
)
from podping_schemas.org.podcastindex.podping.podping_medium import PodpingMedium
from podping_schemas.org.podcastindex.podping.podping_reason import PodpingReason
from podping_schemas.org.podcastindex.podping.podping_write import PodpingWrite

from podping_hivewriter.models.medium import mediums
from podping_hivewriter.models.reason import reasons
from podping_hivewriter.neuron import (
    podping_hive_transaction_neuron,
    podping_write_neuron,
)

try:
    import tracemalloc
except ModuleNotFoundError:
    tracemalloc = False
from platform import python_version as pv, python_implementation as pi
from timeit import default_timer as timer

host = "127.0.0.1"
port = 9979
metrics = {"iris_sent": 0, "ops_received": 0, "iris_received": 0, "txs_received": 0}
txs_received_lock = asyncio.Lock()


def display_top(snapshot, key_type="lineno", limit=3):
    snapshot = snapshot.filter_traces(
        (
            tracemalloc.Filter(False, "<frozen importlib._bootstrap>"),
            tracemalloc.Filter(False, "<unknown>"),
        )
    )
    top_stats = snapshot.statistics(key_type)

    logging.info("Top %s lines" % limit)
    for index, stat in enumerate(top_stats[:limit], 1):
        frame = stat.traceback[0]
        # replace "/path/to/module/file.py" with "module/file.py"
        filename = os.sep.join(frame.filename.split(os.sep)[-2:])
        logging.info(
            "#%s: %s:%s: %.1f KiB" % (index, filename, frame.lineno, stat.size / 1024)
        )
        line = linecache.getline(frame.filename, frame.lineno).strip()
        if line:
            logging.info("    %s" % line)

    other = top_stats[limit:]
    if other:
        size = sum(stat.size for stat in other)
        logging.info("%s other: %.1f KiB" % (len(other), size / 1024))
    total = sum(stat.size for stat in top_stats)
    logging.info("Total allocated size: %.1f KiB" % (total / 1024))


async def podping_hive_transaction_reaction(transaction: PodpingHiveTransaction, _, _2):
    num_iris = sum(len(podping.iris) for podping in transaction.podpings)

    async with txs_received_lock:
        metrics["ops_received"] = metrics["ops_received"] + len(transaction.podpings)
        metrics["iris_received"] = metrics["iris_received"] + num_iris
        metrics["txs_received"] = metrics["txs_received"] + 1


async def endless_send_loop(event_loop):
    tcp_pair_ganglion = GanglionZmqTcpPair(
        peer=(IPv4Address(host), port),
        relevant_neurons=(
            podping_hive_transaction_neuron,
            podping_write_neuron,
        ),
    )
    plexus = Plexus(ganglia=(tcp_pair_ganglion,))
    await plexus.adapt(
        podping_hive_transaction_neuron,
        reactants=(podping_hive_transaction_reaction,),
    )
    await plexus.adapt(podping_write_neuron)

    start_time = timer()
    diag_time = timer()

    while True:
        loop_start = timer()
        # for _ in range(10):
        session_uuid = uuid.uuid4()
        session_uuid_str = str(session_uuid)

        for i in range(1000):
            iri = f"https://example.com?t=agates_test&i={i}s={session_uuid_str}"
            medium: PodpingMedium = random.sample(sorted(mediums), 1)[0]
            reason: PodpingReason = random.sample(sorted(reasons), 1)[0]
            podping_write = PodpingWrite(medium=medium, reason=reason, iri=iri)

            await plexus.transmit(podping_write)

        metrics["iris_sent"] = metrics["iris_sent"] + 1000

        await asyncio.sleep(3 - (timer() - loop_start))
        if tracemalloc and (timer() - diag_time) >= 60:
            snapshot = tracemalloc.take_snapshot()
            display_top(snapshot)
            diag_time = timer()
            logging.info(
                f"IRIs sent: {metrics['iris_sent']} - {metrics['iris_sent'] / (diag_time - start_time)}s"
            )
            logging.info(
                f"TXs received: {metrics['txs_received']} - {metrics['txs_received'] / (diag_time - start_time)}s"
            )
            logging.info(
                f"OPs received: {metrics['ops_received']} - {metrics['ops_received'] / (diag_time - start_time)}s"
            )
            logging.info(
                f"IRIs received: {metrics['iris_received']} - {metrics['iris_received'] / (diag_time - start_time)}s"
            )


if __name__ == "__main__":
    if tracemalloc:
        tracemalloc.start()
    loop = asyncio.get_event_loop()
    logging.getLogger().setLevel(level=logging.INFO)

    loop.run_until_complete(endless_send_loop(loop))

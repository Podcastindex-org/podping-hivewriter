import asyncio
import linecache
import logging
import os

try:
    import tracemalloc
except ModuleNotFoundError:
    tracemalloc = False
import uuid
from random import randint
from platform import python_version as pv, python_implementation as pi
from timeit import default_timer as timer

import zmq
import zmq.asyncio

from podping_hivewriter.constants import LIVETEST_OPERATION_ID
from podping_hivewriter.models.medium import Medium
from podping_hivewriter.models.reason import Reason
from podping_hivewriter.podping_hivewriter import PodpingHivewriter
from podping_hivewriter.podping_settings_manager import PodpingSettingsManager


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


async def endless_send_loop(event_loop):
    context = zmq.asyncio.Context()
    socket = context.socket(zmq.REQ, io_loop=event_loop)
    socket.connect(f"tcp://{host}:{port}")

    test_name = "long_running_zmq"
    python_version = pv()
    python_implementation = pi()
    start_time = timer()

    while True:
        session_uuid = uuid.uuid4()
        session_uuid_str = str(session_uuid)

        num_iris = randint(1, 10)

        for i in range(num_iris):
            await socket.send_string(
                f"https://example.com?t={test_name}&i={i}&v={python_version}&pi={python_implementation}&s={session_uuid_str}"
            )
            response = await socket.recv_string()
            assert response == "OK"

        if tracemalloc and (timer() - start_time) >= 60:
            snapshot = tracemalloc.take_snapshot()
            display_top(snapshot)
            start_time = timer()
        await asyncio.sleep(3)


if __name__ == "__main__":
    if tracemalloc:
        tracemalloc.start()
    loop = asyncio.get_event_loop()
    logging.getLogger().setLevel(level=logging.INFO)
    settings_manager = PodpingSettingsManager()

    host = "127.0.0.1"
    port = 9979
    podping_hivewriter = PodpingHivewriter(
        os.environ["PODPING_HIVE_ACCOUNT"],
        [os.environ["PODPING_HIVE_POSTING_KEY"]],
        settings_manager,
        medium=Medium.podcast,
        reason=Reason.update,
        listen_ip=host,
        listen_port=port,
        resource_test=True,
        operation_id=LIVETEST_OPERATION_ID,
    )
    loop.run_until_complete(podping_hivewriter.wait_startup())
    loop.run_until_complete(endless_send_loop(loop))

    podping_hivewriter.close()

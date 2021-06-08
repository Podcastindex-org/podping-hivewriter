import os

import zmq

from src.podping_hivewriter import hive_writer, config


def test_write_single_url_zmq_req():
    # Ensure use of testnet
    config.Config.test = True

    hive_writer.main()

    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.connect(f"tcp://*:{config.Config.zmq}")

    socket.send_string("https://example.com")

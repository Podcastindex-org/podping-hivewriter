from plexo.neuron.neuron import Neuron

from podping_hivewriter.codec.podping_codec import (
    podping_write_codec,
    podping_write_error_codec,
    podping_hive_transaction_codec,
)
from podping_hivewriter.namespace import podping_hivewriter_namespace
from podping_schemas.org.podcastindex.podping.hivewriter.podping_hive_transaction import (
    PodpingHiveTransaction,
)
from podping_schemas.org.podcastindex.podping.podping_write import (
    PodpingWrite,
)
from podping_schemas.org.podcastindex.podping.podping_write_error import (
    PodpingWriteError,
)

podping_hive_transaction_neuron = Neuron(
    PodpingHiveTransaction,
    podping_hivewriter_namespace,
    podping_hive_transaction_codec,
)
podping_write_neuron = Neuron(
    PodpingWrite, podping_hivewriter_namespace, podping_write_codec
)
podping_write_error_neuron = Neuron(
    PodpingWriteError,
    podping_hivewriter_namespace,
    podping_write_error_codec,
)

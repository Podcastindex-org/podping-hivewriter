from plexo.codec.capnpy_codec import CapnpyCodec

from podping_schemas.org.podcastindex.podping.hivewriter.podping_hive_transaction import (
    PodpingHiveTransaction,
)
from podping_schemas.org.podcastindex.podping.podping_write import (
    PodpingWrite,
)
from podping_schemas.org.podcastindex.podping.podping_write_error import (
    PodpingWriteError,
)

podping_hive_transaction_codec = CapnpyCodec(PodpingHiveTransaction)
podping_write_codec = CapnpyCodec(PodpingWrite)
podping_write_error_codec = CapnpyCodec(PodpingWriteError)

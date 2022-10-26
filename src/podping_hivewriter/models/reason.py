import capnpy
from podping_schemas.org.podcastindex.podping.hivewriter import podping_reason
from podping_schemas.org.podcastindex.podping.hivewriter.podping_reason import (
    PodpingReason as Reason,
)

reasons = frozenset(Reason.__members__)

# capnpy has a different "constructor" for pyx vs pure python
get_reason_by_num = Reason._new_hack if hasattr(Reason, "_new_hack") else Reason._new

str_reason_map = {
    enumerant.name.decode("UTF-8"): get_reason_by_num(enumerant.codeOrder)
    for enumerant in capnpy.get_reflection_data(podping_reason)
    .get_node(Reason)
    .get_enum_enumerants()
}

from typing import FrozenSet

import capnpy
from podping_schemas.org.podcastindex.podping import podping_reason
from podping_schemas.org.podcastindex.podping.podping_reason import (
    PodpingReason,
)

# capnpy has a different "constructor" for pyx vs pure python
get_reason_by_num = (
    PodpingReason._new_hack
    if hasattr(PodpingReason, "_new_hack")
    else PodpingReason._new
)

str_reason_map = {
    enumerant.name.decode("UTF-8"): get_reason_by_num(enumerant.codeOrder)
    for enumerant in capnpy.get_reflection_data(podping_reason)
    .get_node(PodpingReason)
    .get_enum_enumerants()
}

reason_strings: FrozenSet[str] = frozenset(PodpingReason.__members__)
reasons: FrozenSet[PodpingReason] = frozenset(
    {str_reason_map[reason] for reason in reason_strings}
)

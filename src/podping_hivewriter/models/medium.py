from typing import FrozenSet

import capnpy
from podping_schemas.org.podcastindex.podping import podping_medium
from podping_schemas.org.podcastindex.podping.podping_medium import (
    PodpingMedium,
)

# capnpy has a different "constructor" for pyx vs pure python
get_medium_by_num = (
    PodpingMedium._new_hack
    if hasattr(PodpingMedium, "_new_hack")
    else PodpingMedium._new
)

str_medium_map = {
    enumerant.name.decode("UTF-8"): get_medium_by_num(enumerant.codeOrder)
    for enumerant in capnpy.get_reflection_data(podping_medium)
    .get_node(PodpingMedium)
    .get_enum_enumerants()
}

medium_strings: FrozenSet[str] = frozenset(PodpingMedium.__members__)
mediums: FrozenSet[PodpingMedium] = frozenset(
    {str_medium_map[medium] for medium in medium_strings}
)

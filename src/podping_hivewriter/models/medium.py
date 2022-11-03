import capnpy
from podping_schemas.org.podcastindex.podping.hivewriter import podping_medium
from podping_schemas.org.podcastindex.podping.hivewriter.podping_medium import (
    PodpingMedium as Medium,
)

mediums = frozenset(Medium.__members__)

# capnpy has a different "constructor" for pyx vs pure python
get_medium_by_num = Medium._new_hack if hasattr(Medium, "_new_hack") else Medium._new

str_medium_map = {
    enumerant.name.decode("UTF-8"): get_medium_by_num(enumerant.codeOrder)
    for enumerant in capnpy.get_reflection_data(podping_medium)
    .get_node(Medium)
    .get_enum_enumerants()
}

import capnpy
from capnpy.annotate import Options

medium_module = capnpy.load_schema(
    "podping_hivewriter.schema.medium",
    # Make sure properties are imported as specified (camelCase)
    options=Options(convert_case=False, include_reflection_data=True),
)

Medium = medium_module.Medium

mediums = frozenset(Medium.__members__)

# capnpy has a different "constructor" for pyx vs pure python
get_medium_by_num = Medium._new_hack if hasattr(Medium, "_new_hack") else Medium._new

str_medium_map = {
    enumerant.name.decode("UTF-8"): get_medium_by_num(enumerant.codeOrder)
    for enumerant in capnpy.get_reflection_data(medium_module)
    .get_node(Medium)
    .get_enum_enumerants()
}

import capnpy
from capnpy.annotate import Options

medium_module = capnpy.load_schema(
    "podping_hivewriter.schema.medium",
    # Make sure properties are imported as specified (camelCase)
    options=Options(convert_case=False),
)

Medium = medium_module.Medium

mediums = frozenset(Medium.__members__)

str_medium_map = {
    enumerant.name.decode("UTF-8"): Medium._new_hack(enumerant.codeOrder)
    for enumerant in capnpy.get_reflection_data(medium_module)
    .get_node(Medium)
    .get_enum_enumerants()
}

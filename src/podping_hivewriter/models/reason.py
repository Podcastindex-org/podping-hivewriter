import capnpy
from capnpy.annotate import Options

reason_module = capnpy.load_schema(
    "podping_hivewriter.schema.reason",
    # Make sure properties are imported as specified (camelCase)
    options=Options(convert_case=False),
)

Reason = reason_module.Reason

reasons = frozenset(Reason.__members__)

str_reason_map = {
    enumerant.name.decode("UTF-8"): Reason._new_hack(enumerant.codeOrder)
    for enumerant in capnpy.get_reflection_data(reason_module)
    .get_node(Reason)
    .get_enum_enumerants()
}

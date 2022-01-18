import capnpy
from capnpy.annotate import Options

reason_module = capnpy.load_schema(
    "podping_hivewriter.schema.reason",
    # Make sure properties are imported as specified (camelCase)
    options=Options(convert_case=False, include_reflection_data=True),
)

Reason = reason_module.Reason

reasons = frozenset(Reason.__members__)

# capnpy has a different "constructor" for pyx vs pure python
get_reason_by_num = Reason._new_hack if hasattr(Reason, "_new_hack") else Reason._new

str_reason_map = {
    enumerant.name.decode("UTF-8"): get_reason_by_num(enumerant.codeOrder)
    for enumerant in capnpy.get_reflection_data(reason_module)
    .get_node(Reason)
    .get_enum_enumerants()
}

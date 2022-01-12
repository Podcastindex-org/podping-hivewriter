import capnpy
from capnpy.annotate import Options

Reason = capnpy.load_schema(
    "podping_hivewriter.schema.reason",
    # Make sure properties are imported as specified (camelCase)
    options=Options(convert_case=False),
).Reason

reasons = frozenset(Reason.__members__)

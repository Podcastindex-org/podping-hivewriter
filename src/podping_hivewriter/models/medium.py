import capnpy
from capnpy.annotate import Options

Medium = capnpy.load_schema(
    "podping_hivewriter.schema.medium",
    # Make sure properties are imported as specified (camelCase)
    options=Options(convert_case=False),
).Medium

mediums = frozenset(Medium.__members__)

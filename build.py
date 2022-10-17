from capnpy.compiler.distutils import capnpy_schemas


class SetupKwargsProxy:
    def __init__(self, d):
        self._d = d

    @property
    def capnpy_options(self):
        return {
            # do NOT convert camelCase to camel_case
            "convert_case": False,
            # prevents us from having to call .decode("UTF-8") on strings
            # https://capnpy.readthedocs.io/en/latest/usage.html#text
            "text_type": "unicode",
        }

    @property
    def ext_modules(self):
        try:
            return self._d["ext_modules"]
        except KeyError:
            return None

    @ext_modules.setter
    def ext_modules(self, v):
        self._d["ext_modules"] = v


schema_files = [
    "src/podping_hivewriter/schema/podping_hive_transaction.capnp",
    "src/podping_hivewriter/schema/podping_medium.capnp",
    "src/podping_hivewriter/schema/podping_reason.capnp",
    "src/podping_hivewriter/schema/podping_write.capnp",
    "src/podping_hivewriter/schema/podping_write_error.capnp",
]


def build(setup_kwargs):
    capnpy_schemas(SetupKwargsProxy(setup_kwargs), "capnpy_schemas", schema_files)

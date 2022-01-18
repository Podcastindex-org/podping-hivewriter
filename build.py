from capnpy.compiler.distutils import capnpy_schemas


class SetupKwargsProxy:
    def __init__(self, d):
        self._d = d

    @property
    def capnpy_options(self):
        return {
            "convert_case": False,  # do NOT convert camelCase to camel_case
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
    "src/podping_hivewriter/schema/medium.capnp",
    "src/podping_hivewriter/schema/reason.capnp",
]


def build(setup_kwargs):
    capnpy_schemas(SetupKwargsProxy(setup_kwargs), "capnpy_schemas", schema_files)

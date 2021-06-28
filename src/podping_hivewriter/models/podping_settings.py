from typing import Tuple

from pydantic import BaseModel, validator


class PodpingSettings(BaseModel):
    """Dataclass for settings we will fetch from Hive"""

    hive_operation_period: int = 3
    max_url_list_bytes: int = 7500
    diagnostic_report_period: int = 60
    control_account: str = "podping"
    control_account_check_period: int = 60
    test_nodes: Tuple[str, ...] = ("https://testnet.openhive.network",)
    main_nodes: Tuple[str, ...] = (
        "https://api.deathwing.me",
        "https://api.pharesim.me",
        "https://hived.emre.sh",
        "https://hive.roelandp.nl",
        "https://rpc.ausbit.dev",
        "https://hived.privex.io",
        "https://hive-api.arcange.eu",
        "https://rpc.ecency.com",
        "https://api.hive.blog",
        "https://api.openhive.network",
        "https://api.ha.deathwing.me",
        "https://anyx.io",
    )

    @validator("hive_operation_period")
    def hive_op_period_must_be_int_above_one(cls, v):
        """If anyone ever tries to set op period < 1 this will catch
        it. Other float values coerced into int seconds"""
        if v < 1:
            v = 1
        return v

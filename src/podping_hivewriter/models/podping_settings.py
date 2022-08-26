from typing import Tuple

from pydantic import BaseModel, validator


class PodpingSettings(BaseModel):
    """Dataclass for settings we will fetch from Hive"""

    hive_operation_period: int = 3
    max_url_list_bytes: int = 8000
    diagnostic_report_period: int = 180
    control_account: str = "podping"
    control_account_check_period: int = 180
    test_nodes: Tuple[str, ...] = ("https://testnet.openhive.network",)

    @validator("hive_operation_period")
    def hive_op_period_must_be_int_above_one(cls, v):
        """If anyone ever tries to set op period < 1 this will catch
        it. Other float values coerced into int seconds"""
        if v < 1:
            v = 1
        return v

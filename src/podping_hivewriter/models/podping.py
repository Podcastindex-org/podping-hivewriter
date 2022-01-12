from typing import List, Literal

from pydantic import BaseModel, validator

from podping_hivewriter.models.medium import mediums
from podping_hivewriter.models.reason import reasons


class Podping(BaseModel):
    """Dataclass for on-chain podping schema"""

    version: Literal["1.0"] = "1.0"
    medium: str
    reason: str
    iris: List[str]

    @validator("medium")
    def medium_exists(cls, v):
        """Make sure the given medium matches what's available"""
        if v not in mediums:
            raise ValueError(f"medium must be one of {str(', '.join(mediums))}")
        return v

    @validator("reason")
    def reason_exists(cls, v):
        """Make sure the given reason matches what's available"""
        if v not in reasons:
            raise ValueError(f"reason must be one of {str(', '.join(reasons))}")
        return v

    @validator("iris")
    def iris_at_least_one_element(cls, v):
        """Make sure the list contains at least one element"""
        if len(v) == 0:
            raise ValueError("iris must contain at least one element")

        return v

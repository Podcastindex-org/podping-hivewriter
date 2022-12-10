from typing import List, Literal

from pydantic import BaseModel, validator

from podping_hivewriter.models.medium import medium_strings
from podping_hivewriter.models.reason import reason_strings


CURRENT_PODPING_VERSION = "1.1"


class InternalPodping(BaseModel):
    """Dataclass for on-chain podping schema"""

    version: Literal[CURRENT_PODPING_VERSION] = CURRENT_PODPING_VERSION
    medium: str
    reason: str
    iris: List[str]
    timestampNs: int
    sessionId: int

    @validator("medium")
    def medium_exists(cls, v):
        """Make sure the given medium matches what's available"""
        if v not in medium_strings:
            raise ValueError(f"medium must be one of {str(', '.join(medium_strings))}")
        return v

    @validator("reason")
    def reason_exists(cls, v):
        """Make sure the given reason matches what's available"""
        if v not in reason_strings:
            raise ValueError(f"reason must be one of {str(', '.join(reason_strings))}")
        return v

    @validator("iris")
    def iris_at_least_one_element(cls, v):
        """Make sure the list contains at least one element"""
        if len(v) == 0:
            raise ValueError("iris must contain at least one element")

        return v

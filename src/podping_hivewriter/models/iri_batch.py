import uuid
from typing import Set

from podping_schemas.org.podcastindex.podping.hivewriter.podping_medium import (
    PodpingMedium,
)
from podping_schemas.org.podcastindex.podping.hivewriter.podping_reason import (
    PodpingReason,
)
from pydantic import BaseModel, validator


class IRIBatch(BaseModel):
    batch_id: uuid.UUID
    medium: PodpingMedium
    reason: PodpingReason
    iri_set: Set[str]
    priority: int
    timestampNs: int

    @validator("batch_id", pre=True, always=True)
    def default_batch_id(cls, v: uuid.UUID) -> uuid.UUID:
        return v or uuid.uuid4()

    def __lt__(self, other):
        return self.priority <= other.priority

import uuid
from typing import Set

from podping_schemas.org.podcastindex.podping.podping_medium import (
    PodpingMedium,
)
from podping_schemas.org.podcastindex.podping.podping_reason import (
    PodpingReason,
)
from pydantic import BaseModel, validator


class IRIBatch(BaseModel):
    medium: PodpingMedium
    reason: PodpingReason
    iri_set: Set[str]
    priority: int
    timestampNs: int

    def __lt__(self, other):
        return self.priority <= other.priority

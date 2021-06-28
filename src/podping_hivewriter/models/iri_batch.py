import uuid
from typing import Set

from pydantic import BaseModel, validator


class IRIBatch(BaseModel):
    batch_id: uuid.UUID
    iri_set: Set[str]

    @validator("batch_id", pre=True, always=True)
    def default_batch_id(cls, v: uuid.UUID) -> uuid.UUID:
        return v or uuid.uuid4()

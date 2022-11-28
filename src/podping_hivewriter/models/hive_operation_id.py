from podping_schemas.org.podcastindex.podping.podping_medium import (
    PodpingMedium,
)
from podping_schemas.org.podcastindex.podping.podping_reason import (
    PodpingReason,
)


class HiveOperationId:
    def __init__(
        self,
        podping: str,
        medium: PodpingMedium = PodpingMedium.podcast,
        reason: PodpingReason = PodpingReason.update,
    ):
        self.podping: str = podping
        self.medium: PodpingMedium = medium
        self.reason: PodpingReason = reason

    def __eq__(self, other):
        return str(self) == str(other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(str(self))

    def __str__(self):
        return f"{self.podping}_{self.medium}_{str(self.reason).replace('_', '-')}"

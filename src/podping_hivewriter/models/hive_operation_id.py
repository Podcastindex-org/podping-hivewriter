from podping_hivewriter.models.medium import Medium
from podping_hivewriter.models.reason import Reason


class HiveOperationId:
    def __init__(
        self,
        podping: str,
        medium: Medium = Medium.podcast,
        reason: Reason = Reason.update,
    ):
        self.podping: str = podping
        self.medium: Medium = medium
        self.reason: Reason = reason

    def __eq__(self, other):
        return str(self) == str(other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(str(self))

    def __str__(self):
        return f"{self.podping}_{self.medium}_{str(self.reason).replace('_', '-')}"

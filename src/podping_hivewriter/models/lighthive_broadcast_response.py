from operator import itemgetter


class LighthiveBroadcastResponse:
    def __init__(
        self,
        response_dict: dict,
    ):
        self.hive_tx_id: str
        self.hive_block_num: int
        self.hive_tx_num: int
        self.expired: bool
        (
            self.hive_tx_id,
            self.hive_block_num,
            self.hive_tx_num,
            self.expired,
        ) = itemgetter("id", "block_num", "trx_num", "expired")(response_dict)

    def __eq__(self, other):
        return str(self) == str(other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(str(self))

    def __str__(self):
        return self.hive_tx_id

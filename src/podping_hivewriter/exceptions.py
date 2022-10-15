class PodpingCustomJsonPayloadExceeded(RuntimeError):
    """Raise when the size of a json string exceeds the custom_json payload limit"""


class TooManyCustomJsonsPerBlock(RuntimeError):
    """Raise when trying to write more than 5 custom_jsons in a single block"""


class NotEnoughResourceCredits(RuntimeError):
    """Raise when we run out of Resource Credits"""

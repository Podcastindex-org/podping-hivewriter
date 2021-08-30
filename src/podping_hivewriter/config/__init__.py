from enum import Enum


class NotificationReasons(Enum):
    FEED_UPDATED = (1,)
    NEW_FEED = (2,)
    HOST_CHANGE = (3,)
    GOING_LIVE = 4

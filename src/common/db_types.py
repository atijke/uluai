from enum import Enum


class RelatedEnum(str, Enum):
    label: str

    def __new__(cls, value: str, label: str):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.label = label

        return obj


class AccountStatuses(RelatedEnum):
    NEW = 'new', 'New'
    ACTIVE = 'active', 'Active'
    PAUSED = 'paused', 'Paused'
    KICKED = 'kicked', 'Kicked'
    FULL_BAN = 'full_ban', 'Full ban'


class EventPoolStatuses(RelatedEnum):
    NEW = 'new', 'New'
    SKIP = 'skip', 'Skip'
    SUCCESS = 'success', 'Success'
    ERROR = 'error', 'Error'

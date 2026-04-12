"""Early enums used by the scaffold and extended in later phases."""

from enum import StrEnum


class UsageIndicator(StrEnum):
    TEST = "T"
    PRODUCTION = "P"


class AcknowledgmentRequested(StrEnum):
    NO = "0"
    YES = "1"

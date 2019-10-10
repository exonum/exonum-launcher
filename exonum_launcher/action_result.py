"""Module containing ActionResult enum"""
from enum import Enum, auto as enum_auto


class ActionResult(Enum):
    """Denotes if action was successfull or not."""

    Success = enum_auto()
    Fail = enum_auto()

    def __bool__(self) -> bool:
        return self == ActionResult.Success

    def __str__(self) -> str:
        return "success" if bool(self) else "fail"

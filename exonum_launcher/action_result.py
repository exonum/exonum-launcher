"""Module containing ActionResult enum"""
from enum import auto as enum_auto, Enum


class ActionResult(Enum):
    """Denotes if the action was successful or not."""

    Success = enum_auto()
    Fail = enum_auto()
    Unknown = enum_auto()

    def __bool__(self) -> bool:
        return self == ActionResult.Success

    def __str__(self) -> str:
        return "success" if bool(self) else "failed"

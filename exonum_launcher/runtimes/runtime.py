"""Module with RuntimeSpecLoader class"""
import abc
from typing import Dict, Any


class RuntimeSpecLoader(metaclass=abc.ABCMeta):
    """Interface for classes loading artifact spec"""

    @abc.abstractmethod
    def encode_spec(self, data: Dict[str, Any]) -> bytes:
        """Encodes provided runtime-specific artifact spec into bytes."""

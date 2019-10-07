"""Artifact spec encoder for Rust runtime"""

from typing import Dict, Any

from .runtime import RuntimeSpecLoader


class RustSpecLoader(RuntimeSpecLoader):
    """Artifact spec encoder for Rust runtime"""

    def encode_spec(self, data: Dict[str, Any]) -> bytes:
        # Rust artifacts do not have spec
        return b""

"""Artifact spec encoder for Python runtime.

To get it working, you should first compile `.proto` files:

```sh
cd exonum_launcher/runtimes/proto
protoc --proto_path=. --python_out=. python.proto
```
"""

from typing import Dict, Any

from .runtime import RuntimeSpecLoader

try:
    from .proto import python_pb2
except (ModuleNotFoundError, ImportError):
    raise RuntimeError("You should compile .proto files before usage")


class PythonSpecLoader(RuntimeSpecLoader):
    """Artifact spec encoder for Python runtime"""

    def encode_spec(self, data: Dict[str, Any]) -> bytes:
        # Rust artifacts do not have spec
        spec = python_pb2.PythonArtifactSpec()

        spec.source_wheel_name = data["source_wheel_name"]
        spec.service_library_name = data["service_library_name"]
        spec.service_class_name = data["service_class_name"]
        spec.hash = bytes.fromhex(data["hash"])

        return spec.SerializeToString()

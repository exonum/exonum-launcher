# pylint: disable=missing-docstring, protected-access
import unittest
from typing import Any, Dict

from exonum_client.protobuf_loader import ProtobufLoader
from exonum_launcher.configuration import Instance
from exonum_launcher.runtimes.runtime import RuntimeSpecLoader
from exonum_launcher.instances.instance_spec_loader import InstanceSpecLoader


class TestRuntimeSpecLoader(RuntimeSpecLoader, unittest.TestCase):
    """Artifact spec encoder for Rust runtime"""

    def encode_spec(self, data: Dict[str, Any]) -> bytes:
        self.assertTrue("parameter" in data)
        self.assertEqual(data["parameter"], "value")
        return b"runtime_result"


class TestInstanceSpecLoader(InstanceSpecLoader, unittest.TestCase):
    def load_spec(self, loader: ProtobufLoader, instance: Instance) -> bytes:
        self.assertEqual(instance.artifact.runtime, "sample")
        self.assertEqual(instance.artifact.name, "cryptocurrency")

        return b"instance_result"

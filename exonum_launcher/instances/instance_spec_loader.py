"""Module with base class for Instance spec loader plugins."""

import abc

from exonum_client.protobuf_loader import ProtobufLoader

from exonum_launcher.configuration import Instance


class InstanceSpecLoadError(Exception):
    """Exception that should be raised if config load failed."""


class InstanceSpecLoader(metaclass=abc.ABCMeta):
    """Base class for custom instance spec loaders."""

    @abc.abstractmethod
    def load_spec(self, loader: ProtobufLoader, instance: Instance) -> bytes:
        """This method gets an instance spec and Protobuf Loader object and
        must provide instance spec serialized to bytes."""

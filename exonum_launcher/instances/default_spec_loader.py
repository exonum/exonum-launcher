"""Default spec loader which will be attempted to be used in case
if concrete loader was not provided for artifact."""

from exonum_client.protobuf_loader import ProtobufLoader
from exonum_client.module_manager import ModuleManager
from exonum_client.proofs.encoder import build_encoder_function

from exonum_launcher.configuration import Instance

from .instance_spec_loader import InstanceSpecLoader, InstanceSpecLoadError


class DefaultInstanceSpecLoader(InstanceSpecLoader):
    """Default spec loader.
    It attempts to load artifact proto files and recursively merge
    Config message from provided instance config dict."""

    def load_spec(self, loader: ProtobufLoader, instance: Instance) -> bytes:
        try:
            try:
                # Try to load module (if it's already compiled) first.
                service_module = ModuleManager.import_service_module(instance.artifact.name, "service")
            except (ModuleNotFoundError, ImportError):
                # If it's not compiled, load & compile protobuf.
                loader.load_service_proto_files(instance.artifact.runtime_id, instance.artifact.name)
                service_module = ModuleManager.import_service_module(instance.artifact.name, "service")

            config_class = service_module.Config

            # `build_encoder_function` will create a recursive binary serializer for the
            # provided message type. In our case we want to serialize `Config`.
            config_encoder = build_encoder_function(config_class)
            result = config_encoder(instance.config)

        # We're catching all the exceptions to shutdown gracefully (on the caller side) just in case.
        # pylint: disable=broad-except
        except Exception as error:
            artifact_name = instance.artifact.name
            raise InstanceSpecLoadError(
                f"Couldn't get a proto description for artifact: {artifact_name}, error: {error}"
            )

        return result

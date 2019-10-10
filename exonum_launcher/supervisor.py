"""Module encapsulating the interaction with the supervisor."""
from typing import List, Optional, Any
import json

from exonum_client import ExonumClient
from exonum_client.module_manager import ModuleManager

from .configuration import Artifact, Instance
from .instances import InstanceSpecLoader
from .runtimes import RuntimeSpecLoader


class Supervisor:
    """Interface to interact with the Supervisor service."""

    def __init__(self, clients: List[ExonumClient]) -> None:
        self._clients = clients
        self._main_client = clients[0]
        self._loader = self._main_client.protobuf_loader()
        self._supervisor_runtime_id: Optional[int] = None
        self._supervisor_artifact_name: Optional[str] = None
        self._service_module: Optional[Any] = None

    def __enter__(self) -> "Supervisor":
        self.initialize()

        return self

    def __exit__(self, exc_type: Optional[type], exc_value: Optional[Any], exc_traceback: Optional[object]) -> None:
        self.deinitialize()

    def initialize(self) -> None:
        """Initializes the Supervisor interface, doing the following:

        - Initializes protobuf loader;
        - Finds the ID and the name of the exonum supervisor service instance;
        - Loading the supervisor proto files;
        - Importing the supervisor's `service` proto module.
        """
        self._loader.initialize()

        self._loader.load_main_proto_files()

        services = self._main_client.available_services().json()

        for artifact in services["artifacts"]:
            if artifact["name"].startswith("exonum-supervisor"):
                self._supervisor_runtime_id = artifact["runtime_id"]
                self._supervisor_artifact_name = artifact["name"]
                break

        if self._supervisor_artifact_name == "":
            raise RuntimeError(
                "Could not find exonum-supervisor in available artifacts."
                "Please check that exonum node configuration is correct"
            )

        self._loader.load_service_proto_files(self._supervisor_runtime_id, self._supervisor_artifact_name)
        self._service_module = ModuleManager.import_service_module(self._supervisor_artifact_name, "service")

    def deinitialize(self) -> None:
        """Deinitializes the Supervisor by deinitializing the Protobuf Loader."""
        self._loader.deinitialize()

    def _post_to_supervisor(self, endpoint: str, message: bytes, private: bool = True) -> List[str]:
        message_data = message.hex()
        data = json.dumps(message_data)

        responses = []
        for client in self._clients:
            response = client.post_service("supervisor", endpoint, data, private)
            responses.append(response.json())

        return responses

    def create_deploy_request(self, artifact: Artifact, spec_loader: RuntimeSpecLoader) -> bytes:
        """Creates a deploy request for given artifact."""
        assert self._service_module is not None
        deploy_request = self._service_module.DeployRequest()

        deploy_request.artifact.runtime_id = artifact.runtime_id
        deploy_request.artifact.name = artifact.name
        deploy_request.deadline_height = artifact.deadline_height
        deploy_request.spec = spec_loader.encode_spec(artifact.spec)

        return deploy_request.SerializeToString()

    def create_start_instance_request(self, instance: Instance, config_loader: InstanceSpecLoader) -> bytes:
        """Creates a start instance request for given instance."""
        assert self._service_module is not None
        start_request = self._service_module.StartService()

        start_request.artifact.runtime_id = instance.artifact.runtime_id
        start_request.artifact.name = instance.artifact.name
        start_request.name = instance.name
        start_request.deadline_height = instance.deadline_height
        if instance.config:
            start_request.config = config_loader.load_spec(self._loader, instance)

        return start_request.SerializeToString()

    def send_deploy_request(self, deploy_request: bytes) -> List[str]:
        """Sends deploy request to the Supervisor."""
        return self._post_to_supervisor("deploy-artifact", deploy_request)

    def send_start_instance_request(self, start_request: bytes) -> List[str]:
        """Sends start instance request to the Supervisor."""
        return self._post_to_supervisor("start-service", start_request)

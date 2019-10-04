"""Main module of the Exonum Launcher."""
import time
import json
import sys
from typing import Any, List, Dict, Optional, Tuple

import requests
from requests.exceptions import ConnectionError as RequestsConnectionError
from google.protobuf.message import Message as ProtobufMessage

from exonum_client import ExonumClient, ModuleManager
from exonum_client.protobuf_loader import ProtobufLoader

# from .client import SupervisorClient
from .configuration import Artifact, Configuration, Instance


def _msg_to_hex(msg: ProtobufMessage) -> str:
    return msg.SerializeToString().hex()


# TODO proper error handling
def _post_json(url: str, data: Any) -> Any:
    data = json.dumps(data)
    response = requests.post(url, data=data, headers={"content-type": "application/json"})
    return response


class NotCommittedError(Exception):
    """Error raised when sent transaction was not committed."""


class Launcher:
    """Launcher class provides an interface to deploy and initialize
    services in Exonum blockchain."""

    # TODO should it be configurable?

    # Amount of retries to connect to the exonum client.
    RECONNECT_RETRIES = 10
    # Wait interval between connection attempts in seconds.
    RECONNECT_INTERVAL = 0.2

    def __init__(self, config: Configuration) -> None:
        self.config = config

        # TODO check the validity of the networks
        # TODO think of the correctness of the clients management

        self.clients: List[ExonumClient] = []

        for network in self.config.networks:
            client = ExonumClient(
                network["host"], network["public-api-port"], network["private-api-port"], network["ssl"]
            )
            self.clients.append(client)

        self.loader = self.clients[0].protobuf_loader()

        self._pending_deployments: Dict[Artifact, List[str]] = {}
        self._pending_initializations: Dict[Instance, List[str]] = {}
        self._completed_deployments: List[Artifact] = []
        self._completed_initializations: List[Instance] = []

        self._supervisor_runtime_id = 0
        self._supervisor_artifact_name = ""
        self.service_module: Optional[Any] = None

    def __enter__(self) -> "Launcher":
        self.initialize()

        return self

    def __exit__(self, exc_type: Optional[type], exc_value: Optional[Any], exc_traceback: Optional[object]) -> None:
        self.deinitialize()

    def initialize(self) -> None:
        """Initializes the launcher, doing the following:

        - Initializes protobuf loader;
        - Finds the ID and the name of the exonum supervisor service instance;
        - Loading the supervisor proto files;
        - Importing the supervisor's `service` proto module.
        """
        self.loader.initialize()

        self.loader.load_main_proto_files()

        services = self.clients[0].available_services().json()

        for artifact in services["artifacts"]:
            if artifact["name"].startswith("exonum-supervisor"):
                self._supervisor_runtime_id = artifact["runtime_id"]
                self._supervisor_artifact_name = artifact["name"]
                break

        if self._supervisor_artifact_name != "":
            raise RuntimeError(
                "Could not find exonum-supervisor in available artifacts."
                "Please check that exonum node configuration is correct"
            )

        self.loader.load_service_proto_files(self._supervisor_runtime_id, self._supervisor_artifact_name)
        self.service_module = ModuleManager.import_service_module(self._supervisor_artifact_name, "service")

    def deinitialize(self) -> None:
        """Deinitializes the Launcher by deinitializing the Protobuf Loader."""
        self.loader.deinitialize()

    def supervisor_data(self) -> Tuple[int, str]:
        """Returns a tuple of supervisor instance ID and name."""
        return self._supervisor_runtime_id, self._supervisor_artifact_name

    def protobuf_loader(self) -> ProtobufLoader:
        """Returns the ProtobufLoader that is being used by Launcher."""
        return self.loader

    def exonum_clients(self) -> List[ExonumClient]:
        """Returns the list of Exonum clients that are being used by Launcher."""
        return self.clients

    def pending_deployments(self) -> Dict[Artifact, List[str]]:
        """Returns a mapping `Artifact` => `list of deploy transactions hashes`
        for ongoing deployments."""
        return self._pending_deployments

    def pending_initializations(self) -> Dict[Instance, List[str]]:
        """Returns a mapping `Instance` => `list of init transactions hashes
        for ongoing initializations."""
        return self._pending_initializations

    def completed_deployments(self) -> List[Artifact]:
        """Returns a list of artifacts for which deployment is completed."""
        return self._completed_deployments

    def completed_initializations(self) -> List[Instance]:
        """Returns a list of instances for which initialization is completed."""
        return self._completed_initializations

    def _post_to_supervisor(self, endpoint: str, message: ProtobufMessage, private: bool = True) -> List[str]:
        responses = []
        for client in self.clients:
            supervisor_uri = client.service_endpoint("supervisor", endpoint, private)
            response = _post_json(supervisor_uri, _msg_to_hex(message))
            responses.append(response.json())

        return responses

    def _wait_until_txs_are_committed(self, tx_hashes: List[str]) -> None:
        client = self.clients[0]
        for idx, tx_hash in enumerate(tx_hashes):
            success = False
            for _ in range(self.RECONNECT_RETRIES):
                try:
                    info = client.get_tx_info(tx_hash).json()
                    status = info["type"]

                    if status != "committed":
                        with client.create_subscriber() as subscriber:
                            subscriber.wait_for_new_block()
                    else:
                        success = True
                        break
                except RequestsConnectionError:
                    # Exonum API server may be rebooting. Wait for it.
                    time.sleep(self.RECONNECT_INTERVAL)
                    continue

            if not success:
                raise NotCommittedError("Tx [{}] was not committed.".format(tx_hash))

    def deploy_all(self) -> None:
        """Deploys all the services from the provided config."""
        if self.service_module is None:
            raise RuntimeError("Launcher is not initialized")

        for _, artifact in self.config.artifacts.items():
            deploy_request = self.service_module.DeployRequest()

            # TODO add spec to the request.
            deploy_request.artifact.runtime_id = artifact.runtime_id
            deploy_request.artifact.name = artifact.name
            deploy_request.deadline_height = artifact.deadline_height
            # deploy_request.spec = ???

            self._pending_deployments[artifact] = self._post_to_supervisor("deploy-artifact", deploy_request)

    def wait_for_deploy(self) -> None:
        """Waits for all the deployments to be completed."""
        for tx_hashes in self._pending_deployments.values():
            self._wait_until_txs_are_committed(tx_hashes)

        for artifact in self._pending_deployments:
            for _ in range(self.RECONNECT_RETRIES):
                if self.check_deployed(artifact):
                    break

                with self.clients[0].create_subscriber() as subscriber:
                    subscriber.wait_for_new_block()

        self._completed_deployments = list(self._pending_deployments.keys())
        self._pending_deployments = {}

    def start_all(self) -> None:
        """Starts all the service instances from the provided config."""

        if self.service_module is None:
            raise RuntimeError("Launcher is not initialized")

        for instance in self.config.instances:
            start_request = self.service_module.StartService()

            # TODO add config to the request.
            start_request.artifact.runtime_id = instance.artifact.runtime_id
            start_request.artifact.name = instance.artifact.name
            start_request.name = instance.name
            start_request.deadline_height = instance.deadline_height

            if instance.config:
                config = self.get_service_config(instance)
                start_request.config.Pack(config)

            self._pending_initializations[instance] = self._post_to_supervisor("start-service", start_request)

    def wait_for_start(self) -> None:
        """Waits for all the initializations to be completed."""

        for tx_hashes in self._pending_initializations.values():
            self._wait_until_txs_are_committed(tx_hashes)

        for instance in self._pending_initializations:
            for _ in range(self.RECONNECT_RETRIES):
                if self.get_instance_id(instance):
                    break
                else:
                    with self.clients[0].create_subscriber() as subscriber:
                        subscriber.wait_for_new_block()

        self._completed_initializations = list(self._pending_initializations.keys())
        self._pending_initializations = {}

    def check_deployed(self, artifact: Artifact, network_id: int = 0) -> bool:
        """Returns True if artifact is deployed. Otherwise returns False."""
        dispatcher_info = self.clients[network_id].available_services().json()

        for value in dispatcher_info["artifacts"]:
            if value["runtime_id"] == artifact.runtime_id and value["name"] == artifact.name:
                return True

        return False

    def get_instance_id(self, instance: Instance, network_id: int = 0) -> Optional[str]:
        """Returns ID if running instance. Is service instance was not found,
        None is returned."""
        dispatcher_info = self.clients[network_id].available_services().json()

        for value in dispatcher_info["services"]:
            if value["name"] == instance.name:
                return value["id"]

        return None

    def get_service_config(self, instance: Instance) -> ProtobufMessage:
        """Loads the artifact proto files for provided instance,
        gets Config message and fills it.
        Returns a filled Protobuf Message object."""

        try:
            self.loader.load_service_proto_files(instance.artifact.runtime_id, instance.artifact.name)
            service_module = ModuleManager.import_service_module(instance.artifact.name, "service")

        # We're catchin all the exceptions to shutdown gracefully just in case.
        # pylint: disable=broad-except
        except Exception as error:
            print("Couldn't get a proto description for artifact: {}, error: {}".format(instance.artifact.name, error))
            sys.exit(1)

        config = service_module.Config()

        for key, value in instance.config.items():
            assert key in config.DESCRIPTOR.fields_by_name.keys()
            setattr(config, key, value)

        return config


def main(args: Any) -> None:
    """Runs the launcher to deploy and init all the instances from the config."""
    config = Configuration.from_yaml(args.input)

    with Launcher(config) as launcher:
        launcher.deploy_all()
        launcher.wait_for_deploy()
        time.sleep(10)  # TODO Temporary workaround. Waiting for proto description being available.

        for artifact in launcher.completed_deployments():
            deployed = launcher.check_deployed(artifact)
            deployed_str = "succeed" if deployed else "failed"
            print("Artifact {} -> deploy status: {}".format(artifact.name, deployed_str))

        launcher.start_all()
        launcher.wait_for_start()

        for instance in launcher.completed_initializations():
            instance_id = launcher.get_instance_id(instance)
            id_str = "started with ID {}".format(instance_id) if instance_id else "start failed"
            print("Instance {} -> start status: {}".format(instance.name, id_str))


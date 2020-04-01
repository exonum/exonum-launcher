"""Module encapsulating the interaction with the supervisor."""
import random
from typing import Any, List, Optional, Tuple
from google.protobuf.message import Message

from exonum_client import ExonumClient
from exonum_client.module_manager import ModuleManager

from .configuration import Artifact, Instance
from .explorer import Explorer
from .instances import InstanceSpecLoader
from .runtimes import RuntimeSpecLoader


# pylint: disable=too-many-instance-attributes
class Supervisor:
    """Interface to interact with the Supervisor service."""

    def __init__(self, mode: str, clients: List[ExonumClient]) -> None:
        self._mode = mode
        self._clients = clients
        self._main_client = clients[0]
        self._loader = self._main_client.protobuf_loader()
        self._supervisor_runtime_id: Optional[int] = None
        self._supervisor_artifact_name: Optional[str] = None
        self._supervisor_artifact_version: Optional[str] = None
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

        services = self._main_client.public_api.available_services().json()

        for artifact in services["artifacts"]:
            if artifact["name"].startswith("exonum-supervisor"):
                self._supervisor_runtime_id = artifact["runtime_id"]
                self._supervisor_artifact_name = artifact["name"]
                self._supervisor_artifact_version = artifact["version"]
                break

        if not self._supervisor_artifact_name:
            raise RuntimeError(
                "Could not find exonum-supervisor in available artifacts."
                "Please check that exonum node configuration is correct"
            )

        self._loader.load_service_proto_files(
            self._supervisor_runtime_id, self._supervisor_artifact_name, self._supervisor_artifact_version
        )
        self._service_module = ModuleManager.import_service_module(
            self._supervisor_artifact_name, self._supervisor_artifact_version, "service"
        )

    def deinitialize(self) -> None:
        """Deinitializes the Supervisor by deinitializing the Protobuf Loader."""
        self._loader.deinitialize()

    def _post_to_supervisor(self, endpoint: str, message: Message, private: bool = True) -> List[str]:
        responses: List[str] = list()

        data = message.SerializeToString()

        for client in self._clients:
            supervisor_api = (
                client.service_private_api("supervisor") if private else client.service_public_api("supervisor")
            )
            response = supervisor_api.post_service(endpoint, data, data_format="binary")
            responses.append(response.json())

        return responses

    def _get_configuration_number(self) -> int:
        supervisor_private_api = self._main_client.service_private_api("supervisor")
        response = supervisor_private_api.get_service("configuration-number")

        return int(response.json())

    def get_migration_state(self, service: str, artifact: Artifact, seed: int) -> Any:
        """Retrieves a state of the migration for the service."""
        height = artifact.deadline_height
        supervisor_private_api = self._main_client.service_private_api("supervisor")
        response = supervisor_private_api.get_service(
            f"migration-status?service={service}&new_artifact={artifact}&deadline_height={height}&seed={seed}"
        )
        return response.json()

    def create_deploy_request(self, artifact: Artifact, spec_loader: RuntimeSpecLoader) -> Message:
        """Creates a deploy request for given artifact."""
        assert self._service_module is not None
        deploy_request = self._service_module.DeployRequest()

        deploy_request.artifact.runtime_id = artifact.runtime_id
        deploy_request.artifact.name = artifact.name
        deploy_request.artifact.version = artifact.version
        deploy_request.deadline_height = artifact.deadline_height
        deploy_request.spec = spec_loader.encode_spec(artifact.spec)
        deploy_request.seed = _get_seed()

        return deploy_request

    def create_migration_request(self, service_name: str, artifact: Artifact) -> Tuple[Message, int]:
        """Creates a migration request for given service."""
        assert self._service_module is not None
        migration_request = self._service_module.MigrationRequest()
        seed = _get_seed()

        migration_request.service = service_name
        migration_request.new_artifact.runtime_id = artifact.runtime_id
        migration_request.new_artifact.version = artifact.version
        migration_request.new_artifact.name = artifact.name
        migration_request.deadline_height = artifact.deadline_height
        migration_request.seed = seed

        return migration_request, seed

    def create_unload_request(self, artifacts: List[Artifact], actual_from: int) -> Optional[Message]:
        """Creates unload request for the given artifact."""
        assert self._service_module is not None

        artifacts_to_unload = list(filter(lambda a: a.action == "unload", artifacts))

        if not artifacts_to_unload:
            return None

        unload_artifact_request = self._service_module.ConfigPropose()
        unload_artifact_request.configuration_number = self._get_configuration_number()
        unload_artifact_request.actual_from = actual_from

        for artifact in artifacts_to_unload:
            unload_artifact = self._service_module.UnloadArtifact()
            unload_artifact.artifact_id.runtime_id = artifact.runtime_id
            unload_artifact.artifact_id.name = artifact.name
            unload_artifact.artifact_id.version = artifact.version

            config_change = self._service_module.ConfigChange()
            config_change.unload_artifact.CopyFrom(unload_artifact)

            unload_artifact_request.changes.append(config_change)

        return unload_artifact_request

    def create_start_instances_request(
        self, instances: List[Instance], config_loaders: List[InstanceSpecLoader], actual_from: int
    ) -> Optional[Message]:
        """Creates a start instance request for given list of instances."""
        assert self._service_module is not None
        configuration_number = self._get_configuration_number()

        start_request = self._service_module.ConfigPropose()
        start_request.actual_from = actual_from
        start_request.configuration_number = configuration_number
        for instance, config_loader in zip(instances, config_loaders):
            config_change = self._service_module.ConfigChange()
            start_service = self._service_module.StartService()

            start_service.artifact.runtime_id = instance.artifact.runtime_id
            start_service.artifact.name = instance.artifact.name
            start_service.artifact.version = instance.artifact.version
            start_service.name = instance.name
            if instance.config:
                start_service.config = config_loader.load_spec(self._loader, instance)

            config_change.start_service.CopyFrom(start_service)
            start_request.changes.append(config_change)
        return start_request

    def create_config_change_request(
        self,
        consensus: Optional[Any],
        instances: List[Instance],
        config_loaders: List[InstanceSpecLoader],
        actual_from: int,
    ) -> Message:
        """Creates a configuration change request."""

        if self._mode != "simple":
            raise RuntimeError("Changing configuration for decentralized supervisor is not yet supported")

        assert self._service_module is not None

        config_change_request = self._service_module.ConfigPropose()
        config_change_request.configuration_number = self._get_configuration_number()
        config_change_request.actual_from = actual_from

        if consensus is not None:
            config_change = self._service_module.ConfigChange()
            self._build_consensus_change(consensus, config_change)
            config_change_request.changes.append(config_change)

        for instance, config_loader in zip(instances, config_loaders):
            config_change = self._service_module.ConfigChange()

            if instance.action == "start":
                self._build_start_service_change(instance, config_loader, config_change)
            elif instance.action == "config":
                self._build_service_config_change(instance, config_loader, config_change)
            elif instance.action == "stop":
                self._build_stop_service_change(instance, config_change)
            elif instance.action == "resume":
                self._build_resume_service_change(instance, config_loader, config_change)
            elif instance.action == "freeze":
                self._build_freeze_service_change(instance, config_change)
            else:
                raise RuntimeError(f"Unknown action type '{instance.action}' for instance '{instance}'")

            config_change_request.changes.append(config_change)

        return config_change_request

    def _build_consensus_change(self, consensus: Any, change: Any) -> None:
        """Creates a ConfigChange for consensus config."""

        assert self._service_module is not None

        blockchain_module = ModuleManager.import_service_module(
            self._supervisor_artifact_name, self._supervisor_artifact_version, "exonum.blockchain"
        )

        types_module = ModuleManager.import_service_module(
            self._supervisor_artifact_name, self._supervisor_artifact_version, "exonum.crypto.types"
        )

        new_consensus_config = blockchain_module.Config()
        for consensus_key, service_key in consensus["validator_keys"]:
            consensus_key = types_module.PublicKey(data=bytes.fromhex(consensus_key))
            service_key = types_module.PublicKey(data=bytes.fromhex(service_key))

            validator_keys = blockchain_module.ValidatorKeys()
            validator_keys.consensus_key.CopyFrom(consensus_key)
            validator_keys.service_key.CopyFrom(service_key)

            new_consensus_config.validator_keys.append(validator_keys)

        new_consensus_config.first_round_timeout = consensus["first_round_timeout"]
        new_consensus_config.status_timeout = consensus["status_timeout"]
        new_consensus_config.peers_timeout = consensus["peers_timeout"]
        new_consensus_config.txs_block_limit = consensus["txs_block_limit"]
        new_consensus_config.max_message_len = consensus["max_message_len"]
        new_consensus_config.min_propose_timeout = consensus["min_propose_timeout"]
        new_consensus_config.max_propose_timeout = consensus["max_propose_timeout"]
        new_consensus_config.propose_timeout_threshold = consensus["propose_timeout_threshold"]

        change.consensus.CopyFrom(new_consensus_config)

    def _build_service_config_change(self, instance: Instance, config_loader: InstanceSpecLoader, change: Any) -> None:
        """Creates a ConfigChange for service config change."""

        assert self._service_module is not None
        service_config = self._service_module.ServiceConfig()

        if instance.instance_id is None:
            # Instance ID is currently unknown, retrieve it.
            explorer = Explorer(self._main_client)
            instance_id = explorer.get_instance_id(instance)

            if instance_id is None:
                raise RuntimeError(f"Instance {instance} doesn't seem to be deployed, can't change configuration")

            instance.instance_id = instance_id

        service_config.instance_id = instance.instance_id
        service_config.params = config_loader.serialize_config(self._loader, instance, instance.config)

        change.service.CopyFrom(service_config)

    def _build_start_service_change(self, instance: Instance, config_loader: InstanceSpecLoader, change: Any) -> None:
        """Creates a ConfigChange for starting a service."""

        assert self._service_module is not None
        start_service = self._service_module.StartService()

        start_service.artifact.runtime_id = instance.artifact.runtime_id
        start_service.artifact.name = instance.artifact.name
        start_service.artifact.version = instance.artifact.version
        start_service.name = instance.name
        if instance.config:
            start_service.config = config_loader.load_spec(self._loader, instance)

        change.start_service.CopyFrom(start_service)

    def _build_stop_service_change(self, instance: Instance, change: Any) -> None:
        """Creates a ConfigChange for stopping a service."""

        assert self._service_module is not None
        stop_service = self._service_module.StopService()

        if instance.instance_id is None:
            # Instance ID is currently unknown, retrieve it.
            explorer = Explorer(self._main_client)
            instance_id = explorer.get_instance_id(instance)

            if instance_id is None:
                raise RuntimeError(f"Instance {instance} does not seem to be deployed, it can't be stopped")

            instance.instance_id = instance_id

        stop_service.instance_id = instance.instance_id

        change.stop_service.CopyFrom(stop_service)

    def _build_resume_service_change(self, instance: Instance, config_loader: InstanceSpecLoader, change: Any) -> None:
        """Creates a ConfigChange for resuming a service."""

        assert self._service_module is not None
        resume_service = self._service_module.ResumeService()

        if instance.instance_id is None:
            # Instance ID is currently unknown, retrieve it.
            explorer = Explorer(self._main_client)
            instance_id = explorer.get_instance_id(instance)

            if instance_id is None:
                raise RuntimeError(f"Instance {instance} does not seem to be deployed, it can't be resumed")

            instance.instance_id = instance_id

        resume_service.instance_id = instance.instance_id

        if instance.config:
            resume_service.params = config_loader.serialize_config(self._loader, instance, instance.config)

        change.resume_service.CopyFrom(resume_service)

    def _build_freeze_service_change(self, instance: Instance, change: Any) -> None:
        """Creates a ConfigChange for freezing a service."""

        assert self._service_module is not None
        freeze_service = self._service_module.FreezeService()

        if instance.instance_id is None:
            # Instance ID is currently unknown, retrieve it.
            explorer = Explorer(self._main_client)
            instance_id = explorer.get_instance_id(instance)

            if instance_id is None:
                raise RuntimeError(f"Instance {instance} does not seem to be deployed, it can't be frozen")

            instance.instance_id = instance_id

        freeze_service.instance_id = instance.instance_id
        change.freeze_service.CopyFrom(freeze_service)

    def send_deploy_request(self, deploy_request: Message) -> List[str]:
        """Sends deploy request to the Supervisor."""
        return self._post_to_supervisor("deploy-artifact", deploy_request)

    def send_propose_config_request(self, config_proposal: Message) -> List[str]:
        """Sends propose config request to the Supervisor."""
        return self._post_to_supervisor("propose-config", config_proposal)

    def send_migration_request(self, migration_request: Message) -> List[str]:
        """Sends migration request to the Supervisor"""
        return self._post_to_supervisor("migrate", migration_request)


def _get_seed() -> int:
    return random.getrandbits(64)

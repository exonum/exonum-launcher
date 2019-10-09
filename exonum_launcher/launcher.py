"""Main module of the Exonum Launcher."""
import time
import importlib
from typing import Any, List, Dict, Optional

from exonum_client import ExonumClient

from .configuration import Artifact, Configuration, Instance
from .runtimes import RuntimeSpecLoader, RustSpecLoader
from .instances import DefaultInstanceSpecLoader, InstanceSpecLoader
from .supervisor import Supervisor
from .explorer import Explorer


# TODO resolve it.
# pylint: disable=too-many-instance-attributes
class Launcher:
    """Launcher class provides an interface to deploy and initialize
    services in Exonum blockchain."""

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

        self.pending_deployments: Dict[Artifact, List[str]] = {}
        self.pending_initializations: Dict[Instance, List[str]] = {}
        self.failed_deployments: List[Artifact] = []
        self.failed_initializations: List[Instance] = []
        self.completed_deployments: List[Artifact] = []
        self.completed_initializations: List[Instance] = []

        # Load runtime plugins and add rust (as default).
        self._runtime_spec_loaders: Dict[str, RuntimeSpecLoader] = self._load_runtime_plugins()
        self._runtime_spec_loaders["rust"] = RustSpecLoader()

        # Load artifact plugins.
        self._instance_spec_loaders: Dict[Artifact, InstanceSpecLoader] = self._load_artifact_plugins()

        # Create supervsior and explorer.
        self._supervisor = Supervisor(self.clients)
        self._explorer = Explorer(self.clients[0])

    def _load_runtime_plugins(self) -> Dict[str, RuntimeSpecLoader]:
        runtime_loaders: Dict[str, RuntimeSpecLoader] = dict()
        for runtime_name, class_path in self.config.plugins["runtime"].items():
            try:
                runtime_loaders[runtime_name] = _import_class(class_path, RuntimeSpecLoader)
            except (ValueError, ImportError, ModuleNotFoundError, AttributeError) as error:
                raise RuntimeError(f"Could not load runtime parser {class_path}: {error}")

        return runtime_loaders

    def _load_artifact_plugins(self) -> Dict[Artifact, InstanceSpecLoader]:
        instance_loaders: Dict[Artifact, InstanceSpecLoader] = dict()
        for artifact_name, class_path in self.config.plugins["artifact"].items():
            try:
                artifact = self.config.artifacts[artifact_name]
                instance_loaders[artifact] = _import_class(class_path, InstanceSpecLoader)
            except (ValueError, KeyError, ImportError, ModuleNotFoundError, AttributeError) as error:
                raise RuntimeError(f"Could not load runtime parser {class_path}: {error}")

        return instance_loaders

    def __enter__(self) -> "Launcher":
        self.initialize()

        return self

    def __exit__(self, exc_type: Optional[type], exc_value: Optional[Any], exc_traceback: Optional[object]) -> None:
        self.deinitialize()

    def initialize(self) -> None:
        """Initializes the Launcher by initializing the Supervisor."""
        self._supervisor.initialize()

    def deinitialize(self) -> None:
        """Deinitializes the Launcher by deinitializing the Supervisor."""
        self._supervisor.deinitialize()

    def add_runtime_spec_loader(self, runtime: str, spec_loader: RuntimeSpecLoader) -> None:
        """Adds a runtime-specific spec loader to encode runtime artifact spec into bytes."""
        if runtime in self._runtime_spec_loaders:
            raise ValueError(f"Spec loader for runtime '{runtime}' is already added")

        self._runtime_spec_loaders[runtime] = spec_loader

    def add_instance_spec_loader(self, artifact: Artifact, spec_loader: InstanceSpecLoader) -> None:
        """Adds an artifact-specific config spec loader to encode instance configs into bytes."""
        if artifact in self._instance_spec_loaders:
            raise ValueError(f"Instance spec loader for artifact '{artifact.name}' is already added")

        self._instance_spec_loaders[artifact] = spec_loader

    def deploy_all(self) -> None:
        """Deploys all the services from the provided config."""
        for artifact in self.config.artifacts.values():
            spec_loader = self._runtime_spec_loaders[artifact.runtime]
            deploy_request = self._supervisor.create_deploy_request(artifact, spec_loader)

            self.pending_deployments[artifact] = self._supervisor.send_deploy_request(deploy_request)

    def wait_for_deploy(self) -> None:
        """Waits for all the deployments to be completed."""
        for tx_hashes in self.pending_deployments.values():
            self._explorer.wait_for_txs(tx_hashes)

        for artifact in self.pending_deployments:
            # TODO handle return value
            self._explorer.wait_for_deploy(artifact)

        self.completed_deployments = list(self.pending_deployments.keys())
        self.pending_deployments = {}

    def start_all(self) -> None:
        """Starts all the service instances from the provided config."""

        for instance in self.config.instances:
            config_loader = self._instance_spec_loaders.get(instance.artifact, DefaultInstanceSpecLoader())
            start_request = self._supervisor.create_start_instance_request(instance, config_loader)

            self.pending_initializations[instance] = self._supervisor.send_start_instance_request(start_request)

    def wait_for_start(self) -> None:
        """Waits for all the initializations to be completed."""

        for tx_hashes in self.pending_deployments.values():
            self._explorer.wait_for_txs(tx_hashes)

        for instance in self.pending_initializations:
            # TODO handle return value
            self._explorer.wait_for_start(instance)

        self.completed_initializations = list(self.pending_initializations.keys())
        self.pending_initializations = {}

    def explorer(self) -> Explorer:
        """Returns used explorer"""
        return self._explorer


def _import_class(class_path: str, res_type: Any) -> Any:
    module_name, class_name = class_path.rsplit(".", 1)
    module = importlib.import_module(module_name)
    spec_loader = getattr(module, class_name)

    if not issubclass(spec_loader, res_type):
        raise ValueError(f"Class {spec_loader} is not a subclass of {res_type}")

    return spec_loader()

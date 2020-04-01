"""Main module of the Exonum Launcher."""
import importlib
import time
from typing import Any, Dict, List, Optional
from requests.exceptions import ConnectionError as RequestsConnectionError, HTTPError

from exonum_client import ExonumClient

from .action_result import ActionResult
from .configuration import Artifact, Configuration
from .explorer import Explorer, NotCommittedError
from .instances import DefaultInstanceSpecLoader, InstanceSpecLoader
from .launch_state import LaunchState
from .runtimes import RuntimeSpecLoader, RustSpecLoader
from .supervisor import Supervisor


class Launcher:
    """Launcher class provides an interface to deploy and initialize
    services in Exonum blockchain."""

    def __init__(self, config: Configuration) -> None:
        self.config = config

        self.clients = self._load_clients()

        self.launch_state = LaunchState()

        # Load runtime plugins and add rust (as default).
        self._runtime_plugins: Dict[str, RuntimeSpecLoader] = self._load_runtime_plugins()
        self._runtime_plugins["rust"] = RustSpecLoader()

        # Load artifact plugins.
        self._artifact_plugins: Dict[Artifact, InstanceSpecLoader] = self._load_artifact_plugins()

        # Create supervisor and explorer.
        self._supervisor = Supervisor(self.config.supervisor_mode, self.clients)
        self._explorer = Explorer(self.clients[0])

    def _load_clients(self) -> List[ExonumClient]:
        clients: List[ExonumClient] = []

        for network in self.config.networks:
            client = ExonumClient(
                network["host"], network["public-api-port"], network["private-api-port"], network["ssl"]
            )
            clients.append(client)

            # Do not need more than one node in a 'Simple' mode
            if self.config.is_simple():
                break

        return clients

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
        """Initializes the Launcher by initializing the Supervisor and checking that clients are valid."""
        for client in self.clients:
            if client.private_api.get_stats().status_code != 200:
                network = (
                    f"{client.schema}://{client.hostname}; ports: {client.public_api_port} / {client.private_api_port}"
                )
                raise RuntimeError(f"Client from network {network} doesn't respond to API requests")

        self._supervisor.initialize()

    def deinitialize(self) -> None:
        """De-initializes the Launcher by de-initializing the Supervisor."""
        self._supervisor.deinitialize()

    def add_runtime_spec_loader(self, runtime: str, spec_loader: RuntimeSpecLoader) -> None:
        """Adds a runtime-specific spec loader to encode runtime artifact spec into bytes."""
        if runtime in self._runtime_plugins:
            raise ValueError(f"Spec loader for runtime '{runtime}' is already added")

        self._runtime_plugins[runtime] = spec_loader

    def add_instance_spec_loader(self, artifact: Artifact, spec_loader: InstanceSpecLoader) -> None:
        """Adds an artifact-specific config spec loader to encode instance configs into bytes."""
        if artifact in self._artifact_plugins:
            raise ValueError(f"Instance spec loader for artifact '{artifact.name}' is already added")

        self._artifact_plugins[artifact] = spec_loader

    def deploy_all(self) -> None:
        """Deploys all the services from the provided config."""
        for artifact in self.config.artifacts.values():
            if artifact.action != "deploy":
                continue

            spec_loader = self._runtime_plugins[artifact.runtime]
            deploy_request = self._supervisor.create_deploy_request(artifact, spec_loader)
            txs = self._supervisor.send_deploy_request(deploy_request)
            self.launch_state.add_pending_deploy(artifact, txs)

    def wait_for_deploy(self) -> None:
        """Waits for all the deployments to be completed."""
        pending_deployments = self.launch_state.pending_deployments()
        for tx_hashes in pending_deployments.values():
            self._explorer.wait_for_txs(tx_hashes)

        for artifact in pending_deployments:
            result = self._explorer.wait_for_deploy(artifact)
            self.launch_state.complete_deploy(artifact, result)

    def start_all(self) -> None:
        """Starts all the service instances from the provided config."""
        config_loaders = [
            self._artifact_plugins.get(instance.artifact, DefaultInstanceSpecLoader())
            for instance in self.config.instances
        ]

        if not config_loaders:
            return

        config_proposal = self._supervisor.create_config_change_request(
            self.config.consensus, self.config.instances, config_loaders, self.config.actual_from
        )

        txs = self._supervisor.send_propose_config_request(config_proposal)
        self.launch_state.add_pending_config(self.config, txs)

    def wait_for_start(self) -> None:
        """Waits for all the initializations to be completed."""

        if not self.launch_state.pending_configs():
            return

        tx_hashes = self.launch_state.pending_configs()[self.config]

        self._explorer.wait_for_txs(tx_hashes)

        result = ActionResult.Success
        for instance in self.config.instances:
            if instance.action != "start":
                continue

            result = self._explorer.wait_for_start(instance)
            if result == ActionResult.Fail:
                # Since we're sending only one transaction, one fail means fail for everything
                break

        self.launch_state.complete_config(self.config, result)

    def unload_all(self) -> None:
        """Unload all artifacts marked as unloaded."""
        unload_request = self._supervisor.create_unload_request(
            list(self.config.artifacts.values()), self.config.actual_from
        )

        if unload_request:
            txs = self._supervisor.send_propose_config_request(unload_request)
            self.launch_state.add_pending_unload(txs)

    def wait_for_unload(self) -> None:
        """Wait for all unloads to be completed."""
        tx_hashes = self.launch_state.pending_unloads()

        if not tx_hashes:
            return

        try:
            self._explorer.wait_for_txs(tx_hashes)
            tx_status, description = self._explorer.get_tx_status(tx_hashes[0])
            if tx_status:
                self.launch_state.unload_status = ActionResult.Success, description
            else:
                self.launch_state.unload_status = ActionResult.Fail, description

        except NotCommittedError as error:
            self.launch_state.unload_status = ActionResult.Fail, str(error)

    def migrate_all(self) -> None:
        """Migrates all services from the provided config."""
        for service_name, artifact in self.config.migrations.items():
            migration_request, seed = self._supervisor.create_migration_request(service_name, artifact)
            txs = self._supervisor.send_migration_request(migration_request)
            self.launch_state.add_pending_migration((service_name, artifact, seed), txs)

    def wait_for_migration(self) -> None:
        """Waits for all migrations to be completed."""
        pending_migrations = self.launch_state.pending_migrations()
        for tx_hashes in pending_migrations.values():
            self._explorer.wait_for_txs(tx_hashes)

        for (service_name, artifact, seed), _ in pending_migrations.items():
            result = ActionResult.Fail
            description = ""
            for _ in range(0, self._explorer.RECONNECT_RETRIES):
                try:
                    state = self._supervisor.get_migration_state(service_name, artifact, seed)
                    if "state" in state:
                        if state["state"] == "succeed":
                            result = ActionResult.Success
                            description = "Success"
                            break
                        if "failed" in state["state"]:
                            description = state["state"]["failed"]["error"]["description"]
                    time.sleep(self._explorer.RECONNECT_INTERVAL)
                except (RequestsConnectionError, ConnectionRefusedError, HTTPError):
                    time.sleep(self._explorer.RECONNECT_INTERVAL)
            self.launch_state.complete_migration(service_name, (result, description))

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

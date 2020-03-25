"""Launch process state module"""
from typing import Dict, List, Tuple

from .action_result import ActionResult
from .configuration import Artifact, Configuration


class LaunchState:
    """State of the deploy&init process."""

    def __init__(self) -> None:
        self._pending_configs: Dict[Configuration, List[str]] = dict()
        self._pending_deployments: Dict[Artifact, List[str]] = dict()
        self._pending_migrations: Dict[Tuple[str, Artifact, int], List[str]] = dict()
        self._completed_configs: Dict[Configuration, ActionResult] = dict()
        self._completed_deployments: Dict[Artifact, ActionResult] = dict()
        self._complete_migrations: Dict[str, Tuple[ActionResult, str]] = dict()
        self._pending_unloads: List[str] = list()
        self.unload_status = ActionResult.Unknown, ""

    def add_pending_deploy(self, artifact: Artifact, txs: List[str]) -> None:
        """Adds a pending deploy to the state."""
        self._pending_deployments[artifact] = txs

    def add_pending_config(self, config: Configuration, txs: List[str]) -> None:
        """Adds a pending config to the state."""
        self._pending_configs[config] = txs

    def pending_deployments(self) -> Dict[Artifact, List[str]]:
        """Returns a copy of pending deployments dict."""
        return dict(self._pending_deployments)

    def pending_configs(self) -> Dict[Configuration, List[str]]:
        """Returns a copy of pending initializations dict."""
        return dict(self._pending_configs)

    def complete_deploy(self, artifact: Artifact, result: ActionResult) -> None:
        """Completes the deploy process."""
        self._completed_deployments[artifact] = result
        del self._pending_deployments[artifact]

    def complete_config(self, config: Configuration, result: ActionResult) -> None:
        """Adds a pending config to the state."""
        self._completed_configs[config] = result
        if config in self._pending_configs:
            del self._pending_configs[config]

    def completed_deployments(self) -> Dict[Artifact, ActionResult]:
        """Returns a copy of completed deployments dict."""
        return dict(self._completed_deployments)

    def completed_configs(self) -> Dict[Configuration, ActionResult]:
        """Returns a copy of completed configs dict."""
        return dict(self._completed_configs)

    def get_completed_config_state(self, config: Configuration) -> ActionResult:
        """Returns completed config state."""
        if config not in self._completed_configs:
            return ActionResult.Unknown

        return self._completed_configs[config]

    def add_pending_unload(self, txs: List[str]) -> None:
        """Adds status for unloaded artifact."""
        self._pending_unloads = txs

    def pending_unloads(self) -> List[str]:
        """Returns pending unload statuses."""
        return self._pending_unloads

    def add_pending_migration(self, service: Tuple[str, Artifact, int], txs: List[str]) -> None:
        """Adds a pending migration to the state"""
        self._pending_migrations[service] = txs

    def pending_migrations(self) -> Dict[Tuple[str, Artifact, int], List[str]]:
        """Returns pending migrations."""
        return self._pending_migrations

    def complete_migration(self, service_name: str, result: Tuple[ActionResult, str]) -> None:
        """Adds a status of the migration for the service."""
        self._complete_migrations[service_name] = result

    def completed_migrations(self) -> Dict[str, Tuple[ActionResult, str]]:
        """Returns completed migrations statuses."""
        return self._complete_migrations

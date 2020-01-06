"""Launch process state module"""
from typing import Dict, List

from .action_result import ActionResult
from .configuration import Artifact, Instance, Configuration


class LaunchState:
    """State of the deploy&init process."""

    def __init__(self) -> None:
        self._pending_deployments: Dict[Artifact, List[str]] = dict()
        self._pending_configs: Dict[Configuration, List[str]] = dict()
        self._completed_deployments: Dict[Artifact, ActionResult] = dict()
        self._completed_configs: Dict[Configuration, ActionResult] = dict()

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

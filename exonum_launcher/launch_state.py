"""Launch process state module"""
from typing import Dict, List

from .action_result import ActionResult
from .configuration import Artifact, Instance


class LaunchState:
    """State of the deploy&init process."""

    def __init__(self) -> None:
        self._pending_deployments: Dict[Artifact, List[str]] = dict()
        self._pending_initializations: Dict[Instance, List[str]] = dict()
        self._completed_deployments: Dict[Artifact, ActionResult] = dict()
        self._completed_initializations: Dict[Instance, ActionResult] = dict()

    def add_pending_deploy(self, artifact: Artifact, txs: List[str]) -> None:
        """Adds a pending deploy to the state."""
        self._pending_deployments[artifact] = txs

    def add_pending_initialization(self, instance: Instance, txs: List[str]) -> None:
        """Adds a pending initialization to the state."""
        self._pending_initializations[instance] = txs

    def pending_deployments(self) -> Dict[Artifact, List[str]]:
        """Returns a copy of pending deployments dict."""
        return dict(self._pending_deployments)

    def pending_initializations(self) -> Dict[Instance, List[str]]:
        """Returns a copy of pending initializations dict."""
        return dict(self._pending_initializations)

    def complete_deploy(self, artifact: Artifact, result: ActionResult) -> None:
        """Completes the deploy process."""
        self._completed_deployments[artifact] = result
        del self._pending_deployments[artifact]

    def complete_initialization(self, instance: Instance, result: ActionResult) -> None:
        """Completes the initialization process."""
        self._completed_initializations[instance] = result
        if instance in self._pending_initializations:
            del self._pending_initializations[instance]

    def completed_deployments(self) -> Dict[Artifact, ActionResult]:
        """Returns a copy of completed deployments dict."""
        return dict(self._completed_deployments)

    def completed_initializations(self) -> Dict[Instance, ActionResult]:
        """Returns a copy of completed initializations dict."""
        return dict(self._completed_initializations)

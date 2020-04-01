"""Module encapsulating the interaction with the Explorer."""

from typing import Optional, List, Tuple
import time

from requests.exceptions import ConnectionError as RequestsConnectionError, HTTPError
from exonum_client import ExonumClient

from .action_result import ActionResult
from .configuration import Artifact, Instance


class NotCommittedError(Exception):
    """Error raised when sent transaction was not committed."""


class ExecutionFailError(Exception):
    """Error raised when transaction execution fails."""


class Explorer:
    """Interface to interact with the Explorer service."""

    # Amount of retries to connect to the exonum client.
    RECONNECT_RETRIES = 10
    # Wait interval between connection attempts in seconds.
    RECONNECT_INTERVAL = 0.5

    def __init__(self, client: ExonumClient):
        self._client = client

    def is_deployed(self, artifact: Artifact) -> bool:
        """Returns True if artifact is deployed. Otherwise returns False."""
        dispatcher_info = self._client.public_api.available_services().json()

        for value in dispatcher_info["artifacts"]:
            if (
                value["runtime_id"] == artifact.runtime_id
                and value["name"] == artifact.name
                and value["version"] == artifact.version
            ):
                return True

        return False

    def get_instance_id(self, instance: Instance) -> Optional[int]:
        """Returns ID if running instance. Is service instance was not found,
        None is returned."""
        dispatcher_info = self._client.public_api.available_services().json()

        for status in dispatcher_info["services"]:
            spec = status["spec"]
            if spec["name"] == instance.name:
                return int(spec["id"])

        return None

    def get_tx_status(self, tx_hash: str) -> Tuple[bool, str]:
        """Returns status of the transaction by its hash."""
        response = self._client.public_api.get_tx_info(tx_hash)
        response.raise_for_status()
        info = response.json()
        tx_status_description = "OK"

        if info["type"] == "committed":
            status = info["status"]
            if status["type"] == "success":
                return True, tx_status_description

            tx_status_description = status["description"]

        return False, tx_status_description

    def wait_for_tx(self, tx_hash: str) -> None:
        """Waits until the tx is committed."""
        success = False
        description = "uncommitted"
        for _ in range(self.RECONNECT_RETRIES):
            try:
                success, description = self.get_tx_status(tx_hash)
                if success:
                    break

                with self._client.create_subscriber("blocks") as subscriber:
                    subscriber.wait_for_new_event()
            except (RequestsConnectionError, ConnectionRefusedError, HTTPError):
                # Exonum API server may be rebooting. Wait for it.
                time.sleep(self.RECONNECT_INTERVAL)
                continue

        if not success:
            raise NotCommittedError(f"Tx [{tx_hash}] was not committed or committed with error: {description}")

    def wait_for_txs(self, txs: List[str]) -> None:
        """Waits until every transaction from the list is committed."""
        for tx_hash in txs:
            self.wait_for_tx(tx_hash)

    def wait_for_deploy(self, artifact: Artifact) -> ActionResult:
        """Waits for all the deployment of artifact to be completed."""
        for _ in range(self.RECONNECT_RETRIES):
            if self.is_deployed(artifact):
                return ActionResult.Success

            with self._client.create_subscriber("blocks") as subscriber:
                # TODO Temporary solution because currently it takes up to 10 seconds to update dispatcher info.
                time.sleep(2)
                subscriber.wait_for_new_event()

        return ActionResult.Fail

    def wait_for_start(self, instance: Instance) -> ActionResult:
        """Waits for all the initializations to be completed."""
        for _ in range(self.RECONNECT_RETRIES):
            if self.get_instance_id(instance):
                return ActionResult.Success

            with self._client.create_subscriber("blocks") as subscriber:
                subscriber.wait_for_new_event()

        return ActionResult.Fail

"""Module encapsulating the interaction with the Explorer."""

from typing import Optional, List
import time

from requests.exceptions import ConnectionError as RequestsConnectionError
from exonum_client import ExonumClient

from .action_result import ActionResult
from .configuration import Artifact, Instance


class NotCommittedError(Exception):
    """Error raised when sent transaction was not committed."""


class Explorer:
    """Interface to interact with the Explorer service."""

    # Amount of retries to connect to the exonum client.
    RECONNECT_RETRIES = 10
    # Wait interval between connection attempts in seconds.
    RECONNECT_INTERVAL = 0.5

    def __init__(self, client: ExonumClient):
        self._client = client

    def check_deployed(self, artifact: Artifact) -> bool:
        """Returns True if artifact is deployed. Otherwise returns False."""
        dispatcher_info = self._client.available_services().json()

        for value in dispatcher_info["artifacts"]:
            if value["runtime_id"] == artifact.runtime_id and value["name"] == artifact.name:
                return True

        return False

    def get_instance_id(self, instance: Instance) -> Optional[int]:
        """Returns ID if running instance. Is service instance was not found,
        None is returned."""
        dispatcher_info = self._client.available_services().json()

        for status in dispatcher_info["services"]:
            spec = status["spec"]
            if spec["name"] == instance.name:
                return int(spec["id"])

        return None

    def wait_for_tx(self, tx_hash: str) -> None:
        """Waits until the tx is committed."""
        success = False
        for _ in range(self.RECONNECT_RETRIES):
            try:
                info = self._client.get_tx_info(tx_hash).json()
                status = info["type"]

                if status != "committed":
                    with self._client.create_subscriber() as subscriber:
                        subscriber.wait_for_new_block()
                else:
                    success = True
                    break
            except (RequestsConnectionError, ConnectionRefusedError):
                # Exonum API server may be rebooting. Wait for it.
                time.sleep(self.RECONNECT_INTERVAL)
                continue

        if not success:
            raise NotCommittedError("Tx [{}] was not committed.".format(tx_hash))

    def wait_for_txs(self, txs: List[str]) -> None:
        """Waits until every transaction from the list is committed."""
        for tx_hash in txs:
            self.wait_for_tx(tx_hash)

    def wait_for_deploy(self, artifact: Artifact) -> ActionResult:
        """Waits for all the deployment of artifact to be completed."""
        for _ in range(self.RECONNECT_RETRIES):
            if self.check_deployed(artifact):
                return ActionResult.Success

            with self._client.create_subscriber() as subscriber:
                # TODO Temporary solution because it currently it takes up to 10 seconds to
                # update dispatcher info.
                time.sleep(2)
                subscriber.wait_for_new_block()

        return ActionResult.Fail

    def wait_for_start(self, instance: Instance) -> ActionResult:
        """Waits for all the initializations to be completed."""
        for _ in range(self.RECONNECT_RETRIES):
            if self.get_instance_id(instance):
                return ActionResult.Success

            with self._client.create_subscriber() as subscriber:
                subscriber.wait_for_new_block()

        return ActionResult.Fail

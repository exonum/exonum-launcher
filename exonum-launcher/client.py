from typing import Dict, Any

import requests
import json

from .utils import encode
from .configuration import Artifact, Instance


class ExonumClient(object):
    TX_URL = "{}://{}:{}/api/explorer/v1/transactions"

    def __init__(
        self, hostname: str, public_api_port: int = 80, ssl: bool = False
    ) -> None:
        self.schema = "https" if ssl else "http"
        self.hostname = hostname
        self.public_api_port = public_api_port
        self.tx_url = self.TX_URL.format(
            self.schema, hostname, public_api_port)

    def send_raw_tx(self, tx: bytes) -> Dict[str, str]:
        try:
            response = requests.post(
                self.tx_url,
                data=self._msg_to_json(tx),
                headers={"content-type": "application/json"},
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def _msg_to_json(self, tx) -> str:
        return json.dumps({"tx_body": encode(tx)}, indent=4)


class SupervisorClient(object):
    BASE_URL = "{}:{}/api/services/supervisor/{}"

    @staticmethod
    def from_dict(data: Dict[Any, Any]):
        return SupervisorClient(host=data["host"], public_api_port=data["public-api-port"],
                                private_api_port=data["private-api-port"])

    def __init__(
        self, host: str, public_api_port: int, private_api_port: int,
    ) -> None:
        self.host = host
        self.public_api_port = public_api_port
        self.private_api_port = private_api_port

    def deploy_artifact(self, artifact: Artifact, deadline_height: int) -> str:
        data = {
            "artifact": {
                "runtime_id": artifact.runtime_id,
                "name": artifact.name,
            },
            "deadline_height": deadline_height
        }
        return self._post_json(self.private_api_port, "deploy-artifact", data)

    def start_service(self, instance: Instance) -> str:
        data = {
            "artifact": {
                "runtime_id": instance.artifact.runtime_id,
                "name": instance.artifact.name,
            },
            "name": instance.name,
            "config": {
                "type_url": "string",
                "value": []
            }
        }
        return self._post_json(self.private_api_port, "start-service", data)        

    def _post_json(self, port: int, method: str, data: Any) -> str:
        url = self.BASE_URL.format(self.host, port, method)
        data = json.dumps(data)
        response = requests.post(url, data=data, headers={
                                 "content-type": "application/json"})
        return response.json()

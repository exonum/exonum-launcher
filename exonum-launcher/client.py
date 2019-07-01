from typing import Dict, Any

import requests
import json

from .utils import encode
from .configuration import Artifact, Instance
from .messages import Supervisor


def _msg_to_hex(msg) -> str:
    return encode(msg.SerializeToString(deterministic=True))


class SupervisorClient(object):
    BASE_URL = "{}:{}/api/services/supervisor/{}"

    @staticmethod
    def from_dict(data: Dict[Any, Any]):
        return SupervisorClient(host=data["host"],
                                public_api_port=data["public-api-port"],
                                private_api_port=data["private-api-port"])

    def __init__(
        self, host: str, public_api_port: int, private_api_port: int,
    ) -> None:
        self.host = host
        self.public_api_port = public_api_port
        self.private_api_port = private_api_port

    def deploy_artifact(self, artifact: Artifact) -> str:
        msg = Supervisor.deploy_artifact(artifact)
        return self._post_json(self.private_api_port,
                               "deploy-artifact",
                               _msg_to_hex(msg))

    def start_service(self, instance: Instance) -> str:
        msg = Supervisor.start_service(instance)
        return self._post_json(self.private_api_port,
                               "start-service",
                               _msg_to_hex(msg))

    def _post_json(self, port: int, method: str, data: Any) -> str:
        url = self.BASE_URL.format(self.host, port, method)
        data = json.dumps(data)
        response = requests.post(url, data=data, headers={
                                 "content-type": "application/json"})
        return response.json()

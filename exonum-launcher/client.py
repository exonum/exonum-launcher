from typing import Dict, Any

import requests
import json
import importlib

from .utils import encode
from .configuration import Artifact, Instance

def _msg_to_hex(msg) -> str:
    return encode(msg.SerializeToString())


def _post_json(url: str, data: Any) -> Any:
    data = json.dumps(data)
    response = requests.post(url, data=data, headers={
                             "content-type": "application/json"})
    return response.json()


def _get_json(url: str, params=None) -> Any:
    response = requests.get(url, params)
    return response.json()


class SupervisorClient(object):
    # host:port/handler/method
    BASE_URL = "{}:{}/{}/{}"

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

    def supervisor(self) -> Any:
        messages = importlib.import_module(".messages", "exonum-launcher")
        return messages.Supervisor()

    def deploy_artifact(self, artifact: Artifact) -> str:
        msg = self.supervisor().deploy_artifact(artifact)
        return _post_json(
            self._supervisor_endpoint(method="deploy-artifact", private=True),
            _msg_to_hex(msg)
        )

    def start_service(self, instance: Instance) -> str:
        msg = self.supervisor().start_service(instance)
        return _post_json(
            self._supervisor_endpoint(method="start-service", private=True),
            _msg_to_hex(msg)
        )

    def dispatcher_info(self) -> Any:
        return _get_json(self._system_endpoint(method="services"))

    def proto_sources(self, artifact: Artifact=None) -> str:
        params = None
        if artifact is not None:
            params = {'artifact': "{}:{}".format(artifact.runtime_id, artifact.name)}
        return _get_json(self._system_endpoint(method="proto-sources"), params=params)

    def _supervisor_endpoint(self, method: str, private=False) -> str:
        if private is False:
            port = self.public_api_port
        else:
            port = self.private_api_port
        return self.BASE_URL.format(self.host, port, "api/services/supervisor", method)

    def _system_endpoint(self, method: str, private=False) -> str:
        if private is False:
            port = self.public_api_port
        else:
            port = self.private_api_port
        return self.BASE_URL.format(self.host, port, "api/system/v1", method)

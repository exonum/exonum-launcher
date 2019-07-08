from typing import Dict, Any

import requests
import json

from .utils import encode
from .configuration import Artifact, Instance
from .messages import Supervisor


def _msg_to_hex(msg) -> str:
    return encode(msg.SerializeToString())


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

    def deploy_artifact(self, artifact: Artifact) -> str:
        msg = Supervisor.deploy_artifact(artifact)
        return self._post_json(
            self._supervisor_endpoint(method="deploy-artifact", private=True), 
            _msg_to_hex(msg)
        )

    def start_service(self, instance: Instance) -> str:
        msg = Supervisor.start_service(instance)
        return self._post_json(
            self._supervisor_endpoint(method="start-service", private=True), 
            _msg_to_hex(msg)
        )

    def dispatcher_info(self) -> Any:
        return self._get_json(self._system_endpoint(method="services"))

    def _supervisor_endpoint(self, method: str, private=False) -> str:
        port = None
        if private is False:
            port = self.public_api_port
        else:
            port = self.private_api_port
        return self.BASE_URL.format(self.host, port, "api/services/supervisor", method)

    def _system_endpoint(self, method: str, private=False) -> str:
        port = None
        if private is False:
            port = self.public_api_port
        else:
            port = self.private_api_port
        return self.BASE_URL.format(self.host, port, "api/system/v1", method)        

    def _post_json(self, url: str, data: Any) -> Any:
        data = json.dumps(data)
        response = requests.post(url, data=data, headers={
                                 "content-type": "application/json"})
        return response.json()

    def _get_json(self, url: str, query_str=None) -> Any:
        if query_str is not None:
            url = url + "?" + query_str
        response = requests.get(url)
        return response.json()

import yaml
import json

from typing import Dict, Any
from google.protobuf.message import Message
import google.protobuf.json_format as JsonFormat

from .messages import get_service_config_structure

RUNTIMES = {
    "rust": 0,
}


class Artifact(object):
    @staticmethod
    def from_dict(module: str, data: Dict[Any, Any]):
        return Artifact(data["name"], data["runtime"], module)

    def __init__(self, name: str, runtime: str, module: str) -> None:
        self.name = name
        self.runtime = runtime
        self.runtime_id = RUNTIMES[runtime]
        ConfigSpec = get_service_config_structure(module, module)
        self.config_spec = ConfigSpec()

    def serialize_config(self, data: Any) -> Message:
        json_data = json.dumps(data)
        JsonFormat.Parse(json_data, self.config_spec)

class Instance(object):
    def __init__(self, artifact: Artifact, name: str, config: Any) -> None:
        self.artifact = artifact
        self.name = name
        self.config = artifact.serialize_config(config)

class Configuration(object):
    @staticmethod
    def from_yaml(path: str):
        data = load_yaml(path)
        return Configuration(data)

    def __init__(self, data: Dict[Any, Any]) -> None:
        self.networks = data["networks"]
        self.artifacts = dict()
        self.instances = list()

        # Imports configuration parser for each artifact.
        for module, artifact in data["artifacts"].items():
            artifact = Artifact.from_dict(module, artifact)
            self.artifacts[str(module)] = artifact

        # Converts config for each instance into protobuf
        for (name, instance) in data["instances"].items():
            artifact = self.artifacts[instance["artifact"]]
            self.instances += [Instance(artifact, name, instance["config"])]

        return None


def load_yaml(path: str) -> Dict[Any, Any]:
    with open(path, 'r') as f:
        return yaml.safe_load(f)

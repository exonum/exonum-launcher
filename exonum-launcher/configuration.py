import yaml
import json

from typing import Dict, Any

RUNTIMES = {
    "rust": 0,
}


class Artifact(object):
    @staticmethod
    def from_dict(module: str, data: Dict[Any, Any]):
        return Artifact(
            name=data["name"],
            runtime=data["runtime"],
            module=module,
            deadline_height=data["deadline_height"]
        )

    def __init__(self, name: str, runtime: str, module: str, deadline_height: int) -> None:
        self.name = name
        self.module = module
        self.runtime = runtime
        self.runtime_id = RUNTIMES[runtime]
        self.deadline_height = deadline_height


class Instance(object):
    def __init__(self, artifact: Artifact, name: str, config: Any) -> None:
        self.artifact = artifact
        self.name = name
        self.config = config


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

from typing import Any, Dict, List
import yaml

RUNTIMES = {
    "rust": 0,
}


class Artifact(object):
    @staticmethod
    def from_dict(data: Dict[Any, Any]):
        return Artifact(
            name=data["name"],
            runtime=data["runtime"],
            spec=data.get("spec", None)
        )

    def __init__(self, name: str, runtime: str, spec: Any) -> None:
        self.name = name
        self.runtime = runtime
        self.runtime_id = RUNTIMES[runtime]
        self.spec = spec
        self.deadline_height = None


class Instance(object):
    def __init__(self, artifact: Artifact, name: str, config: Any) -> None:
        self.artifact = artifact
        self.name = name
        self.config = config
        self.deadline_height = None
        self.id = None


def _get_specific(name: Any, value: Dict[Any, Any], parent: Dict[Any, Any]) -> Any:
    return value.get(name, parent.get(name))


class Configuration:
    @staticmethod
    def from_yaml(path: str):
        data = load_yaml(path)
        return Configuration(data)

    def __init__(self, data: Dict[Any, Any]):
        self.networks = data["networks"]
        self.artifacts: Dict[str, Artifact] = dict()
        self.instances: List[Instance] = list()

        # Imports configuration parser for each artifact.
        for name, value in data["artifacts"].items():
            artifact = Artifact.from_dict(value)
            artifact.deadline_height = _get_specific("deadline_height", value, parent=data)
            self.artifacts[str(name)] = artifact

        # Converts config for each instance into protobuf
        for (name, value) in data["instances"].items():
            artifact = self.artifacts[value["artifact"]]
            instance = Instance(artifact, name, value.get("config", None))
            instance.deadline_height = _get_specific("deadline_height", value, parent=data)
            self.instances += [instance]


def load_yaml(path: str) -> Dict[Any, Any]:
    with open(path, 'r') as f:
        return yaml.safe_load(f)

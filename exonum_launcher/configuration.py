"""Module capable of parsing config file"""
from typing import Any, Dict, List
import yaml

RUNTIMES = {"rust": 0}


class Artifact:
    """Representation of parsed artifact description."""

    @staticmethod
    def from_dict(data: Dict[Any, Any]) -> "Artifact":
        """Parses an `Artifact` entity from provided dict."""
        return Artifact(name=data["name"], runtime=data["runtime"], spec=data.get("spec", None))

    def __init__(self, name: str, runtime: str, spec: Any) -> None:
        self.name = name
        self.runtime = runtime
        self.runtime_id = RUNTIMES[runtime]
        self.spec = spec
        self.deadline_height = None


class Instance:
    """Representation of parsed service instance description."""

    def __init__(self, artifact: Artifact, name: str, config: Any) -> None:
        self.artifact = artifact
        self.name = name
        self.config = config
        self.deadline_height = None
        self.instance_id = None


def _get_specific(name: Any, value: Dict[Any, Any], parent: Dict[Any, Any]) -> Any:
    """Attempts to find a key in value, and if there is no such key in it,
    attempts to find it in the parent element."""
    return value.get(name, parent.get(name))


class Configuration:
    """Parsed configuration of services to deploy&init."""

    @staticmethod
    def from_yaml(path: str) -> "Configuration":
        """Parses configuration from YAML file."""
        data = load_yaml(path)
        return Configuration(data)

    def __init__(self, data: Dict[Any, Any]) -> None:
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
    """Loads YAML from file."""
    with open(path, "r") as config_file:
        return yaml.safe_load(config_file)

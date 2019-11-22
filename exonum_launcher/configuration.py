"""Module capable of parsing config file"""
from typing import Any, Dict, List
import yaml

RUNTIMES = {"rust": 0}
SUPERVISOR_MODES = ["simple", "decentralized"]


class Artifact:
    """Representation of parsed artifact description."""

    @staticmethod
    def from_dict(data: Dict[Any, Any]) -> "Artifact":
        """Parses an `Artifact` entity from provided dict."""
        spec = data.get("spec", dict())
        # Check whether we need to deploy artifact or not
        deploy = data.get("deploy", True)
        return Artifact(name=data["name"], runtime=data["runtime"], spec=spec, deploy=deploy)

    def __init__(self, name: str, runtime: str, spec: Any, deploy: bool) -> None:
        self.name = name
        self.runtime = runtime
        self.runtime_id = RUNTIMES[runtime]
        self.spec = spec
        self.deadline_height = None
        self.deploy = deploy


class Instance:
    """Representation of parsed service instance description."""

    def __init__(self, artifact: Artifact, name: str, config: Any) -> None:
        self.artifact = artifact
        self.name = name
        self.config = config
        self.instance_id = None


def _get_specific(name: Any, value: Dict[Any, Any], parent: Dict[Any, Any]) -> Any:
    """Attempts to find a key in value, and if there is no such key in it,
    attempts to find it in the parent element."""
    return value.get(name, parent.get(name))


class Configuration:
    """Parsed configuration of services to deploy&init."""

    @staticmethod
    def declare_runtime(runtime: str, runtime_id: int) -> None:
        """With this method you can declare an additional runtime, for example:

        >>> Configuration.declare_runtime("java", 1)

        Please note that this method should be called before config parsing.
        """
        if runtime in RUNTIMES:
            raise ValueError(f"Runtime {runtime} is already declared (it has id {RUNTIMES[runtime]})")

        RUNTIMES[runtime] = runtime_id

    @staticmethod
    def runtimes() -> Dict[str, int]:
        """Returns a list of added runtimes."""
        return RUNTIMES

    @staticmethod
    def from_yaml(path: str) -> "Configuration":
        """Parses configuration from YAML file."""
        data = load_yaml(path)
        return Configuration(data)

    def __init__(self, data: Dict[Any, Any]) -> None:
        runtimes = data.get("runtimes")
        if runtimes is not None:
            for runtime in runtimes:
                self.declare_runtime(runtime, runtimes[runtime])

        self.networks = data["networks"]
        self.supervisor_mode = data.get("supervisor_mode", "simple")
        if not self.supervisor_mode in SUPERVISOR_MODES:
            raise ValueError(
                f"The supervisor mode must be one of these: {SUPERVISOR_MODES}, "
                f"but '{self.supervisor_mode}' was given."
            )
        self.actual_from = data.get("actual_from", 0)
        self.artifacts: Dict[str, Artifact] = dict()
        self.instances: List[Instance] = list()
        self.plugins: Dict[str, Dict[str, str]] = data.get("plugins", {"runtime": dict(), "artifact": dict()})

        # Imports configuration parser for each artifact.
        for name, value in data["artifacts"].items():
            artifact = Artifact.from_dict(value)
            artifact.deadline_height = _get_specific("deadline_height", value, parent=data)
            self.artifacts[str(name)] = artifact

        # Converts config for each instance into protobuf
        for (name, value) in data["instances"].items():
            artifact = self.artifacts[value["artifact"]]
            instance = Instance(artifact, name, value.get("config", None))
            self.instances += [instance]

    def is_simple(self) -> bool:
        """Returns true if in a 'Simple' mode."""
        return self.supervisor_mode == "simple"


def load_yaml(path: str) -> Dict[Any, Any]:
    """Loads YAML from file."""
    with open(path, "r") as config_file:
        return yaml.safe_load(config_file)

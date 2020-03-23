"""Module capable of parsing config file"""
from typing import Any, Dict, List, Optional

import yaml
from exonum_client.crypto import PublicKey

RUNTIMES = {"rust": 0}
SUPERVISOR_MODES = ["simple", "decentralized"]


class Artifact:
    """Representation of parsed artifact description."""

    @staticmethod
    def from_dict(data: Dict[Any, Any]) -> "Artifact":
        """Parses an `Artifact` entity from provided dict."""
        actions = ["none", "deploy", "unload"]
        spec = data.get("spec", dict())
        # Check whether we need to deploy the artifact or not
        action = data.get("action", "none")
        if action not in actions:
            raise RuntimeError(f"Incorrect action '{action}'. Available actions are: {actions}")
        return Artifact(name=data["name"], version=data["version"], runtime=data["runtime"], spec=spec, action=action)

    # pylint: disable=too-many-arguments
    def __init__(self, name: str, version: str, runtime: str, spec: Any, action: str) -> None:
        self.name = name
        self.version = version
        self.runtime = runtime
        self.runtime_id = RUNTIMES[runtime]
        self.spec = spec
        self.deadline_height = None
        self.action = action

    def __str__(self) -> str:
        return f"{self.runtime_id}:{self.name}:{self.version}"


class Instance:
    """Representation of parsed service instance description."""

    def __init__(self, artifact: Artifact, name: str, action: str, config: Any) -> None:
        actions = ["start", "stop", "config", "resume", "freeze"]
        if action not in actions:
            raise RuntimeError(f"Incorrect action '{action}', available actions are: {actions}")

        self.artifact = artifact
        self.name = name
        self.config = config
        self.instance_id: Optional[int] = None
        self.action = action


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
        self.migrations: Dict[str, Artifact] = dict()
        self.plugins: Dict[str, Dict[str, str]] = data.get("plugins", dict())
        self.consensus: Any = data.get("consensus", None)

        if self.consensus is not None:
            self._validate_consensus_config()

        # Init the plugins
        plugin_types: List[str] = ["runtime", "artifact"]
        # Add the plugin types
        for plugin_type in plugin_types:
            if plugin_type not in self.plugins.keys():
                self.plugins[plugin_type] = dict()

        # Imports configuration parser for each artifact.
        artifacts = data.get("artifacts", dict())
        for name, value in artifacts.items():
            artifact = Artifact.from_dict(value)
            artifact.deadline_height = _get_specific("deadline_height", value, parent=data)
            self.artifacts[str(name)] = artifact

        # Converts config for each instance into protobuf.
        instances = data.get("instances", dict())
        for (name, value) in instances.items():
            artifact = self.artifacts[value["artifact"]]
            instance = Instance(artifact, name, value.get("action", "start"), value.get("config", None))
            self.instances += [instance]

        # Import configuration parser for each migration.
        migrations = data.get("migrations", dict())
        for name, value in migrations.items():
            artifact = Artifact.from_dict(value)
            artifact.deadline_height = _get_specific("deadline_height", value, parent=data)
            self.migrations[str(name)] = artifact

    def _validate_consensus_config(self) -> None:
        assert self.consensus is not None
        expected_fields = [
            "validator_keys",
            "first_round_timeout",
            "status_timeout",
            "peers_timeout",
            "txs_block_limit",
            "max_message_len",
            "min_propose_timeout",
            "max_propose_timeout",
            "propose_timeout_threshold",
        ]

        for field in expected_fields:
            if field not in self.consensus:
                raise RuntimeError(
                    f"Invalid consensus config '{self.consensus}', at least the field '{field}' is missing."
                )

        for key_pair in self.consensus["validator_keys"]:
            if len(key_pair) != 2:
                raise RuntimeError(
                    "Validator keys should be a list of pairs (consensus_key, service_key) in hexadecimal form"
                )

            # Check that keys can be parsed correctly.
            _ = PublicKey(bytes.fromhex(key_pair[0]))
            _ = PublicKey(bytes.fromhex(key_pair[1]))

    def is_simple(self) -> bool:
        """Returns true if in a 'Simple' mode."""
        return self.supervisor_mode == "simple"


def load_yaml(path: str) -> Dict[Any, Any]:
    """Loads YAML from file."""
    with open(path, "r") as config_file:
        return yaml.safe_load(config_file)

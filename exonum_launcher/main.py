"""Main module of the Exonum Launcher."""
import sys
from typing import Any, Dict

from .action_result import ActionResult
from .configuration import Configuration
from .launcher import Launcher


def load_config(path: str) -> Configuration:
    """Loads configuration from yaml"""
    return Configuration.from_yaml(path)


def run_launcher(config: Configuration) -> Dict[str, Any]:
    """Runs the launcher.

    Returns a dictionary with two entries:

    "artifacts" - contains a mapping `Artifact` => `bool denoting if artifact is deployed`
    "instances" - contains a mapping `Instance` => `Optional[InstanceId]`.
    """
    with Launcher(config) as launcher:
        explorer = launcher.explorer()
        results: Dict[str, Any] = {"artifacts": dict(), "instances": dict()}

        # Unload stage
        launcher.unload_all()
        launcher.wait_for_unload()

        for artifact, status in launcher.launch_state.completed_unloads().items():
            status_description = "succeed" if status == ActionResult.Success else "failed"
            print(f"Artifact {artifact.name}:{artifact.version} -> unload status: {status_description}")

        # Deploy stage
        launcher.deploy_all()
        launcher.wait_for_deploy()

        for artifact in launcher.launch_state.completed_deployments():
            deployed = explorer.check_deployed(artifact)
            results["artifacts"][artifact] = deployed
            deployed_str = "succeed" if deployed else "failed"
            print(f"Artifact {artifact.name} -> deploy status: {deployed_str}")

        # Start stage
        launcher.start_all()
        launcher.wait_for_start()

        config_state = launcher.launch_state.get_completed_config_state(launcher.config)

        if config_state == ActionResult.Fail:
            print("Applying of config -> FAIL")

        for instance in launcher.config.instances:
            if instance.action == "start":
                instance_id = explorer.get_instance_id(instance)
                results["instances"][instance] = instance_id
                id_str = "started with ID {}".format(instance_id) if instance_id else "start failed"
                print(f"Instance {instance.name} -> start status: {id_str}")
            elif instance.action == "stop":
                print(f"Instance {instance.name} stopped")
            elif instance.action == "resume":
                print(f"Instance {instance.name} resumed")
            elif instance.action == "freeze":
                print(f"Instance {instance.name} frozen")
            elif instance.action == "config":
                print(f"Instance {instance.name} -> config '{instance.config}' applied")

        return results


def main(args: Any) -> None:
    """Runs the launcher to deploy and init all the instances from the config."""

    # Declare runtimes
    if args.runtimes:
        for runtime in args.runtimes:
            try:
                name, runtime_id = runtime.split("=")
                Configuration.declare_runtime(name, int(runtime_id))
            except ValueError:
                print("Runtimes must be provided in format `runtime_name=runtime_id`")
                sys.exit(1)

    # Load config
    config = load_config(args.input)

    # Add custom spec loaders to the config.
    if args.runtime_parsers:
        for parser in args.runtime_parsers:
            try:
                runtime_name, class_path = parser.split("=")
                config.plugins["runtime"][runtime_name] = class_path
            except ValueError as error:
                print(f"Could not load runtime parser {parser}: {error}")
                sys.exit(1)

    if args.instance_parsers:
        for parser in args.instance_parsers:
            try:
                artifact_name, class_path = parser.split("=")

                config.plugins["runtime"][artifact_name] = class_path
            except ValueError as error:
                print(f"Could not load runtime parser {parser}: {error}")
                sys.exit(1)

    # Run the launcher
    run_launcher(config)

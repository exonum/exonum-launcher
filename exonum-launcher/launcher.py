import time
from typing import Any, List

from .client import SupervisorClient
from .configuration import Artifact, Configuration, Instance


def contains_artifact(dispatcher_info: Any, expected: Artifact) -> bool:
    for value in dispatcher_info["artifacts"]:
        if value["runtime_id"] == expected.runtime_id and value["name"] == expected.name:
            return True
    return False


def find_instance_id(dispatcher_info: Any, instance: Instance) -> str:
    for value in dispatcher_info["services"]:
        if value["name"] == instance.name:
            return value["id"]
    return None


def deploy_all(networks: List[Any], artifact: Artifact):
    # Sends deploy transaction.
    for network in networks:
        client = SupervisorClient.from_dict(network)
        client.deploy_artifact(artifact)


def check_deploy(networks: List[Any], artifact: Artifact):
    for network in networks:
        client = SupervisorClient.from_dict(network)
        dispatcher_info = client.dispatcher_info()
        if not contains_artifact(dispatcher_info, artifact):
            raise Exception(
                "Deployment wasn't succeeded for artifact {}.".format(artifact.__dict__))

        print(
            "[{}] -> Deployed artifact '{}'".format(network["host"], artifact.name))


def start_all(networks: List[Any], instance: Instance):
    for network in networks:
        client = SupervisorClient.from_dict(network)
        client.start_service(instance)


def assign_instance_id(networks: List[Any], instance: Instance):
    for network in networks:
        client = SupervisorClient.from_dict(network)
        dispatcher_info = client.dispatcher_info()
        instance.id = find_instance_id(dispatcher_info, instance)
        if instance.id is None:
            raise Exception(
                "Start service wasn't succeeded for instance {}.".format(instance.__dict__))

        print(
            "[{}] -> Started service '{}' with id {}".format(network["host"], instance.name, instance.id))


def main(args) -> None:
    config = Configuration.from_yaml(args.input)
    # Deploy artifacts
    for artifact in config.artifacts.values():
        deploy_all(config.networks, artifact)

    # Wait between blocks.
    time.sleep(2)

    # Verify that deploy was succeeded.
    for artifact in config.artifacts.values():
        check_deploy(config.networks, artifact)

    # Start instances
    for instance in config.instances:
        start_all(config.networks, instance)

    # Wait between blocks.
    time.sleep(2)

    # Gets instance identifiers.
    for instance in config.instances:
        assign_instance_id(config.networks, instance)

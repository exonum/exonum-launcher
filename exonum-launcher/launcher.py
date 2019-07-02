from typing import Dict, Any, List

import time
import yaml

from .configuration import Configuration, Artifact, Instance
from .client import SupervisorClient


def deploy_all(networks: List[Any], artifact: Artifact):
    for network in networks:
        client = SupervisorClient.from_dict(network)
        txid = client.deploy_artifact(artifact)
        print(
            "[{}] -> Deploy artifact '{}'".format(network["host"], artifact.name))


def start_all(networks: List[Any], instance: Instance):
    for network in networks:
        client = SupervisorClient.from_dict(network)
        txid = client.start_service(instance)

        print(
            "[{}] -> Start service '{}'".format(network["host"], instance.name))


def main(args) -> None:
    config = Configuration.from_yaml(args.input)
    # Deploy artifacts
    for artifact in config.artifacts.values():
        deploy_all(config.networks, artifact)
        time.sleep(2)  # wait between blocks
    # Start instances 
    for instance in config.instances:
        start_all(config.networks, instance)
        time.sleep(2)  # wait between blocks        

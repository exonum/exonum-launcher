import time
from typing import Any, List, Dict, Optional
from exonum import ExonumClient

from .client import SupervisorClient
from .configuration import Artifact, Configuration, Instance


class Launcher:
    # TODO should it be configurable?
    ''' Amount of retries to connect to the exonum client. '''
    RECONNECT_RETRIES = 5
    ''' Wait interval between connection attempts in seconds. '''
    RECONNECT_INTERVAL = 0.1

    def __init__(self, config_path: str):
        self.config = Configuration.from_yaml(config_path)
        # TODO check the validity of the networks
        # TODO think of the correctness of the clients management

        network = self.config.networks[0]
        self.clients: List[ExonumClient] = []

        for network in self.config.networks:
            client = ExonumClient(network['host'], network['public-api-port'],
                                  network['public-api-port'], network['ssl'])
            self.clients.append(client)

        self.loader = self.clients[0].protobuf_loader()

        self._pending_deployments: Dict[Artifact, str] = {}
        self._pending_initializations: Dict[Instance, str] = {}
        self._completed_deployments: List[Artifact] = []
        self._completed_initializations: List[Instance] = []

    def __enter__(self):
        self.initialize()

        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.deinitalize()

    def initialize(self):
        self.loader.initialize()

        self.loader.load_main_proto_files()

        services = self.loader.available_services().json()

        self._supervisor_runtime_id = 0
        self._supervisor_artifact_name = ''

        for artifacts in services['artifacts']:
            if artifact['name'].startswith('exonum-supervisor'):
                self._supervisor_runtime_id = artifact['runtime_id']
                self._supervisor_artifact_name = artifact['name']
                break

        # TODO there should be a proper error handling here
        assert self._supervisor_artifact_name != '', 'Could not find exonum-supervisor in available artifacts'

        self.loader.load_service_proto_files(self._supervisor_runtime_id, self._supervisor_artifact_name)

    def deinitialize(self):
        self.loader.deinitialize()

    def supervisor_data(self):
        return (self._supervisor_runtime_id, self._supervisor_artifact_name)

    def protobuf_loader(self):
        return self.loader

    def exonum_clients(self):
        return self.clients

    def pending_deployments(self):
        return self._pending_deployments

    def pending_initializations(self):
        return self._pending_initializations

    def completed_deployments(self):
        return self._completed_deployments

    def completed_initializations(self):
        return self._completed_initializations

    def deploy_artifact(self, artifact):
        pass

    def wait_for_deploy(self, artifact):
        pass

    def start_service_instance(self, instance):
        pass

    def wait_for_instance_start(self, instance):
        pass


def contains_artifact(dispatcher_info: Any, expected: Artifact) -> bool:
    for value in dispatcher_info["artifacts"]:
        if value["runtime_id"] == expected.runtime_id and value["name"] == expected.name:
            return True
    return False


def find_instance_id(dispatcher_info: Any, instance: Instance) -> Optional[str]:
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

import codecs
import time
import json
import requests
from typing import Any, List, Dict, Optional
from exonum import ExonumClient, ModuleManager

# from .client import SupervisorClient
from .configuration import Artifact, Configuration, Instance
from .utils import encode


def _msg_to_hex(msg) -> str:
    return encode(msg.SerializeToString())


# TODO proper error handling
def _post_json(url: str, data: Any) -> Any:
    data = json.dumps(data)
    response = requests.post(url, data=data, headers={
                             "content-type": "application/json"})
    return response


class Launcher:
    # TODO should it be configurable?
    ''' Amount of retries to connect to the exonum client. '''
    RECONNECT_RETRIES = 5
    ''' Wait interval between connection attempts in seconds. '''
    RECONNECT_INTERVAL = 0.1

    def __init__(self, config):
        self.config = config
        # TODO check the validity of the networks
        # TODO think of the correctness of the clients management

        network = self.config.networks[0]
        self.clients: List[ExonumClient] = []

        for network in self.config.networks:
            client = ExonumClient(network['host'], network['public-api-port'],
                                  network['private-api-port'], network['ssl'])
            self.clients.append(client)

        self.loader = self.clients[0].protobuf_loader()

        self._pending_deployments: Dict[Artifact, List[str]] = {}
        self._pending_initializations: Dict[Instance, List[str]] = {}
        self._completed_deployments: List[Artifact] = []
        self._completed_initializations: List[Instance] = []

    def __enter__(self):
        self.initialize()

        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.deinitialize()

    def initialize(self):
        self.loader.initialize()

        self.loader.load_main_proto_files()

        services = self.clients[0].available_services().json()

        self._supervisor_runtime_id = 0
        self._supervisor_artifact_name = ''

        for artifact in services['artifacts']:
            if artifact['name'].startswith('exonum-supervisor'):
                self._supervisor_runtime_id = artifact['runtime_id']
                self._supervisor_artifact_name = artifact['name']
                break

        # TODO there should be a proper error handling here
        assert self._supervisor_artifact_name != '', 'Could not find exonum-supervisor in available artifacts'

        self.loader.load_service_proto_files(self._supervisor_runtime_id, self._supervisor_artifact_name)

        self.service_module = ModuleManager.import_service_module(self._supervisor_artifact_name, 'service')

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

    def deploy_all(self):
        for artifact_name, artifact in self.config.artifacts.items():
            deploy_request = self.service_module.DeployRequest()

            # TODO add spec to the request.
            deploy_request.artifact.runtime_id = artifact.runtime_id
            deploy_request.artifact.name = artifact.name
            deploy_request.deadline_height = artifact.deadline_height
            # deploy_request.spec = ???

            self._pending_deployments[artifact] = []
            for client in self.clients:
                deploy_uri = client.service_endpoint('supervisor', 'deploy-artifact', private=True)
                print(deploy_uri)
                response = _post_json(deploy_uri, _msg_to_hex(deploy_request))
                print(response)
                print(response.json())
                self._pending_deployments[artifact].append(response)
                print('OK')

    def wait_for_deploy(self):
        # TODO
        # for idx, (artifact, tx_hash) in self._pending_deployments.items():
        # status = self.get_tx_info(tx_hash)['']
        time.sleep(2)

    # TODO error-handling. API may be remounted during this method call.
    def start_all(self):
        for instance in self.config.instances:
            start_request = self.service_module.StartService()

            # TODO add config to the request.
            start_request.artifact.runtime_id = instance.artifact.runtime_id
            start_request.artifact.name = instance.artifact.name
            start_request.name = instance.name
            start_request.deadline_height = instance.deadline_height
            # start_request.config = ???

            self._pending_initializations[instance] = []
            for client in self.clients:
                start_service_uri = client.service_endpoint('supervisor', 'start-service', private=True)
                response = _post_json(start_service_uri, _msg_to_hex(start_request))
                self._pending_initializations[instance].append(response)
                print('OK')

    def wait_for_start(self):
        # TODO
        time.sleep(2)


# def contains_artifact(dispatcher_info: Any, expected: Artifact) -> bool:
#     for value in dispatcher_info["artifacts"]:
#         if value["runtime_id"] == expected.runtime_id and value["name"] == expected.name:
#             return True
#     return False


# def find_instance_id(dispatcher_info: Any, instance: Instance) -> Optional[str]:
#     for value in dispatcher_info["services"]:
#         if value["name"] == instance.name:
#             return value["id"]
#     return None


# def deploy_all(networks: List[Any], artifact: Artifact):
#     # Sends deploy transaction.
#     for network in networks:
#         client = SupervisorClient.from_dict(network)
#         client.deploy_artifact(artifact)


# def check_deploy(networks: List[Any], artifact: Artifact):
#     for network in networks:
#         client = SupervisorClient.from_dict(network)
#         dispatcher_info = client.dispatcher_info()
#         if not contains_artifact(dispatcher_info, artifact):
#             raise Exception(
#                 "Deployment wasn't succeeded for artifact {}.".format(artifact.__dict__))

#         print(
#             "[{}] -> Deployed artifact '{}'".format(network["host"], artifact.name))


# def start_all(networks: List[Any], instance: Instance):
#     for network in networks:
#         client = SupervisorClient.from_dict(network)
#         client.start_service(instance)


# def assign_instance_id(networks: List[Any], instance: Instance):
#     for network in networks:
#         client = SupervisorClient.from_dict(network)
#         dispatcher_info = client.dispatcher_info()
#         instance.id = find_instance_id(dispatcher_info, instance)
#         if instance.id is None:
#             raise Exception(
#                 "Start service wasn't succeeded for instance {}.".format(instance.__dict__))

#         print(
#             "[{}] -> Started service '{}' with id {}".format(network["host"], instance.name, instance.id))


def main(args) -> None:
    config = Configuration.from_yaml(args.input)

    with Launcher(config) as launcher:
        launcher.deploy_all()

        launcher.wait_for_deploy()

        # for artifact in launcher.completed_deployments():
        #     deployed = launcher.check_deployed(artifact)

        launcher.start_all()

        launcher.wait_for_start()

        # for instance in launcher.completed_initializations():
        #     instance_id = launcher.get_instance_id(instance)

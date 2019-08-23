import time
import json
import requests
from requests.exceptions import ConnectionError
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


class NotCommittedError(Exception):
    pass


class Launcher:
    # TODO should it be configurable?
    """ Amount of retries to connect to the exonum client. """
    RECONNECT_RETRIES = 10
    """ Wait interval between connection attempts in seconds. """
    RECONNECT_INTERVAL = 0.2

    def __init__(self, config):
        self.config = config
        # TODO check the validity of the networks
        # TODO think of the correctness of the clients management

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
        return self._supervisor_runtime_id, self._supervisor_artifact_name

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

    def _post_to_supervisor(self, endpoint, message, private=True) -> List[str]:
        responses = []
        for client in self.clients:
            supervisor_uri = client.service_endpoint('supervisor', endpoint, private)
            response = _post_json(supervisor_uri, _msg_to_hex(message))
            responses.append(response.json())

        return responses

    def _wait_until_txs_are_committed(self, tx_hashes: List[str]):
        client = self.clients[0]
        for idx, tx_hash in enumerate(tx_hashes):
            success = False
            for _ in range(self.RECONNECT_RETRIES):
                try:
                    info = client.get_tx_info(tx_hash).json()
                    status = info['type']

                    if status != 'committed':
                        with client.create_subscriber() as subscriber:
                            subscriber.wait_for_new_block()
                    else:
                        success = True
                        break
                except ConnectionError:
                    # Exonum API server may be rebooting. Wait for it.
                    time.sleep(self.RECONNECT_INTERVAL)
                    continue

            if not success:
                raise NotCommittedError('Tx [{}] was not committed.'.format(tx_hash))

    def deploy_all(self):
        for artifact_name, artifact in self.config.artifacts.items():
            deploy_request = self.service_module.DeployRequest()

            # TODO add spec to the request.
            deploy_request.artifact.runtime_id = artifact.runtime_id
            deploy_request.artifact.name = artifact.name
            deploy_request.deadline_height = artifact.deadline_height
            # deploy_request.spec = ???

            self._pending_deployments[artifact] = self._post_to_supervisor('deploy-artifact', deploy_request)

    def wait_for_deploy(self):
        for tx_hashes in self._pending_deployments.values():
            self._wait_until_txs_are_committed(tx_hashes)

        for artifact in self._pending_deployments.keys():
            for _ in range(self.RECONNECT_RETRIES):
                if self.check_deployed(artifact):
                    break
                else:
                    with self.clients[0].create_subscriber() as subscriber:
                        subscriber.wait_for_new_block()

        self._completed_deployments = self._pending_deployments.keys()
        self._pending_deployments = {}

    def start_all(self):
        for instance in self.config.instances:
            start_request = self.service_module.StartService()

            # TODO add config to the request.
            start_request.artifact.runtime_id = instance.artifact.runtime_id
            start_request.artifact.name = instance.artifact.name
            start_request.name = instance.name
            start_request.deadline_height = instance.deadline_height

            if instance.config:
                config = self.get_service_config(instance)
                start_request.config.Pack(config)

            self._pending_initializations[instance] = self._post_to_supervisor('start-service', start_request)

    def wait_for_start(self):
        for tx_hashes in self._pending_initializations.values():
            self._wait_until_txs_are_committed(tx_hashes)

        for instance in self._pending_initializations.keys():
            for _ in range(self.RECONNECT_RETRIES):
                if self.get_instance_id(instance):
                    break
                else:
                    with self.clients[0].create_subscriber() as subscriber:
                        subscriber.wait_for_new_block()

        self._completed_initializations = self._pending_initializations.keys()
        self._pending_initializations = {}

    def check_deployed(self, artifact: Artifact, network_id=0) -> bool:
        dispatcher_info = self.clients[network_id].available_services().json()

        for value in dispatcher_info['artifacts']:
            if value['runtime_id'] == artifact.runtime_id and value['name'] == artifact.name:
                return True

        return False

    def get_instance_id(self, instance: Instance, network_id=0) -> Optional[str]:
        dispatcher_info = self.clients[network_id].available_services().json()

        for value in dispatcher_info['services']:
            if value['name'] == instance.name:
                return value['id']

        return None

    def get_service_config(self, instance):
        self.loader.load_service_proto_files(instance.artifact.runtime_id, instance.artifact.name)
        service_module = ModuleManager.import_service_module(instance.artifact.name, "service")
        config = service_module.Config()

        for key, value in instance.config.items():
            assert key in config.DESCRIPTOR.fields_by_name.keys()
            setattr(config, key, value)

        return config


def main(args) -> None:
    config = Configuration.from_yaml(args.input)

    with Launcher(config) as launcher:
        launcher.deploy_all()

        launcher.wait_for_deploy()

        for artifact in launcher.completed_deployments():
            deployed = launcher.check_deployed(artifact)
            deployed_str = 'succeed' if deployed else 'failed'
            print('Artifact {} -> deploy status: {}'.format(artifact.name, deployed_str))

        launcher.start_all()

        launcher.wait_for_start()

        for instance in launcher.completed_initializations():
            instance_id = launcher.get_instance_id(instance)
            id_str = 'started with ID {}'.format(instance_id) if instance_id else 'start failed'
            print('Instance {} -> start status: {}'.format(instance.name, id_str))

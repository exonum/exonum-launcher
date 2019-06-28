from typing import Dict, Any, List

import time
import yaml

from .configuration import Configuration, Artifact, Instance
from .client import SupervisorClient


def deploy_all(networks: List[Any], artifact: Artifact):
    for network in networks:
        client = SupervisorClient.from_dict(network)
        txid = client.deploy_artifact(artifact, 100000)

        print(
            "[{}] -> Deploy artifact '{}' with id: {}".format(network["host"], artifact.name, txid))


def start_all(networks: List[Any], instance: Instance):
    for network in networks:
        client = SupervisorClient.from_dict(network)
        txid = client.start_service(instance)

        print(
            "[{}] -> Start service '{}' with id: {}".format(network["host"], instance.name, txid))


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

    # Start services

        # data = load_config(args.input)

        # transactions = data["transactions"]

        # exonum_cfg = data["exonum"]

        # client = ExonumClient(
        #     exonum_cfg["hostname"], exonum_cfg["public_api_port"], exonum_cfg["ssl"])

        # pk, sk = gen_keypair()

        # for transaction in transactions:
        #     signed_tx = None
        #     if transaction['type'] == 'deploy':
        #         signed_tx = get_signed_deploy_tx(pk, sk, transaction)
        #     elif transaction['type'] == 'init':
        #         signed_tx = get_signed_init_tx(pk, sk, transaction)
        #     else:
        #         signed_tx = get_custom_tx(pk, sk, transaction)

        #     response = client.send_raw_tx(signed_tx.SerializeToString())
        #     print(response)

        #     time.sleep(1)  # 1 second wait between blocks

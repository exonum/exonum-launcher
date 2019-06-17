from typing import Dict, Any

import time

from .utils import gen_keypair, load_config
from .messages import DeployMessages, get_signed_deploy_tx, get_signed_init_tx, get_custom_tx
from .client import ExonumClient


def main(args) -> None:
    data = load_config(args.input)

    transactions = data["transactions"]

    exonum_cfg = data["exonum"]

    client = ExonumClient(
        exonum_cfg["hostname"], exonum_cfg["public_api_port"], exonum_cfg["ssl"])

    pk, sk = gen_keypair()

    for transaction in transactions:
        signed_tx = None
        if transaction['type'] == 'deploy':
            signed_tx = get_signed_deploy_tx(pk, sk, transaction)
        elif transaction['type'] == 'init':
            signed_tx = get_signed_init_tx(pk, sk, transaction)
        else:
            signed_tx = get_custom_tx(pk, sk, transaction)

        response = client.send_raw_tx(signed_tx.SerializeToString())
        print(response)

        time.sleep(1)  # 1 second wait between blocks

from typing import Dict, Any

from .utils import gen_keypair, load_config
from .messages import DeployMessages, get_signed_tx
from .client import ExonumClient


def main(args) -> None:
    data = load_config(args.input)

    transactions = data["transactions"]

    exonum_cfg = data["exonum"]

    client = ExonumClient(exonum_cfg["hostname"], exonum_cfg["public_api_port"], exonum_cfg["ssl"])

    pk, sk = gen_keypair()

    for transaction in transactions:
        signed_tx = get_signed_tx(pk, sk, transaction)

        response = client.send_raw_tx(signed_tx.SerializeToString())
        print(response)

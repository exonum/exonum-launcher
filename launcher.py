from typing import Tuple, Dict, Any

import json

from .utils import gen_keypair
from .messages import DeployMessages
from .client import ExonumClient

CONFIGURATION_SERVICE_ID = 1
DEPLOY_INIT_METHOD_ID = 5
RUST_RUNTIME_ID = 0
ACTIVATION_HEIGHT_IMMEDIATELY = 0


def load_config(path: str) -> Dict[Any, Any]:
    with open(path) as f:
        return json.load(f)


def main(args) -> None:
    data = load_config(args.input)

    transactions = data["transactions"]
    artifact_spec_data = transactions[0]["artifact_spec"]
    instance_name = transactions[0]["instance_name"]
    init_data = transactions[0]["init_data"]

    exonum_cfg = data["exonum"]

    pk, sk = gen_keypair()

    call_info = DeployMessages.call_info(CONFIGURATION_SERVICE_ID, DEPLOY_INIT_METHOD_ID)

    artifact_spec = DeployMessages.rust_artifact_spec(artifact_spec_data["name"], artifact_spec_data["version"])
    deploy_tx = DeployMessages.deploy_tx(RUST_RUNTIME_ID, ACTIVATION_HEIGHT_IMMEDIATELY, artifact_spec)

    tx = DeployMessages.any_tx(call_info, deploy_tx)

    signed_tx = DeployMessages.signed_message(tx, pk, sk)

    print(signed_tx)

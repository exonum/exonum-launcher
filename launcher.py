from typing import Tuple, Dict

from .proto import runtime_pb2 as runtime
from .proto import configuration_pb2 as configuration
from .proto import protocol_pb2 as protocol
from .proto import helpers_pb2 as helpers
import google.protobuf.internal.well_known_types as well_known_types
from google.protobuf.message import Message

from pysodium import crypto_sign_keypair, crypto_sign_detached
import requests
import json
import codecs


CONFIGURATION_SERVICE_ID = 1
DEPLOY_INIT_METHOD_ID = 5
RUST_RUNTIME_ID = 0
ACTIVATION_HEIGHT_IMMEDIATELY = 0


class DeployMessages:
    def rust_artifact_spec(name: str, version: str) -> runtime.RustArtifactSpec:
        artifact_spec = runtime.RustArtifactSpec()
        artifact_spec.name = name
        artifact_spec.version.CopyFrom(runtime.Version(data=version))

        return artifact_spec

    def call_info(instance_id: int, method_id: int) -> protocol.CallInfo:
        call_info = protocol.CallInfo()
        call_info.instance_id = instance_id
        call_info.method_id = method_id

        return call_info

    def deploy_tx(runtime_id: int, activation_height: int, artifact_spec: Message) -> configuration.DeployTx:
        deploy_tx = configuration.DeployTx()
        deploy_tx.runtime_id = runtime_id
        deploy_tx.activation_height = activation_height
        deploy_tx.artifact_spec.Pack(artifact_spec)

        return deploy_tx

    def any_tx(call_info: protocol.CallInfo, payload: Message) -> protocol.AnyTx:
        tx = protocol.AnyTx()
        tx.dispatch.CopyFrom(call_info)
        tx.payload = payload.SerializeToString()

        return tx

    def signed_message(msg: Message, pk: bytes, sk: bytes) -> protocol.SignedMessage:
        signed_message = protocol.SignedMessage()

        signed_message.exonum_msg = msg.SerializeToString()
        signed_message.key.CopyFrom(helpers.PublicKey(data=pk))

        signature = bytes(sign(signed_message.exonum_msg, sk))

        signed_message.sign.CopyFrom(helpers.Signature(data=signature))

        return signed_message


def gen_keypair() -> Tuple[bytes, bytes]:
    return crypto_sign_keypair()


def sign(data: bytes, sk: bytes) -> bytes:
    return crypto_sign_detached(data, sk)


def encode(bytes):
    return codecs.encode(bytes, "hex").decode("utf-8")


class ExonumClient(object):
    def __init__(
        self, hostname: str, public_api_port=80, private_api_port=81, ssl=False
    ) -> ExonumClient:
        self.schema = "https" if ssl else "http"
        self.hostname = hostname
        self.public_api_port = public_api_port
        self.private_api_port = private_api_port
        self.service_name = service_name
        self.tx_url = TX_URL.format(self.schema, hostname, public_api_port)

    def send_raw_tx(self, tx: bytes) -> Dict[str, str]:
        try:
            response = requests.post(
                self.tx_url,
                data=tx.to_json(),
                headers={"content-type": "application/json"},
            )
            return response
        except Exception as e:
            return {"error": str(e)}

    def _msg_to_json(self, tx) -> str:
        return json.dumps({"tx_body": encode(tx)}, indent=4)


def main(args) -> None:
    pk, sk = gen_keypair()

    call_info = DeployMessages.call_info(CONFIGURATION_SERVICE_ID, DEPLOY_INIT_METHOD_ID)

    artifact_spec = DeployMessages.rust_artifact_spec("cryptocurrency", "0.0.1")
    deploy_tx = DeployMessages.deploy_tx(RUST_RUNTIME_ID, ACTIVATION_HEIGHT_IMMEDIATELY, artifact_spec)

    tx = DeployMessages.any_tx(call_info, deploy_tx)

    signed_tx = DeployMessages.signed_message(tx, pk, sk)

    print(signed_tx)


if __name__ == "__main__":
    main()

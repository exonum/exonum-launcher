from typing import Tuple

import proto.runtime_pb2 as runtime
import proto.configuration_pb2 as configuration
import proto.protocol_pb2 as protocol
import proto.helpers_pb2 as helpers
import google.protobuf.internal.well_known_types as well_known_types
from google.protobuf.message import Message

from pysodium import crypto_sign_keypair, crypto_sign_detached


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


def main() -> None:
    pk, sk = gen_keypair()

    call_info = DeployMessages.call_info(0, 0)

    artifact_spec = DeployMessages.rust_artifact_spec("cryptocurrency", "0.0.1")
    deploy_tx = DeployMessages.deploy_tx(0, 0, artifact_spec)

    tx = DeployMessages.any_tx(call_info, deploy_tx)

    signed_tx = DeployMessages.signed_message(tx, pk, sk)

    print(signed_tx)


if __name__ == "__main__":
    main()

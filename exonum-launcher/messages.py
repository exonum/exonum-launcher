from typing import Dict, Any

from .proto import runtime_pb2 as runtime
from .proto import configuration_pb2 as configuration
from .proto import protocol_pb2 as protocol
from .proto import helpers_pb2 as helpers
import google.protobuf.internal.well_known_types as well_known_types
from google.protobuf.message import Message

from .utils import sign

CONFIGURATION_SERVICE_ID = 1
DEPLOY_INIT_METHOD_ID = 5
RUST_RUNTIME_ID = 0
ACTIVATION_HEIGHT_IMMEDIATELY = 0


class DeployMessages:
    @staticmethod
    def rust_artifact_spec(name: str, version: str) -> runtime.RustArtifactSpec:
        artifact_spec = runtime.RustArtifactSpec()
        artifact_spec.name = name
        artifact_spec.version.CopyFrom(runtime.Version(data=version))

        return artifact_spec

    @staticmethod
    def call_info(instance_id: int, method_id: int) -> protocol.CallInfo:
        call_info = protocol.CallInfo()
        call_info.instance_id = instance_id
        call_info.method_id = method_id

        return call_info

    @staticmethod
    def deploy_tx(runtime_id: int, activation_height: int, artifact_spec: Message) -> configuration.DeployTx:
        deploy_tx = configuration.DeployTx()
        deploy_tx.runtime_id = runtime_id
        deploy_tx.activation_height = activation_height
        deploy_tx.artifact_spec.Pack(artifact_spec)

        return deploy_tx

    @staticmethod
    def any_tx(call_info: protocol.CallInfo, payload: Message) -> protocol.AnyTx:
        tx = protocol.AnyTx()
        tx.dispatch.CopyFrom(call_info)
        tx.payload = payload.SerializeToString()

        return tx

    @staticmethod
    def signed_message(msg: Message, pk: bytes, sk: bytes) -> protocol.SignedMessage:
        signed_message = protocol.SignedMessage()

        signed_message.exonum_msg = msg.SerializeToString()
        signed_message.key.CopyFrom(helpers.PublicKey(data=pk))

        signature = bytes(sign(signed_message.exonum_msg, sk))

        signed_message.sign.CopyFrom(helpers.Signature(data=signature))

        return signed_message


def get_signed_tx(pk: bytes, sk: bytes, artifact: Dict[Any, Any]) -> protocol.SignedMessage:
    artifact_name = artifact["artifact_spec"]["name"]
    artifact_version = artifact["artifact_spec"]["version"]

    call_info = DeployMessages.call_info(CONFIGURATION_SERVICE_ID, DEPLOY_INIT_METHOD_ID)

    artifact_spec = DeployMessages.rust_artifact_spec(artifact_name, artifact_version)
    deploy_tx = DeployMessages.deploy_tx(RUST_RUNTIME_ID, ACTIVATION_HEIGHT_IMMEDIATELY, artifact_spec)

    tx = DeployMessages.any_tx(call_info, deploy_tx)

    signed_tx = DeployMessages.signed_message(tx, pk, sk)

    return signed_tx

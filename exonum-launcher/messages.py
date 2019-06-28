from typing import Dict, Any, List
import sys
import os
import importlib
import json

import google.protobuf.internal.well_known_types as well_known_types
import google.protobuf.json_format as json_format
from google.protobuf.message import Message

from .utils import sign

# Dynamically load protobuf modules.
proto_path = os.environ.get("EXONUM_LAUNCHER_PROTO_PATH", "")
try:
    sys.path.append(proto_path)

    from proto import runtime_pb2 as runtime
    from proto import protocol_pb2 as protocol
    from proto import helpers_pb2 as helpers
except (ModuleNotFoundError, ImportError):
    print("Incorrect directory for proto files was provided")
    exit(1)


CONFIGURATION_SERVICE_ID = 1
DEPLOY_METHOD_ID = 3
INIT_METHOD_ID = 4
DEPLOY_INIT_METHOD_ID = 5
RUST_RUNTIME_ID = 0
ACTIVATION_HEIGHT_IMMEDIATELY = 0


class DeployMessages:
    @staticmethod
    def call_info(instance_id: int, method_id: int) -> protocol.CallInfo:
        call_info = protocol.CallInfo()
        call_info.instance_id = instance_id
        call_info.method_id = method_id

        return call_info

    @staticmethod
    def any_tx(call_info: protocol.CallInfo, payload: Message) -> protocol.AnyTx:
        tx = protocol.AnyTx()
        tx.call_info.CopyFrom(call_info)
        tx.payload = payload.SerializeToString()

        return tx

    @staticmethod
    def exonum_message_from_any_tx(any_tx: protocol.AnyTx) -> protocol.ExonumMessage:
        exonum_msg = protocol.ExonumMessage()
        exonum_msg.transaction.CopyFrom(any_tx)

        return exonum_msg

    @staticmethod
    def signed_message(msg: Message, pk: bytes, sk: bytes) -> protocol.SignedMessage:
        signed_message = protocol.SignedMessage()

        signed_message.exonum_msg = msg.SerializeToString()
        signed_message.key.CopyFrom(helpers.PublicKey(data=pk))

        signature = bytes(sign(signed_message.exonum_msg, sk))

        signed_message.sign.CopyFrom(helpers.Signature(data=signature))

        return signed_message

def get_all_service_messages(service_name: str, module_name: str) -> Dict[str, type]:
    # Warning: this function assumes that messages for
    # artifact named `example` lie in `example/service_pb2.py`
    service = importlib.import_module(
        '{}.{}_pb2'.format(service_name, module_name))

    return service.__dict__


def get_service_config_structure(service_name: str, module_name: str) -> type:
    # Warning: this function assumes that Config for
    # artifact named `example` lies in `example/service_pb2.py`
    return get_all_service_messages(service_name, module_name)['Config']

def get_custom_tx(pk: bytes, sk: bytes, artifact: Dict[Any, Any]) -> protocol.SignedMessage:
    artifact_name = artifact["artifact"]["name"]
    artifact_module = artifact["artifact"]["module"]
    service_id = artifact["service_id"]
    method_id = artifact["method_id"]
    tx_name = artifact["type"]
    json_data = json.dumps(artifact["data"])

    call_info = DeployMessages.call_info(service_id, method_id)

    tx = get_all_service_messages(artifact_name, artifact_module)[tx_name]()

    json_format.Parse(json_data, tx)

    tx = DeployMessages.any_tx(call_info, tx)

    exonum_msg = DeployMessages.exonum_message_from_any_tx(tx)

    signed_tx = DeployMessages.signed_message(exonum_msg, pk, sk)

    return signed_tx

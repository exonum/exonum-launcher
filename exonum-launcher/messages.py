from typing import Dict, Any, List
import sys
import os
import importlib
import json

import google.protobuf.internal.well_known_types as well_known_types
import google.protobuf.json_format as json_format
from google.protobuf.message import Message
from google.protobuf.any_pb2 import Any as PbAny

from .utils import sign
from .configuration import Artifact, Instance

# Dynamically load protobuf modules.
proto_path = os.environ.get("EXONUM_LAUNCHER_PROTO_PATH", "")
sys.path.append(proto_path)

from exonum_proto import runtime_pb2 as runtime
from exonum_proto import protocol_pb2 as protocol
from exonum_proto import helpers_pb2 as helpers
from exonum_proto import supervisor_pb2 as supervisor



def get_all_service_messages(service_name: str, module_name: str) -> Dict[str, type]:
    # Warning: this function assumes that messages for
    # artifact named `example` lie in `example/service_pb2.py`
    service = importlib.import_module(
        'services.{}.{}_pb2'.format(service_name, module_name))

    return service.__dict__


def get_service_config_structure(service_name: str, module_name: str) -> type:
    # Warning: this function assumes that Config for
    # artifact named `example` lies in `example/service_pb2.py`
    return get_all_service_messages(service_name, module_name)['Config']


def artifact_id(artifact: Artifact) -> runtime.ArtifactId:
    artifact_id = runtime.ArtifactId()
    artifact_id.runtime_id = artifact.runtime_id
    artifact_id.name = artifact.name
    return artifact_id


def serialize_spec(artifact: Artifact, data: Any) -> PbAny:
    output = PbAny()
    if data is not None:
        # TODO This way is runtime specific.
        pass
    
    return output


def serialize_config(artifact: Artifact, data: Any) -> PbAny:
    output = PbAny()
    if data is not None:
        json_data = json.dumps(data)
        msg = get_service_config_structure(artifact.module, artifact.module)()
        json_format.Parse(json_data, msg)
        output.Pack(msg)

    return output


class Supervisor:
    @staticmethod
    def deploy_artifact(artifact: Artifact) -> supervisor.DeployArtifact:
        msg = supervisor.DeployArtifact()
        msg.artifact.CopyFrom(artifact_id(artifact))
        msg.deadline_height = artifact.deadline_height
        msg.spec.CopyFrom(serialize_spec(artifact, artifact.spec))
        return msg

    @staticmethod
    def start_service(instance: Instance) -> supervisor.StartService:
        msg = supervisor.StartService()
        msg.artifact.CopyFrom(artifact_id(instance.artifact))
        msg.name = instance.name
        msg.deadline_height = instance.deadline_height
        msg.config.CopyFrom(serialize_config(
            instance.artifact, instance.config))
        return msg

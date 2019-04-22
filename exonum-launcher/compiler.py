from typing import Optional

import os
import shutil
import subprocess

PROTOC_ENV_NAME = "PROTOC"
EXONUM_PROTO_PATH = "--proto_path={}/exonum/src/proto/schema/exonum"
SERVICE_PROTO_PATH = "--proto_path={}"
HELPERS_PROTO = "helpers.proto"
CONFIGURATION_PROTO = "configuration.proto"
RUNTIME_PROTO = "runtime.proto"
PROTOCOL_PROTO = "protocol.proto"
BLOCKCHAIN_PROTO = "blockchain.proto"


def find_protoc() -> Optional[str]:
    if PROTOC_ENV_NAME in os.environ:
        return os.getenv(PROTOC_ENV_NAME)
    else:
        return shutil.which("protoc")


def find_proto_files(path: str) -> str:
    return " ".join(filter(lambda file: file.endswith(".proto"), os.listdir(path)))


def fix_proto_imports(path: str) -> None:
    ''' Fixes imports in generated files '''
    with open(path, "rt") as file_in:
        file_content = file_in.readlines()

    with open(path, "wt") as file_out:
        for line in file_content:
            if line == "import helpers_pb2 as helpers__pb2\n":
                line = "from . import helpers_pb2 as helpers__pb2\n"
            elif line == "import blockchain_pb2 as blockchain__pb2\n":
                line = "from . import blockchain_pb2 as blockchain__pb2\n"
            file_out.write(line)


def create_dir_if_not_exist(path: str) -> None:
    if not os.path.exists(path):
        os.makedirs(path)


def run_protoc(protoc_args, output_dir: str) -> None:
    create_dir_if_not_exist(output_dir)
    protoc_process = subprocess.Popen(
        protoc_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    code = protoc_process.wait()
    if code == 0:
        print("Proto files for {} were compiled successfully".format(output_dir))
    else:
        out, err = protoc_process.communicate()
        print("Error acquired while compiling files: {}".format(err.decode("utf-8")))

    for file in filter(lambda f: f.endswith(".py"), os.listdir(output_dir)):
        fix_proto_imports("{}/{}".format(output_dir, file))


def main(args) -> None:
    path_to_protoc = find_protoc()

    if path_to_protoc is None:
        print("Protobuf compiler not found")
        exit(1)

    output_dir = os.path.join(args.output, 'proto')
    protoc_args = [
        path_to_protoc,
        EXONUM_PROTO_PATH.format(args.exonum_sources),
        HELPERS_PROTO,
        CONFIGURATION_PROTO,
        RUNTIME_PROTO,
        PROTOCOL_PROTO,
        BLOCKCHAIN_PROTO,
        "--python_out={}".format(output_dir),
    ]
    run_protoc(protoc_args, output_dir)

    for service_info in args.services:
        service_name, service_path = service_info.split(':')
        output_dir = os.path.join(args.output, service_name)
        protoc_args = [
            path_to_protoc,
            EXONUM_PROTO_PATH.format(args.exonum_sources),
            SERVICE_PROTO_PATH.format(service_path),
            HELPERS_PROTO,
            find_proto_files(service_path),
            "--python_out={}".format(output_dir),
        ]
        run_protoc(protoc_args, output_dir)

from typing import Optional, List

import os
import shutil
import subprocess

PROTOC_ENV_NAME = "PROTOC"
EXONUM_MODULES = [
    "helpers",
    "supervisor",
    "runtime",
    "blockchain",
    "protocol",
]


def find_protoc() -> Optional[str]:
    if PROTOC_ENV_NAME in os.environ:
        return os.getenv(PROTOC_ENV_NAME)
    else:
        return shutil.which("protoc")


def find_proto_files(path: str) -> str:
    files = []
    for module_path in os.listdir(path):
        module, _pattern, tail = module_path.rpartition(".proto")
        if not tail and module:
            files += [module]
    return files


def fix_proto_imports(path: str, module: str) -> None:
    ''' Fixes imports in generated files '''
    with open(path, "rt") as file_in:
        file_content = file_in.readlines()

    with open(path, "wt") as file_out:
        for line in file_content:
            if line == "import {}_pb2 as {}__pb2\n".format(module, module):
                line = "from . import {}_pb2 as {}__pb2\n".format(
                    module, module)
            file_out.write(line)


def create_dir_if_not_exist(path: str) -> None:
    if not os.path.exists(path):
        os.makedirs(path)


class Protoc:

    def __init__(self, protoc_path: str, input_dirs: [str], output_dir: str) -> None:
        self.protoc_path = protoc_path
        self.output_dir = output_dir
        self.input_dirs = input_dirs
        self.modules = []

    def args(self) -> List[str]:
        args = [self.protoc_path]
        for input_dir in self.input_dirs:
            args += ["--proto_path=" + input_dir]
        for module in self.modules:
            args += [module + ".proto"]
        args += ["--python_out=" + self.output_dir]
        return args

    def run(self) -> None:
        create_dir_if_not_exist(self.output_dir)
        protoc_process = subprocess.Popen(
            self.args(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        code = protoc_process.wait()
        if code == 0:
            print("Proto files for {} were compiled successfully".format(
                self.output_dir))
        else:
            _out, err = protoc_process.communicate()
            print("Error acquired while compiling files: {}".format(
                err.decode("utf-8")))

        for file in filter(lambda f: f.endswith(".py"), os.listdir(self.output_dir)):
            path = "{}/{}".format(self.output_dir, file)
            for module in self.modules:
                fix_proto_imports(path, module)


def main(args) -> None:
    path_to_protoc = find_protoc()

    if path_to_protoc is None:
        print("Protobuf compiler not found")
        exit(1)

    output_dir = os.path.join(args.output, 'exonum')
    exonum_proto_path = os.path.join(
        args.exonum_sources, 'exonum', 'src', 'proto', 'schema', 'exonum')

    protoc = Protoc(protoc_path=path_to_protoc,
                    input_dirs=[exonum_proto_path],
                    output_dir=output_dir)
    protoc.modules = EXONUM_MODULES.copy()
    protoc.run()

    for service_info in args.services:
        service_name, service_path = service_info.split(':')
        output_dir = os.path.join(
            args.output, "services", service_name)

        protoc = Protoc(protoc_path=path_to_protoc,
                        input_dirs=[exonum_proto_path, service_path],
                        output_dir=output_dir)
        protoc.modules = EXONUM_MODULES.copy() + find_proto_files(service_path)
        protoc.run()

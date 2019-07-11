import time
import os, sys

from typing import Any, List

from .client import SupervisorClient
from .configuration import Artifact, Configuration, Instance
from .compiler import Protoc


def contains_artifact(dispatcher_info: Any, expected: Artifact) -> bool:
    for value in dispatcher_info["artifacts"]:
        if value["runtime_id"] == expected.runtime_id and value["name"] == expected.name:
            return True
    return False


def find_instance_id(dispatcher_info: Any, instance: Instance) -> str:
    for value in dispatcher_info["services"]:
        if value["name"] == instance.name:
            return value["id"]
    return None


def compile_proto_file(out_dir: str, package: str, files: Any):
    src_dir = os.path.join(out_dir, "sources")
    out_dir = os.path.join(out_dir, "out")

    package_out_dir = os.path.join(out_dir, package)
    package_dir = os.path.join(src_dir, package)
    if not os.path.exists(package_dir):
        os.makedirs(package_dir)

    modules = []
    for item in files:
        file_path = os.path.join(package_dir, item['name'])
        modules += [file_path]
        with open(file_path, "w") as out:
            out.write(item['content'])

    protoc = Protoc(include_dirs=[package_dir,
                                  os.path.join(src_dir, "exonum")],
                    output_dir=package_out_dir)
    protoc.modules = modules
    protoc.run()


def compile_core_artifacts(out_dir: str, network: Any):
    client = SupervisorClient.from_dict(network)

    compile_proto_file(out_dir, package="exonum", files=client.proto_sources())
    compile_proto_file(out_dir,
                    package="supervisor",
                    files=client.proto_sources(
                        artifact=Artifact(
                            "exonum-supervisor/0.11.0",
                            runtime="rust",
                            module="supervisor",
                            spec=None)))


def compile_proto_files(out_dir: str, network: Any, artifacts: List[Artifact]):
    client = SupervisorClient.from_dict(network)
    for artifact in artifacts.values():
        compile_proto_file(out_dir, package=artifact.module,
                        files=client.proto_sources(artifact=artifact))


def deploy_all(networks: List[Any], artifact: Artifact):
    # Sends deploy transaction.
    for network in networks:
        client = SupervisorClient.from_dict(network)
        client.deploy_artifact(artifact)


def check_deploy(networks: List[Any], artifact: Artifact):
    for network in networks:
        client = SupervisorClient.from_dict(network)
        dispatcher_info = client.dispatcher_info()
        if not contains_artifact(dispatcher_info, artifact):
            raise Exception(
                "Deployment wasn't succeeded for artifact {}.".format(artifact.__dict__))

        print(
            "[{}] -> Deployed artifact '{}'".format(network["host"], artifact.name))


def start_all(networks: List[Any], instance: Instance):
    for network in networks:
        client = SupervisorClient.from_dict(network)
        client.start_service(instance)


def assign_instance_id(networks: List[Any], instance: Instance):
    for network in networks:
        client = SupervisorClient.from_dict(network)
        dispatcher_info = client.dispatcher_info()
        instance.id = find_instance_id(dispatcher_info, instance)
        if instance.id is None:
            raise Exception(
                "Start service wasn't succeeded for instance {}.".format(instance.__dict__))

        print(
            "[{}] -> Started service '{}' with id {}".format(network["host"], instance.name, instance.id))


def main(args) -> None:
    config = Configuration.from_yaml(args.input)

    proto_sources_path = args.proto
    sys.path.append(os.path.join(proto_sources_path, "out", "exonum"))
    sys.path.append(os.path.join(proto_sources_path, "out", "supervisor"))

    # Download core artifacts.
    compile_core_artifacts(proto_sources_path, config.networks[0])

    # Deploy artifacts
    for artifact in config.artifacts.values():
        deploy_all(config.networks, artifact)

    # Wait between blocks.
    time.sleep(2)

    # Verify that deploy was succeeded.
    for artifact in config.artifacts.values():
        check_deploy(config.networks, artifact)

    # Download all artifacts.
    compile_proto_files(proto_sources_path,
                        config.networks[0], config.artifacts)

    # Start instances
    for instance in config.instances:
        start_all(config.networks, instance)

    # Wait between blocks.
    time.sleep(2)

    # Gets instance identifiers.
    for instance in config.instances:
        assign_instance_id(config.networks, instance)

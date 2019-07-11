import argparse
import os

from .compiler import main as compiler_main


def run() -> None:
    parser = argparse.ArgumentParser(
        prog="exonum-service-launcher", description="Exonum service launcher"
    )
    sub_parser = parser.add_subparsers(
        title="subcommands"
    )

    parser_compile = sub_parser.add_parser(
        "compile", help="Compiles proto files into Python equivalent")
    parser_compile.add_argument(
        "-e",
        "--exonum-sources",
        type=str,
        help="A path to exonum's sources",
        required=True,
    )
    parser_compile.add_argument(
        "-s",
        "--services",
        type=str,
        help="Space-separated sequence of service_name:path_to_service pairs",
        nargs='*',
    )
    parser_compile.add_argument(
        "-o",
        "--output",
        type=str,
        help="A path to the directory where compiled files should be saved",
        required=True,
    )
    parser_compile.set_defaults(func=compiler_main)

    parser_run = sub_parser.add_parser("run", help="Runs the service launcher")
    parser_run.add_argument(
        "-i",
        "--input",
        type=str,
        help="A path to json input for service initialization",
        required=True,
    )
    parser_run.add_argument(
        "-p",
        "--proto",
        type=str,
        help="A path to the directory with generated proto files",
        required=True,
    )
    parser_run.set_defaults(func=prepare_launcher)

    parser_run = sub_parser.add_parser(
        "server", help="Runs the web UI for service launcher")
    parser_run.add_argument(
        "-i",
        "--input",
        type=str,
        help="A path to json input for service initialization",
        required=True,
    )
    parser_run.add_argument(
        "-p",
        "--proto",
        type=str,
        help="A path to the directory with generated proto files",
        required=True,
    )
    parser_run.set_defaults(func=prepare_server)

    args = parser.parse_args()

    args.func(args)


def prepare_launcher(args):
    proto_path = os.path.join(args.proto, "out")

    os.environ["EXONUM_LAUNCHER_PROTO_PATH"] = proto_path

    from .launcher import main as launcher_main

    launcher_main(args)


def prepare_server(args):
    proto_path = os.path.join(args.proto, "out")
    if not os.path.exists(proto_path):
        os.makedirs(proto_path)

    os.environ["EXONUM_LAUNCHER_PROTO_PATH"] = proto_path

    from .server import main as server_main

    server_main(args)


if __name__ == "__main__":
    run()

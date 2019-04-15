import argparse

from .compiler import main as compiler_main
from .launcher import main as launcher_main


def run() -> None:
    parser = argparse.ArgumentParser(
        prog="exonum-service-launcher", description="Exonum service launcher"
    )
    sub_parser = parser.add_subparsers(
        title="subcommands"
    )

    parser_compile = sub_parser.add_parser("compile", help="Compiles proto files into Python equivalent")
    parser_compile.add_argument(
        "-e",
        "--exonum-sources",
        type=str,
        help="A path to exonum's sources",
        required=True,
    )
    parser_compile.set_defaults(func=compiler_main)

    parser_run = sub_parser.add_parser("run", help="Runs the service launcher")
    parser_run.set_defaults(func=launcher_main)

    args = parser.parse_args()

    args.func(args)


if __name__ == "__main__":
    run()

import argparse
import os


def run() -> None:
    parser = argparse.ArgumentParser(
        prog="exonum-service-launcher", description="Exonum service launcher"
    )
    sub_parser = parser.add_subparsers(
        title="subcommands"
    )

    parser_run = sub_parser.add_parser("run", help="Runs the service launcher")
    parser_run.add_argument(
        "-i",
        "--input",
        type=str,
        help="A path to json input for service initialization",
        required=True,
    )
    parser_run.set_defaults(func=prepare_launcher)

    args = parser.parse_args()

    args.func(args)


def prepare_launcher(args):
    from .launcher import main as launcher_main

    launcher_main(args)


if __name__ == "__main__":
    run()

"""Exonum Launcher runner."""
import argparse
from .launcher import main as launcher_main


def run() -> None:
    """Parses arguments and runs the application."""
    parser = argparse.ArgumentParser(prog="exonum_launcher", description="Exonum service launcher")
    sub_parser = parser.add_subparsers(title="subcommands")

    parser_run = sub_parser.add_parser("run", help="Runs the service launcher")
    parser_run.add_argument(
        "-i", "--input", type=str, help="A path to yaml input for service initialization", required=True
    )
    parser_run.set_defaults(func=launcher_main)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    run()

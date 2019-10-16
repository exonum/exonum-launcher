"""CLI for exonum launcher"""
import argparse
from .main import main as launcher_main


def run_cli() -> None:
    """Parses arguments and runs the application."""
    parser = argparse.ArgumentParser(prog="exonum_launcher", description="Exonum service launcher")

    parser.add_argument(
        "-i", "--input", type=str, help="A path to yaml input for service initialization", required=True
    )

    parser.add_argument(
        "-r",
        "--runtimes",
        type=str,
        nargs="+",
        help="Additional runtimes, e.g. `--runtimes java=1 python=2 wasm=3`",
        required=False,
    )

    parser.add_argument(
        "--runtime-parsers",
        type=str,
        nargs="+",
        help="""
        Runtime spec parsers, e.g. `--runtime-parsers python=your_module.YourRuntimeSpecLoader`
        Values will be imported and treated like SpecLoader, so ensure that module with loader is in `sys.path`.
        """,
        required=False,
    )

    parser.add_argument(
        "--instance-parsers",
        type=str,
        nargs="+",
        help="""
        Instance spec parsers, e.g. `--runtime-parsers python=your_module.YourInstanceSpecLoader`
        Values will be imported and treated like InstanceSpecLoader, so ensure that module with loader is in `sys.path`.
        """,
        required=False,
    )

    args = parser.parse_args()
    launcher_main(args)

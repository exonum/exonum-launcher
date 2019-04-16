# Exonum Dynamic Service Launcher

A tool to send deploy&init transactions into the Exonum blockchain.

## Capabilities

Tool has 2 subcommands: `compile` and `run`.

The first one compiles `*.proto` files into python.

The second one sends transactions into the blockchain.


```sh
usage: exonum-service-launcher [-h] {compile,run} ...

Exonum service launcher

optional arguments:
  -h, --help     show this help message and exit

subcommands:
  {compile,run}
    compile      Compiles proto files into Python equivalent
    run          Runs the service launcher
```

Usage of the `compile` subcommand:

```sh
usage: exonum-service-launcher compile [-h] -e EXONUM_SOURCES
                                       [-s [SERVICE_PATHS [SERVICE_PATHS ...]]]
                                       -o OUTPUT

optional arguments:
  -h, --help            show this help message and exit
  -e EXONUM_SOURCES, --exonum-sources EXONUM_SOURCES
                        A path to exonums sources
  -s [SERVICE_PATHS [SERVICE_PATHS ...]], --service-paths [SERVICE_PATHS [SERVICE_PATHS ...]]
                        Space-separated paths to the directory with services
                        proto files
  -o OUTPUT, --output OUTPUT
                        A path to the directory where compiled files should be
                        saved
```

Usage of the `run` subcommand:

```sh
usage: exonum-service-launcher run [-h] -i INPUT -p PROTO

optional arguments:
  -h, --help            show this help message and exit
  -i INPUT, --input INPUT
                        A path to json input for service initialization
  -p PROTO, --proto PROTO
                        A path to the directory with generated proto files
```

Example of expected `json` file:

```json
{
    "exonum": {
        "hostname": "127.0.0.1",
        "public_api_port": 80,
        "ssl": false
    },
    "transactions": [
        {
            "artifact_spec": {
                "name": "cryptocurrency",
                "version": "0.0.1"
            },
            "instance_name": "XNM token",
            "init_data": {
                "field_a": "value_a",
                "field_b": "value_b"
            }
        }
    ]
}
```

## Install

I highly recommend to install this tool in the virtualenv.

```sh
python -m venv launcher
cd launcher
source bin/activate
git clone git@github.com:popzxc/exonum-launcher.git
python3 -m pip install exonum-launcher
```

## License
Apache 2.0 - see [LICENSE](LICENSE) for more information.

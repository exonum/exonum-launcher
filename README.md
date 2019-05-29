# Exonum Dynamic Service Launcher

A tool to send deploy&init transactions into the Exonum blockchain.

## Capabilities

Tool has 3 subcommands: `compile`, `run` and `server`.

The first one compiles `*.proto` files into python.

The second one sends transactions into the blockchain.

The third one launches a site on https://127.0.0.1:5000 with a web interface for deploy&init transaction sender.


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
                                       [-s [SERVICES [SERVICES ...]]] -o
                                       OUTPUT

optional arguments:
  -h, --help            show this help message and exit
  -e EXONUM_SOURCES, --exonum-sources EXONUM_SOURCES
                        A path to exonums sources
  -s [SERVICES [SERVICES ...]], --services [SERVICES [SERVICES ...]]
                        Space-separated sequence of
                        service_name:path_to_service pairs
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

Example of expected `json` file (don't forget to set transaction type!):

```json
{
    "exonum": {
        "hostname": "127.0.0.1",
        "public_api_port": 8000,
        "ssl": false
    },
    "transactions": [
        {
            "type": "deploy",
            "artifact_spec": {
                "name": "cryptocurrency",
                "version": "0.0.1"
            }
        },
        {
            "type": "init",
            "artifact_spec": {
                "name": "cryptocurrency",
                "version": "0.1.0"
            },
            "instance_name": "XNM token",
            "constructor_data": {
                "some_number": 45
            }
        }
    ]
}
```

Usage of the `server` subcommand is equivalent to `run` command. However, if any transactions are listed in the "transactions" section, they won't be sent.

## Warning

As for now, `run` subcommand assumes that service name from `compile` command is equal to the name of the `.proto` file and is equal to the artifact name from the transaction.

For example:

You want to send transaction to initialize `cryptocurrency` artifact. Then make sure that `.proto` file for that service is called `cryptocurrency.proto` and in the `compile` command you write `-s cryptocurrency:some/path`.

Also this `.proto` file should contain `ConstructorData` message.

Otherwise you'll get an error.

## Install

I highly recommend to install this tool in the virtualenv.

```sh
python -m venv launcher
cd launcher
source bin/activate
git clone git@github.com:popzxc/exonum-launcher.git
python3 -m pip install exonum-launcher

python -m exonum-launcher compile -e exonum -s cryptocurrency:exonum/examples/cryptocurrency-advanced/backend/src/proto -o proto

python -m exonum-launcher run -i input.json -p proto
```

## License
Apache 2.0 - see [LICENSE](LICENSE) for more information.

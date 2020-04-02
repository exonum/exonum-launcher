# Exonum Dynamic Service Launcher

**Status:**
[![Travis Build Status](https://travis-ci.org/exonum/exonum-launcher.svg?branch=master)](https://travis-ci.org/exonum/exonum-launcher)

Exonum Dynamic Service Launcher is a tool to manage the lifecycle of the Exonum services.

This tool is capable of deploying artifacts, managing running services, and
changing the configuration of the Exonum blockchain.

## Usage

```sh
usage: exonum_launcher [-h] -i INPUT [-r RUNTIMES [RUNTIMES ...]]
                       [--runtime-parsers RUNTIME_PARSERS [RUNTIME_PARSERS ...]]
                       [--instance-parsers INSTANCE_PARSERS [INSTANCE_PARSERS ...]]

Exonum service launcher

optional arguments:
  -h, --help            show this help message and exit
  -i INPUT, --input INPUT
                        A path to yaml input for service initialization
  -r RUNTIMES [RUNTIMES ...], --runtimes RUNTIMES [RUNTIMES ...]
                        Additional runtimes, e.g. `--runtimes java=1 python=2
                        wasm=3`
  --runtime-parsers RUNTIME_PARSERS [RUNTIME_PARSERS ...]
                        Runtime spec parsers, e.g. `--runtime-parsers
                        python=your_module.YourRuntimeSpecLoader` Values will
                        be imported and treated like SpecLoader, so ensure
                        that module with loader is in `sys.path`.
  --instance-parsers INSTANCE_PARSERS [INSTANCE_PARSERS ...]
                        Instance spec parsers, e.g. `--runtime-parsers
                        python=your_module.YourInstanceSpecLoader` Values will
                        be imported and treated like InstanceSpecLoader, so
                        ensure that module with loader is in `sys.path`.
```

So, if you want to run `exonum-launcher` with Rust runtime only and without custom artifact spec loaders, you can just use:

```sh
python3 -m exonum_launcher -i sample.yml
```

If you want to use `exonum-launcher` with Python runtime and Python runtime spec loader, the command will be:

```sh
python3 -m exonum_launcher --runtimes python=2 --runtime-parsers python=exonum_launcher.runtimes.python.PythonSpecLoader -i sample.yml
```

Example of expected `yaml` file:

```yaml
networks:
  - host: "127.0.0.1"
    ssl: false
    public-api-port: 8080
    private-api-port: 8081

deadline_height: 10000

artifacts:
  cryptocurrency:
    runtime: rust
    name: "exonum-cryptocurrency-advanced:0.1.0"
    action: deploy
  
  # Example of artifact that should not be deployed
  example_artifact:
    runtime: rust
    name: "exonum-cryptocurrency-advanced:0.1.0"
    
instances:
  xnm-token:
    artifact: cryptocurrency
    action: start
    config: []
  nnm-token:
    artifact: "cryptocurrency"
    action: start
    config: []
  some-instance:
    # Since we will not deploy `example_artifact`, it is assumed that it is already deployed
    artifact: "example_artifact"
    action: start
    config:
      val_a: "123"
      val_b: 345
```

`action` field in the `artifacts` section can be one of the following:

- `deploy` - to deploy an artifact.
- `unload` - to unload deployed artifact.
- `none` - to do nothing (default action).

`action` field in the `instances` section can be one of the following:

- `start` - to start a new instance (default action);
- `config` - to change a configuration of existing service (only in `simple` supervisor mode!);
- `stop` - to stop a running service.
- `freeze` - to freeze a running service.
- `resume` - to resume a frozen or stopped service.

**Important:** if you have more than one validator in the network, ensure that connection data
(`networks` section of the config) is specified for **every** validator.

Deploy&init process requires requests to be sent to each validator, so don't expect that transaction broadcast
mechanism will work here.

If supervisor works in the `simple` mode, it's also possible to change consensus config
by providing a `consensus` field in the config, for example:

```yaml
consensus:
    validator_keys:
      - ["1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a",
         "2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b"]
    first_round_timeout: 100
    status_timeout: 100
    peers_timeout: 100
    txs_block_limit: 100
    max_message_len: 100
    min_propose_timeout: 100
    max_propose_timeout: 100
    propose_timeout_threshold: 100
```

## Plugins

You can define custom runtimes and plugins in the config (so you won't have to provide them from command line):

```yaml
runtimes:
  python: 2

plugins:
  runtime:
    python: "exonum_launcher.runtimes.python.PythonSpecLoader"
  artifact: {}
```

See `samples` folder for more examples.

## Install

```sh
pip install exonum-launcher --no-binary=protobuf
```

## License

Apache 2.0 - see [LICENSE](LICENSE) for more information.

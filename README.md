# Exonum Dynamic Service Launcher

**Status:**
[![Travis Build Status](https://travis-ci.org/exonum/exonum-launcher.svg?branch=master)](https://travis-ci.org/exonum/exonum-launcher)

A tool to send deploy&init requests into the Exonum blockchain.

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
    name: "exonum-cryptocurrency-advanced:0.12.0"
  
  # Example of artifact that should not be deployed
  example_artifact:
    runtime: rust
    name: "exonum-cryptocurrency-advanced:0.12.0"
    deploy: false
  
instances:
  xnm-token:
    artifact: cryptocurrency
    config: []
  nnm-token:
    artifact: "cryptocurrency"
    config: []
  some-instance:
    # Since we will not deploy `example_artifact`, it is assumed that it is already deployed
    artifact: "example_artifact"
    config:
      val_a: "123"
      val_b: 345
```

Also you can define custom runtimes and plugins in the config (so you won't have to provide them from command line):

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

#### Requirements

- [Python3](https://www.python.org/downloads/)
- [`exonum-python-client`](https://github.com/exonum/exonum-python-client)

It is highly recommended to install this tool in the virtualenv.

```sh
# Create new virtual environment
python3 -m venv launcher_venv

# Activate it
source launcher_venv/bin/activate

# Install exonum-launcher
git clone git@github.com:exonum/exonum-launcher.git
python3 -m pip install -e exonum-launcher

# Use it
python3 -m exonum_launcher run -i input.yaml
```

## License

Apache 2.0 - see [LICENSE](LICENSE) for more information.

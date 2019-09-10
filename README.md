# Exonum Dynamic Service Launcher

A tool to send deploy&init requests into the Exonum blockchain.

## Usage

```sh
usage: python -m exonum_launcher run [-h] -i INPUT

optional arguments:
  -h, --help            show this help message and exit
  -i INPUT, --input INPUT
                        A path to yaml input for service initialization
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
    name: "exonum-cryptocurrency-advanced/0.11.0"
  
instances:
  xnm-token:
    artifact: cryptocurrency
    config: []
  nnm-token:
    artifact: "cryptocurrency"
    config: []
```

## Install

I highly recommend to install this tool in the virtualenv.

```sh
mkdir launcher
cd launcher
python3 -m venv launcher_venv
source launcher_venv/bin/activate
git clone git@github.com:popzxc/exonum-launcher.git
python3 -m pip install -e exonum-launcher

python3 -m exonum_launcher run -i input.yaml
```

## License
Apache 2.0 - see [LICENSE](LICENSE) for more information.

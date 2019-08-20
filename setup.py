#!/usr/bin/env python
from distutils.core import setup

install_requires = ["protobuf", "pysodium", "requests", "urllib3>=1.24.2", "pyyaml"]

python_requires = ">=3.6"

setup(
    name="exonum_launcher",
    version="0.1",
    description="Exonum Python Service Launcher",
    url="https://github.com/popzxc/exonum-launcher/",
    packages=["exonum_launcher"],
    install_requires=install_requires,
    python_requires=python_requires,
)

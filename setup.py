#!/usr/bin/env python
"""Setup Script for the Exonum Launcher."""
import setuptools

INSTALL_REQUIRES = ["pyyaml", "exonum-python-client==1.0.1"]

PYTHON_REQUIRES = ">=3.6"

with open("README.md", "r") as readme:
    LONG_DESCRIPTION = readme.read()

setuptools.setup(
    name="exonum-launcher",
    version="0.2.0",
    author="The Exonum Team",
    author_email="contact@exonum.com",
    description="Exonum Dynamic Services Launcher",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    url="https://github.com/exonum/exonum-launcher",
    packages=["exonum_launcher", "exonum_launcher.instances", "exonum_launcher.runtimes"],
    install_requires=INSTALL_REQUIRES,
    python_requires=PYTHON_REQUIRES,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Topic :: Security :: Cryptography",
    ],
)

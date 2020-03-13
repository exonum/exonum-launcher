# pylint: disable=missing-docstring, protected-access

import unittest
import os
import copy

from exonum_launcher.configuration import Configuration

_RUNTIMES_START_STATE = copy.deepcopy(Configuration.runtimes())
_DIR_PATH = os.path.dirname(os.path.realpath(__file__))


class TestConfiguration(unittest.TestCase):
    @staticmethod
    def load_config(file_name: str) -> Configuration:
        """Loads Configuration from the sample .yml file"""
        config_path = os.path.join(_DIR_PATH, "test_data", file_name)
        return Configuration.from_yaml(config_path)

    def tearDown(self) -> None:
        # Clean global runtimes state after use.
        runtimes = Configuration.runtimes()
        if runtimes != _RUNTIMES_START_STATE:
            runtimes.clear()
            for key in _RUNTIMES_START_STATE:
                runtimes[key] = _RUNTIMES_START_STATE[key]

    def test_defaults(self) -> None:
        self.assertTrue("rust" in Configuration.runtimes())
        self.assertEqual(Configuration.runtimes()["rust"], 0)

    def test_declare_runtime(self) -> None:
        Configuration.declare_runtime("test", 2)

        runtimes = Configuration.runtimes()
        self.assertTrue("rust" in runtimes)
        self.assertTrue("test" in runtimes)
        self.assertEqual(runtimes["rust"], 0)
        self.assertEqual(runtimes["test"], 2)

    def test_sample_parse(self) -> None:
        config = self.load_config("sample_config.yml")

        self.assertEqual(len(config.networks), 2)
        self.assertEqual(config.networks[0]["host"], "127.0.0.1")
        self.assertEqual(config.networks[1]["host"], "8.8.8.8")

        self.assertTrue("runtime" in config.plugins)
        self.assertTrue("artifact" in config.plugins)
        self.assertEqual(len(config.plugins["runtime"]), 0)
        self.assertEqual(len(config.plugins["artifact"]), 0)

        self.assertEqual(config.supervisor_mode, "decentralized")

        self.assertTrue("cryptocurrency" in config.artifacts)

        cryptocurrency = config.artifacts["cryptocurrency"]
        self.assertEqual(cryptocurrency.name, "exonum-cryptocurrency-advanced")
        self.assertEqual(cryptocurrency.version, "0.12.0")
        self.assertEqual(cryptocurrency.runtime, "rust")
        self.assertEqual(cryptocurrency.runtime_id, 0)
        self.assertEqual(cryptocurrency.deadline_height, 10000)
        self.assertEqual(cryptocurrency.spec, {})
        self.assertEqual(cryptocurrency.deploy, True)

        self.assertTrue("should_not_be_deployed" in config.artifacts)

        should_not_be_deployed = config.artifacts["should_not_be_deployed"]
        self.assertEqual(should_not_be_deployed.deploy, False)

        self.assertEqual(len(config.instances), 2)

        names = ["xnm-token", "nnm-token"]
        for i, name in enumerate(names):
            instance = config.instances[i]
            self.assertEqual(instance.artifact, cryptocurrency)
            self.assertEqual(instance.name, name)
            self.assertIsNone(instance.config)

    def test_parse_runtimes(self) -> None:
        config = self.load_config("custom_runtimes.yml")

        runtimes = config.runtimes()
        expected_layout = {"rust": 0, "example": 2, "other_example": 42}
        self.assertEqual(runtimes, expected_layout)

        self.assertTrue("cryptocurrency" in config.artifacts)
        self.assertTrue("other_cryptocurrency" in config.artifacts)
        self.assertEqual(config.artifacts["cryptocurrency"].runtime, "example")
        self.assertEqual(config.artifacts["cryptocurrency"].runtime_id, 2)
        self.assertEqual(config.artifacts["other_cryptocurrency"].runtime, "other_example")
        self.assertEqual(config.artifacts["other_cryptocurrency"].runtime_id, 42)

    def test_parse_plugins(self) -> None:
        config = self.load_config("custom_plugins.yml")

        expected_layout = {
            "runtime": {"sample": "tests.spec_loaders.TestRuntimeSpecLoader"},
            "artifact": {"cryptocurrency": "tests.spec_loaders.TestInstanceSpecLoader"},
        }

        self.assertEqual(config.plugins, expected_layout)

    def test_parse_plugins_runtime_only(self) -> None:
        config = self.load_config("custom_plugins_runtime_only.yml")

        expected_layout = {
            "runtime": {"sample3": "tests.spec_loaders.TestRuntimeSpecLoader"},
            "artifact": {},
        }

        self.assertEqual(config.plugins, expected_layout)

    def test_parse_consensus(self) -> None:
        config = self.load_config("consensus.yml")

        self.assertIsNotNone(config.consensus)
        self.assertEqual(len(config.consensus["validator_keys"]), 1)
        self.assertEqual(len(config.consensus["validator_keys"][0]), 2)
        self.assertEqual(config.consensus["first_round_timeout"], 100)

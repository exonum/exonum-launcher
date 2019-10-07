# pylint: disable=missing-docstring, protected-access

import unittest
import os

from exonum_launcher.configuration import Configuration


class TestConfiguration(unittest.TestCase):
    def test_parse(self) -> None:
        dir_path = os.path.dirname(os.path.realpath(__file__))
        config_path = os.path.join(dir_path, "sample_config.yml")
        config = Configuration.from_yaml(config_path)

        self.assertEqual(len(config.networks), 2)
        self.assertEqual(config.networks[0]["host"], "127.0.0.1")
        self.assertEqual(config.networks[1]["host"], "8.8.8.8")

        self.assertTrue("cryptocurrency" in config.artifacts)

        cryptocurrency = config.artifacts["cryptocurrency"]
        self.assertEqual(cryptocurrency.name, "exonum-cryptocurrency-advanced:0.12.0")
        self.assertEqual(cryptocurrency.runtime, "rust")
        self.assertEqual(cryptocurrency.runtime_id, 0)
        self.assertEqual(cryptocurrency.deadline_height, 10000)
        self.assertEqual(cryptocurrency.spec, {})

        self.assertEqual(len(config.instances), 2)

        names = ["xnm-token", "nnm-token"]
        for i, name in enumerate(names):
            instance = config.instances[i]
            self.assertEqual(instance.artifact, cryptocurrency)
            self.assertEqual(instance.name, name)
            self.assertEqual(instance.deadline_height, 10000)
            self.assertIsNone(instance.config)

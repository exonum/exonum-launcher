# pylint: disable=missing-docstring, protected-access, no-self-use

import unittest
from unittest.mock import MagicMock, call
from requests import Response

from exonum_launcher.action_result import ActionResult
from exonum_launcher.supervisor import Supervisor
from exonum_launcher.launcher import Launcher
from exonum_launcher.runtimes.rust import RustSpecLoader

from .test_config import TestConfiguration
from .spec_loaders import TestRuntimeSpecLoader, TestInstanceSpecLoader


class MockDefaultInstanceSpecLoader:
    """Mock class that mimics DefaultInstanceSpecLoader in mock method calls."""

    def __eq__(self, other: object) -> bool:
        return type(other).__name__ == "DefaultInstanceSpecLoader"


class TestLauncher(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        # Replace supervisor init with a mock.
        cls._supervisor_init = Supervisor.__init__  # type: ignore
        Supervisor.__init__ = MagicMock(return_value=None)  # type: ignore

    @classmethod
    def tearDownClass(cls) -> None:
        # Restore supervisor original init.
        Supervisor.__init__ = cls._supervisor_init  # type: ignore

    def test_creation(self) -> None:
        """Tests the creation of the launcher"""
        config = TestConfiguration.load_config("sample_config.yml")
        launcher = Launcher(config)

        self.assertEqual(len(launcher.clients), len(config.networks))
        for i, network in enumerate(config.networks):
            self.assertEqual(launcher.clients[i].hostname, network["host"])
            self.assertEqual(launcher.clients[i].public_api_port, network["public-api-port"])
            self.assertEqual(launcher.clients[i].private_api_port, network["private-api-port"])
            schema = "https" if network["ssl"] else "http"
            self.assertEqual(launcher.clients[i].schema, schema)

    def test_initialize(self) -> None:
        """Tests that on initialize launcher initializes Supervisor and verifies clients."""
        config = TestConfiguration.load_config("sample_config.yml")
        launcher = Launcher(config)

        # Create mock OK response.
        response = Response()
        response.status_code = 200

        # Setup mocks.
        launcher._supervisor.initialize = MagicMock(return_value=None)  # type: ignore
        for client in launcher.clients:
            client.stats = MagicMock(return_value=response)

        # Initialize launcher.
        launcher.initialize()

        # Check that expected methods are called
        launcher._supervisor.initialize.assert_called()  # type: ignore
        for client in launcher.clients:
            client.stats.assert_called()

    def test_deinitialize(self) -> None:
        """Tests that deinitialize deinitializes Supervisor."""
        config = TestConfiguration.load_config("sample_config.yml")
        launcher = Launcher(config)

        # Create mock OK response.
        response = Response()
        response.status_code = 200

        # Setup init mocks.
        launcher._supervisor.initialize = MagicMock(return_value=None)  # type: ignore
        for client in launcher.clients:
            client.stats = MagicMock(return_value=response)

        # Initialize launcher.
        launcher.initialize()

        # Setup deinit mock.
        launcher._supervisor.deinitialize = MagicMock(return_value=None)  # type: ignore

        # Deinitialize
        launcher.deinitialize()

        launcher._supervisor.deinitialize.assert_called()  # type: ignore

    def test_context_manager(self) -> None:
        """Tests that creation via `with` calls initialize and deinitialize"""
        config = TestConfiguration.load_config("sample_config.yml")

        old_init = Launcher.initialize
        old_deinit = Launcher.deinitialize

        # Setup mocks.
        Launcher.initialize = MagicMock(return_value=None)  # type: ignore
        Launcher.deinitialize = MagicMock(return_value=None)  # type: ignore

        # Create launcher.
        with Launcher(config) as _:
            pass

        # Check that everything was called.
        # pylint: disable=no-member
        Launcher.initialize.assert_called()  # type: ignore
        Launcher.deinitialize.assert_called()  # type: ignore

        # Restore methods.
        Launcher.initialize = old_init  # type: ignore
        Launcher.deinitialize = old_deinit  # type: ignore

    def test_load_plugins(self) -> None:
        """Tests that plugins are loaded as expected."""
        config = TestConfiguration.load_config("custom_plugins.yml")

        cryptocurrency = config.artifacts["cryptocurrency"]

        launcher = Launcher(config)
        self.assertEqual(type(launcher._runtime_plugins["rust"]), RustSpecLoader)
        self.assertEqual(type(launcher._runtime_plugins["sample"]), TestRuntimeSpecLoader)
        self.assertEqual(type(launcher._artifact_plugins[cryptocurrency]), TestInstanceSpecLoader)

    def test_deploy_all(self) -> None:
        """Tests that deploy method uses supervisor to deploy all artifacts from config."""
        config = TestConfiguration.load_config("sample_config.yml")
        launcher = Launcher(config)

        # Build a list of expected arguements for method calls.
        create_calls_sequence = []
        send_calls_sequence = []
        for artifact in config.artifacts.values():
            create_calls_sequence.append(call(artifact, launcher._runtime_plugins[artifact.runtime]))
            send_calls_sequence.append(call(b"123"))

        # Mock methods.
        launcher._supervisor.create_deploy_request = MagicMock(return_value=b"123")  # type: ignore
        launcher._supervisor.send_deploy_request = MagicMock(return_value=["123"])  # type: ignore

        # Call deploy.
        launcher.deploy_all()

        # Check that methods were invoked with the expected arguments and in the expected order.
        launcher._supervisor.create_deploy_request.assert_has_calls(create_calls_sequence)  # type: ignore
        launcher._supervisor.send_deploy_request.assert_has_calls(send_calls_sequence)  # type: ignore

        # Check that results were added to the pending deployments.
        for artifact in config.artifacts.values():
            self.assertEqual(launcher.launch_state._pending_deployments[artifact], ["123"])

    def test_start_all(self) -> None:
        """Tests that deploy method uses supervisor to deploy all artifacts from config."""
        config = TestConfiguration.load_config("sample_config.yml")
        launcher = Launcher(config)

        # Mark all the artifacts as successfully deployed.
        for artifact in config.artifacts.values():
            launcher.launch_state._completed_deployments[artifact] = ActionResult.Success

        # Build a list of expected arguements for method calls.
        start_calls_sequence = []
        send_calls_sequence = []
        for instance in config.instances:
            spec_loader = launcher._artifact_plugins.get(instance.artifact, MockDefaultInstanceSpecLoader())
            start_calls_sequence.append(call(instance, spec_loader))
            send_calls_sequence.append(call(b"123"))

        # Mock methods.
        launcher._supervisor.create_start_instance_request = MagicMock(return_value=b"123")  # type: ignore
        launcher._supervisor.send_start_instance_request = MagicMock(return_value=["123"])  # type: ignore

        # Call start.
        launcher.start_all()

        # Check that methods were invoked with the expected arguments and in the expected order.
        launcher._supervisor.create_start_instance_request.assert_has_calls(start_calls_sequence)  # type: ignore
        launcher._supervisor.send_start_instance_request.assert_has_calls(send_calls_sequence)  # type: ignore

        # Check that results were added to the pending deployments.
        for instance in config.instances:
            self.assertEqual(launcher.launch_state._pending_initializations[instance], ["123"])

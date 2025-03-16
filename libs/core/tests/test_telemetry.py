"""Tests for the telemetry module."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.telemetry import (
    UniversalTelemetryClient,
    disable_telemetry,
    enable_telemetry,
    get_telemetry_client,
)


@pytest.fixture
def mock_project_root(tmp_path):
    """Create a temporary directory for testing."""
    return tmp_path


@pytest.fixture
def mock_environment():
    """Set up and tear down environment variables for testing."""
    original_env = os.environ.copy()
    os.environ["CUA_TELEMETRY_SAMPLE_RATE"] = "100"

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_disabled_environment():
    """Set up environment variables with telemetry disabled."""
    original_env = os.environ.copy()
    os.environ["CUA_TELEMETRY"] = "off"
    os.environ["CUA_TELEMETRY_SAMPLE_RATE"] = "100"

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


class TestTelemetryClient:
    """Tests for the universal telemetry client."""

    @patch("core.telemetry.telemetry.POSTHOG_AVAILABLE", True)
    @patch("core.telemetry.telemetry.get_posthog_telemetry_client")
    def test_initialization(self, mock_get_posthog, mock_project_root, mock_environment):
        """Test client initialization."""
        mock_client = MagicMock()
        mock_get_posthog.return_value = mock_client

        client = UniversalTelemetryClient(mock_project_root)
        assert client._client is not None
        mock_get_posthog.assert_called_once_with(mock_project_root)

    @patch("core.telemetry.telemetry.POSTHOG_AVAILABLE", True)
    @patch("core.telemetry.telemetry.get_posthog_telemetry_client")
    def test_increment(self, mock_get_posthog, mock_project_root, mock_environment):
        """Test incrementing counters."""
        mock_client = MagicMock()
        mock_get_posthog.return_value = mock_client

        client = UniversalTelemetryClient(mock_project_root)
        client.increment("test_counter", 5)

        mock_client.increment.assert_called_once_with("test_counter", 5)

    @patch("core.telemetry.telemetry.POSTHOG_AVAILABLE", True)
    @patch("core.telemetry.telemetry.get_posthog_telemetry_client")
    def test_record_event(self, mock_get_posthog, mock_project_root, mock_environment):
        """Test recording events."""
        mock_client = MagicMock()
        mock_get_posthog.return_value = mock_client

        client = UniversalTelemetryClient(mock_project_root)
        client.record_event("test_event", {"prop1": "value1"})

        mock_client.record_event.assert_called_once_with("test_event", {"prop1": "value1"})

    @patch("core.telemetry.telemetry.POSTHOG_AVAILABLE", True)
    @patch("core.telemetry.telemetry.get_posthog_telemetry_client")
    def test_flush(self, mock_get_posthog, mock_project_root, mock_environment):
        """Test flushing telemetry data."""
        mock_client = MagicMock()
        mock_client.flush.return_value = True
        mock_get_posthog.return_value = mock_client

        client = UniversalTelemetryClient(mock_project_root)
        result = client.flush()

        assert result is True
        mock_client.flush.assert_called_once()

    @patch("core.telemetry.telemetry.POSTHOG_AVAILABLE", True)
    @patch("core.telemetry.telemetry.get_posthog_telemetry_client")
    def test_enable_disable(self, mock_get_posthog, mock_project_root):
        """Test enabling and disabling telemetry."""
        mock_client = MagicMock()
        mock_get_posthog.return_value = mock_client

        client = UniversalTelemetryClient(mock_project_root)

        client.enable()
        mock_client.enable.assert_called_once()

        client.disable()
        mock_client.disable.assert_called_once()


def test_get_telemetry_client():
    """Test the global client getter."""
    # Reset global state
    from core.telemetry.telemetry import _universal_client

    _universal_client = None

    with patch("core.telemetry.telemetry.UniversalTelemetryClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # First call should create a new client
        client1 = get_telemetry_client()
        assert client1 is mock_client
        mock_client_class.assert_called_once()

        # Second call should return the same client
        client2 = get_telemetry_client()
        assert client2 is client1
        assert mock_client_class.call_count == 1


def test_disable_telemetry():
    """Test the global disable function."""
    # Reset global state
    from core.telemetry.telemetry import _universal_client

    _universal_client = None

    with patch("core.telemetry.telemetry.get_telemetry_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Disable globally
        disable_telemetry()
        mock_client.disable.assert_called_once()


def test_enable_telemetry():
    """Test the global enable function."""
    # Reset global state
    from core.telemetry.telemetry import _universal_client

    _universal_client = None

    with patch("core.telemetry.telemetry.get_telemetry_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Enable globally
        enable_telemetry()
        mock_client.enable.assert_called_once()

"""Tests for the PostHog telemetry client."""

import os
from unittest.mock import MagicMock, patch

import pytest

from core.telemetry.posthog_client import (
    PostHogTelemetryClient,
    TelemetryConfig,
    get_posthog_config,
    get_posthog_telemetry_client,
)


@pytest.fixture
def mock_environment():
    """Set up and tear down environment variables for testing."""
    original_env = os.environ.copy()
    os.environ["CUA_TELEMETRY_SAMPLE_RATE"] = "100"
    # Remove PostHog env vars as they're hardcoded now
    # os.environ["CUA_POSTHOG_API_KEY"] = "test-api-key"
    # os.environ["CUA_POSTHOG_HOST"] = "https://test.posthog.com"

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_disabled_environment():
    """Set up and tear down environment variables with telemetry disabled."""
    original_env = os.environ.copy()
    os.environ["CUA_TELEMETRY"] = "off"
    os.environ["CUA_TELEMETRY_SAMPLE_RATE"] = "100"
    # Remove PostHog env vars as they're hardcoded now
    # os.environ["CUA_POSTHOG_API_KEY"] = "test-api-key"
    # os.environ["CUA_POSTHOG_HOST"] = "https://test.posthog.com"

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


class TestTelemetryConfig:
    """Tests for telemetry configuration."""

    def test_from_env_defaults(self):
        """Test loading config from environment with defaults."""
        # Clear relevant environment variables
        with patch.dict(
            os.environ,
            {
                k: v
                for k, v in os.environ.items()
                if k not in ["CUA_TELEMETRY", "CUA_TELEMETRY_SAMPLE_RATE"]
            },
        ):
            config = TelemetryConfig.from_env()
            assert config.enabled is True  # Default is now enabled
            assert config.sample_rate == 5
            assert config.project_root is None

    def test_from_env_with_vars(self, mock_environment):
        """Test loading config from environment variables."""
        config = TelemetryConfig.from_env()
        assert config.enabled is True
        assert config.sample_rate == 100
        assert config.project_root is None

    def test_from_env_disabled(self, mock_disabled_environment):
        """Test disabling telemetry via environment variable."""
        config = TelemetryConfig.from_env()
        assert config.enabled is False
        assert config.sample_rate == 100
        assert config.project_root is None

    def test_to_dict(self):
        """Test converting config to dictionary."""
        config = TelemetryConfig(enabled=True, sample_rate=50)
        config_dict = config.to_dict()
        assert config_dict == {"enabled": True, "sample_rate": 50}


class TestPostHogConfig:
    """Tests for PostHog configuration."""

    def test_get_posthog_config(self):
        """Test getting PostHog config."""
        config = get_posthog_config()
        assert config is not None
        assert config["api_key"] == "phc_eSkLnbLxsnYFaXksif1ksbrNzYlJShr35miFLDppF14"
        assert config["host"] == "https://eu.i.posthog.com"


class TestPostHogTelemetryClient:
    """Tests for PostHog telemetry client."""

    @patch("posthog.capture")
    @patch("posthog.identify")
    def test_initialization(self, mock_identify, mock_capture, mock_environment):
        """Test client initialization."""
        client = PostHogTelemetryClient()
        assert client.config.enabled is True
        assert client.initialized is True
        mock_identify.assert_called_once()

    @patch("posthog.capture")
    def test_increment_counter(self, mock_capture, mock_environment):
        """Test incrementing a counter."""
        client = PostHogTelemetryClient()
        client.increment("test_counter", 5)
        mock_capture.assert_called_once()
        args, kwargs = mock_capture.call_args
        assert kwargs["event"] == "counter_increment"
        assert kwargs["properties"]["counter_name"] == "test_counter"
        assert kwargs["properties"]["value"] == 5

    @patch("posthog.capture")
    def test_record_event(self, mock_capture, mock_environment):
        """Test recording an event."""
        client = PostHogTelemetryClient()
        client.record_event("test_event", {"param": "value"})
        mock_capture.assert_called_once()
        args, kwargs = mock_capture.call_args
        assert kwargs["event"] == "test_event"
        assert kwargs["properties"]["param"] == "value"

    @patch("posthog.capture")
    def test_disabled_client(self, mock_capture, mock_environment):
        """Test that disabled client doesn't send events."""
        client = PostHogTelemetryClient()
        client.disable()
        client.increment("test_counter")
        client.record_event("test_event")
        mock_capture.assert_not_called()

    @patch("posthog.flush")
    def test_flush(self, mock_flush, mock_environment):
        """Test flushing events."""
        client = PostHogTelemetryClient()
        result = client.flush()
        assert result is True
        mock_flush.assert_called_once()

    def test_global_client(self, mock_environment):
        """Test global client initialization."""
        client1 = get_posthog_telemetry_client()
        client2 = get_posthog_telemetry_client()
        assert client1 is client2  # Same instance

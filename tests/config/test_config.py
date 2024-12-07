import pytest
from unittest.mock import patch, mock_open
from src.config.config import Config
import yaml


@pytest.fixture(autouse=True)
def reset_config():
    """Reset Config singleton between tests"""
    Config._instance = None
    Config._config = None
    yield


@pytest.fixture
def test_config_path(tmp_path):
    """Create a temporary config file"""
    config_data = {
        "data_dir": "./test_data",
        "database": {
            "host": "localhost",
            "port": 5432,
            "name": "r4dar_test_db",
            "user": "r4dar_test",
            "password": "test_password",
        },
        "block_explorers": {
            "etherscan": {"key": "TEST_API_KEY"},
            "basescan": {"key": "TEST_BASESCAN_KEY"},
            "arbiscan": {"key": "TEST_ARBISCAN_KEY"},
            "polygonscan": {"key": "TEST_POLYGONSCAN_KEY"},
            "bscscan": {"key": "TEST_BSCSCAN_KEY"},
        },
        "llm": {"openai": {"key": "test-key", "model": "gpt-4"}},
    }

    config_path = tmp_path / "config.yml"
    with open(config_path, "w") as f:
        yaml.dump(config_data, f)
    return str(config_path)


def test_config_loading(test_config_path):
    with patch.dict("os.environ", {"R4DAR_CONFIG": test_config_path}):
        config = Config()
        assert config.data_dir == "./test_data"
        assert config.database_url == "postgresql://r4dar_test:test_password@localhost:5432/r4dar_test_db"


def test_invalid_config():
    Config._instance = None  # Reset singleton
    Config._config = None

    # Mock an invalid YAML file
    invalid_yaml = "invalid: yaml: content: - ["

    with patch("builtins.open", mock_open(read_data=invalid_yaml)), pytest.raises(ValueError) as exc_info:
        Config().load_config()

    assert "Invalid configuration" in str(exc_info.value)


def test_missing_config():
    Config._instance = None  # Reset singleton
    Config._config = None

    with patch("builtins.open", side_effect=FileNotFoundError()), pytest.raises(ValueError) as exc_info:
        Config().load_config()

    assert "Invalid configuration" in str(exc_info.value)

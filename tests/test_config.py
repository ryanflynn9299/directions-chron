import pytest
from unittest.mock import patch
import os
import yaml
import importlib

@pytest.fixture
def mock_yaml_dict():
    return {
        "default_routes": {
            "start_point": "YAML Point A",
            "end_point": "YAML Point B",
            "collect_return_trip": True
        },
        "schedule": {
            "study_duration_days": 7,
            "peak_interval_minutes": 10
        }
    }

def test_config_loads_defaults(mock_yaml_dict):
    # Clear environment variables
    with patch.dict(os.environ, {}, clear=True):
        with patch('yaml.safe_load', return_value=mock_yaml_dict):
            with patch('src.config.config.load_dotenv'):
                import src.config.config
                importlib.reload(src.config.config)
                
                # Should pull from YAML
                assert src.config.config.START_POINT == "YAML Point A"
                assert src.config.config.END_POINT == "YAML Point B"
                assert src.config.config.COLLECT_RETURN_TRIP is True
                assert src.config.config.STUDY_DURATION_DAYS == 7
            
def test_config_loads_env_overrides(mock_yaml_dict):
    env_overrides = {
        "START_POINT": "ENV Point A",
        "STUDY_DURATION_DAYS": "30",
        "COLLECT_RETURN_TRIP": "false"
    }
    
    with patch.dict(os.environ, env_overrides, clear=True):
        with patch('yaml.safe_load', return_value=mock_yaml_dict):
            with patch('src.config.config.load_dotenv'):
                import src.config.config
                importlib.reload(src.config.config)
                
                # Should pull from ENV overrides
                assert src.config.config.START_POINT == "ENV Point A"
                # Should remain YAML since not overridden
                assert src.config.config.END_POINT == "YAML Point B" 
                assert src.config.config.COLLECT_RETURN_TRIP is False
                assert src.config.config.STUDY_DURATION_DAYS == 30

def test_config_missing_yaml_fallback():
    # If no yaml and no env
    with patch.dict(os.environ, {}, clear=True):
        with patch('builtins.open', side_effect=FileNotFoundError):
            with patch('src.config.config.load_dotenv'):
                import src.config.config
                importlib.reload(src.config.config)
                
                assert src.config.config.START_POINT is None
                assert src.config.config.COLLECT_RETURN_TRIP is False
                assert src.config.config.INTERVAL_MINUTES == 5
            
def test_config_invalid_env_types(mock_yaml_dict):
    env_overrides = {
        "STUDY_DURATION_DAYS": "not_an_int"
    }
    
    with patch.dict(os.environ, env_overrides, clear=True):
        with patch('yaml.safe_load', return_value=mock_yaml_dict):
            with patch('src.config.config.load_dotenv'):
                import src.config.config
                importlib.reload(src.config.config)
                
                # Should fallback to hardcoded defaults on ValueError
                assert src.config.config.STUDY_DURATION_DAYS == 14

"""
Configuration file reader utilities for OPS setup.

This module provides utilities for reading and parsing JSON configuration files
used in TPS/TIS simulations.
"""

import json
from pathlib import Path
from typing import Dict, Any, Union


def read_config(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Read a JSON configuration file.

    Parameters
    ----------
    file_path : str or Path
        Path to the JSON configuration file.

    Returns
    -------
    dict
        Dictionary containing the configuration parameters.

    Raises
    ------
    FileNotFoundError
        If the configuration file does not exist.
    json.JSONDecodeError
        If the file is not valid JSON.
    """
    file_path = Path(file_path)
    with open(file_path, 'r') as file:
        config = json.load(file)
    return config


def print_config(config: Union[Dict, list], prefix: str = '') -> None:
    """
    Pretty print a configuration dictionary in a hierarchical format.

    Parameters
    ----------
    config : dict or list
        Configuration dictionary or list to print.
    prefix : str, optional
        Prefix for indentation (used internally for recursion).
    """
    if isinstance(config, dict):
        for key, value in config.items():
            new_prefix = f"{prefix}{key}: "
            if isinstance(value, (dict, list)):
                print(new_prefix)
                print_config(value, prefix + '    ')
            else:
                print(f"{new_prefix}{value}")
    elif isinstance(config, list):
        for index, item in enumerate(config):
            new_prefix = f"{prefix}[{index}]: "
            if isinstance(item, (dict, list)):
                print(new_prefix)
                print_config(item, prefix + '    ')
            else:
                print(f"{new_prefix}{item}")


def validate_config_keys(config: Dict[str, Any], required_keys: list, 
                         config_name: str = "Configuration") -> None:
    """
    Validate that a configuration contains all required keys.

    Parameters
    ----------
    config : dict
        Configuration dictionary to validate.
    required_keys : list
        List of required key names.
    config_name : str, optional
        Name of the configuration for error messages.

    Raises
    ------
    KeyError
        If any required key is missing.
    """
    missing_keys = [key for key in required_keys if key not in config]
    if missing_keys:
        raise KeyError(
            f"{config_name} is missing required keys: {', '.join(missing_keys)}"
        )

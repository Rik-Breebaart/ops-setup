"""
ops_setup - OpenPathSampling Setup Utilities

A package providing utilities and base classes for setting up TPS/TIS
simulations with OpenPathSampling.
"""

__version__ = "0.1.0"

from .core.config_reader import read_config, print_config, validate_config_keys
from .core.tps_setup import TPSSetupBase
from .core.tis_setup import TISSetupBase

__all__ = [
    'read_config',
    'print_config',
    'validate_config_keys',
    'TPSSetupBase',
    'TISSetupBase',
]

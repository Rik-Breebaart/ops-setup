"""Utility functions for TPS/TIS setup."""

from .argument_parser import (
    create_parser,
    get_tps_parser,
    get_tis_parser,
    COMMON_ARGUMENTS,
    TPS_ARGUMENTS,
    TIS_ARGUMENTS
)

__all__ = [
    'create_parser',
    'get_tps_parser',
    'get_tis_parser',
    'COMMON_ARGUMENTS',
    'TPS_ARGUMENTS',
    'TIS_ARGUMENTS',
]

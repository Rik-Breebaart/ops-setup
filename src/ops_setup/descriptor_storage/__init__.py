"""
Descriptor storage module for OpenPathSampling.

This module provides efficient storage and retrieval of molecular descriptors
computed during TPS, TIS, RETIS and other path sampling simulations.

The main class is `DescriptorStorage`, which provides:
- Hierarchical organization of trajectories
- Efficient numpy array storage
- Context manager support for safe I/O during simulations
- Support for trajectory weighting (for RETIS, etc.)
- Fast access without loading full OPS storage

Examples
--------
>>> from ops_setup.descriptor_storage import DescriptorStorage
>>> 
>>> # Create and add descriptors during simulation
>>> with DescriptorStorage("my_descriptors", mode='w', method_type='TPS') as storage:
...     storage.add_trajectory(
...         set_name='initial_conditions',
...         interface_value=0.5,
...         descriptors={'distance': dist_array, 'angle': angle_array},
...         n_points=100,
...         storage_index=0
...     )
>>> 
>>> # Load and analyze later
>>> storage = DescriptorStorage.load("my_descriptors", mode='r')
>>> print(storage.summary())
>>> distances = storage.get_trajectory_descriptors('initial_conditions', '0.50', 0, 'distance')
"""

from .descriptor_storage import (
    DescriptorStorage,
    TrajectoryInfo,
    InterfaceData,
    SetData,
)

__all__ = [
    'DescriptorStorage',
    'TrajectoryInfo',
    'InterfaceData',
    'SetData',
]

__version__ = '0.1.0'

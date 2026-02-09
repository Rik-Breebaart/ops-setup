#!/usr/bin/env python
"""
Example usage of DescriptorStorage for TPS simulations.

This example demonstrates how to use the DescriptorStorage class to
efficiently store and retrieve trajectory descriptors during and after
TPS simulations.
"""

import numpy as np
from pathlib import Path
import sys

# Add ops-setup to path
sys.path.insert(0, str(Path.home() / "code" / "ops-setup" / "src"))

from ops_setup.descriptor_storage import DescriptorStorage


def example_basic_usage():
    """Basic example of creating and accessing descriptor storage."""
    print("=" * 70)
    print("Example 1: Basic Usage")
    print("=" * 70)
    
    # Create new storage
    storage_path = Path("/tmp/example_descriptors")
    
    with DescriptorStorage(storage_path, mode='w', method_type='TPS') as storage:
        # Add trajectory 1
        storage.add_trajectory(
            set_name='initial_conditions',
            interface_value=0.5,
            descriptors={
                'distance': np.random.rand(100, 1),
                'angle': np.random.rand(100, 1)
            },
            n_points=100,
            storage_index=0
        )
        
        # Add trajectory 2
        storage.add_trajectory(
            set_name='initial_conditions',
            interface_value=0.5,
            descriptors={
                'distance': np.random.rand(120, 1),
                'angle': np.random.rand(120, 1)
            },
            n_points=120,
            storage_index=1
        )
        
        print("\n✓ Added 2 trajectories with descriptors")
    
    # Reload and access
    storage = DescriptorStorage.load(storage_path, mode='r')
    
    dist_traj1 = storage.get_trajectory_descriptors(
        'initial_conditions', '0.50', 0, 'distance'
    )
    print(f"✓ Retrieved trajectory 1 distances: shape {dist_traj1.shape}")
    
    # Get all descriptors at interface
    all_distances = storage.get_interface_descriptors(
        'initial_conditions', '0.50', 'distance'
    )
    print(f"✓ Retrieved all distances at interface: shape {all_distances.shape}")
    
    print("\n" + storage.summary())


def example_with_weights():
    """Example with trajectory weighting (useful for RETIS)."""
    print("\n" + "=" * 70)
    print("Example 2: With Trajectory Weights")
    print("=" * 70)
    
    storage_path = Path("/tmp/example_descriptors_weighted")
    
    with DescriptorStorage(storage_path, mode='w', method_type='RETIS') as storage:
        # Add multiple trajectories
        for i in range(3):
            storage.add_trajectory(
                set_name='shooting_point_ensemble',
                interface_value=0.5,
                descriptors={
                    'cv_value': np.random.rand(100 + i*10, 1),
                },
                n_points=100 + i*10,
                storage_index=i
            )
        
        print(f"✓ Added 3 trajectories")
    
    # Load and add weights
    storage = DescriptorStorage.load(storage_path, mode='a')
    
    weights = np.array([1.0, 2.5, 0.8])  # Different weights for each trajectory
    storage.set_trajectory_weights('shooting_point_ensemble', '0.50', weights)
    
    # Get per-point weights
    point_weights = storage.get_interface_weights('shooting_point_ensemble', '0.50')
    print(f"✓ Set trajectory weights: {weights}")
    print(f"✓ Per-point weights shape: {point_weights.shape}")
    
    storage.flush()
    print(f"\n✓ Saved storage with weights to {storage_path}")


def example_multiple_sets():
    """Example with multiple origin sets and interfaces."""
    print("\n" + "=" * 70)
    print("Example 3: Multiple Sets and Interfaces")
    print("=" * 70)
    
    storage_path = Path("/tmp/example_descriptors_multi")
    
    with DescriptorStorage(storage_path, mode='w', method_type='TIS') as storage:
        # Basin A - multiple interfaces
        for interface in [0.3, 0.5, 0.7]:
            for traj_id in range(2):
                storage.add_trajectory(
                    set_name='basin_A',
                    interface_value=interface,
                    descriptors={
                        'distance': np.random.rand(100, 1),
                    },
                    n_points=100,
                    storage_index=traj_id
                )
        
        # Basin B - multiple interfaces
        for interface in [1.5, 1.7, 1.9]:
            for traj_id in range(2):
                storage.add_trajectory(
                    set_name='basin_B',
                    interface_value=interface,
                    descriptors={
                        'distance': np.random.rand(100, 1),
                    },
                    n_points=100,
                    storage_index=traj_id
                )
        
        print(f"✓ Added trajectories for 2 sets × 3 interfaces")
    
    # Load and explore
    storage = DescriptorStorage.load(storage_path, mode='r')
    print("\n" + storage.summary())
    
    # Access specific trajectory
    desc = storage.get_trajectory_descriptors('basin_A', '0.50', 1, 'distance')
    print(f"\n✓ Basin A, interface 0.50, trajectory 1: shape {desc.shape}")


def example_incremental_writing():
    """Example of incremental writing during simulation."""
    print("\n" + "=" * 70)
    print("Example 4: Incremental Writing (Simulation)")
    print("=" * 70)
    
    storage_path = Path("/tmp/example_descriptors_incremental")
    
    # Simulate adding descriptors during MC steps
    with DescriptorStorage(storage_path, mode='w', method_type='TPS') as storage:
        
        print("Simulating MC steps with periodic descriptor computation...")
        
        for step in range(5):
            # Simulate computing trajectory
            traj_length = 100 + np.random.randint(0, 50)
            
            # Add descriptors
            storage.add_trajectory(
                set_name='tps_ensemble',
                interface_value=0.5,
                descriptors={
                    'cv_value': np.random.rand(traj_length, 1),
                    'forces': np.random.rand(traj_length, 3)
                },
                n_points=traj_length,
                storage_index=step
            )
            
            print(f"  Step {step}: added trajectory with {traj_length} points")
            
            # Flush every other step to demonstrate incremental saving
            if step % 2 == 0:
                storage.flush()
                print(f"    → Flushed to disk")
    
    # Load final result
    storage = DescriptorStorage.load(storage_path, mode='r')
    print(f"\n✓ Final storage contains {len(storage.sets['tps_ensemble'].interfaces['0.50'].trajectories)} trajectories")
    print("\n" + storage.summary())


if __name__ == "__main__":
    example_basic_usage()
    example_with_weights()
    example_multiple_sets()
    example_incremental_writing()
    
    print("\n" + "=" * 70)
    print("All examples completed successfully!")
    print("=" * 70)

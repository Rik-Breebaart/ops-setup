"""
QUICK REFERENCE: DescriptorStorage API

Copy-paste templates for common operations.
"""

# ============================================================================
# INITIALIZATION
# ============================================================================

from pathlib import Path
from ops_setup.descriptor_storage import DescriptorStorage

# Create new storage
storage = DescriptorStorage(
    Path("descriptors"),
    mode='w',
    method_type='TPS'
)

# Load existing
storage = DescriptorStorage.load(Path("descriptors"), mode='r')
storage = DescriptorStorage.load(Path("descriptors"), mode='a')  # append

# Context manager (auto-close)
with DescriptorStorage(Path("descriptors"), mode='w') as storage:
    # operations here
    pass  # auto-flush and close


# ============================================================================
# ADDING DATA
# ============================================================================

import numpy as np

# Add single trajectory
storage.add_trajectory(
    set_name='ensemble',
    interface_value=0.5,
    descriptors={
        'distance': np.random.rand(100, 1),
        'angle': np.random.rand(100, 1)
    },
    n_points=100,
    storage_index=0
)

# Add from computed values
distances = [distance_fn(s) for s in trajectory]
storage.add_trajectory(
    set_name='ensemble',
    interface_value=0.5,
    descriptors={'distance': np.array(distances).reshape(-1, 1)},
    n_points=len(trajectory),
    storage_index=step
)

# Batch add and flush
for i in range(100):
    # compute trajectory...
    storage.add_trajectory(...)
    
    if i % 20 == 0:
        storage.flush()


# ============================================================================
# RETRIEVING DATA
# ============================================================================

# Get single trajectory descriptor
distances = storage.get_trajectory_descriptors(
    set_name='ensemble',
    interface_key='0.50',
    trajectory_idx=0,
    descriptor_name='distance'
)
# Returns: np.array of shape (100, 1)

# Get all trajectories at one interface (concatenated)
all_distances = storage.get_interface_descriptors(
    set_name='ensemble',
    interface_key='0.50',
    descriptor_name='distance'
)
# Returns: np.array of shape (total_frames, 1)

# Get all descriptors in entire set
set_distances = storage.get_set_descriptors(
    set_name='ensemble',
    descriptor_name='distance'
)
# Returns: dict of {interface_key -> np.array}


# ============================================================================
# WEIGHTS (RETIS/Weighted Ensembles)
# ============================================================================

# Set trajectory weights
weights = np.array([1.0, 2.5, 0.8, ...])  # one per trajectory
storage.set_trajectory_weights(
    set_name='ensemble',
    interface_key='0.50',
    weights=weights
)

# Get per-frame weights (expanded to match trajectories)
point_weights = storage.get_interface_weights(
    set_name='ensemble',
    interface_key='0.50'
)
# Returns: np.array of shape (total_frames,) with weights repeated


# ============================================================================
# I/O MANAGEMENT
# ============================================================================

# Flush accumulators to disk
storage.flush()

# Save with compression
storage.save(use_compression=True)

# Close storage
storage.close()

# Get status
print(storage.summary())

# List all sets
for set_name in storage.sets.keys():
    print(f"Set: {set_name}")

# List interfaces in set
for interface_key in storage.sets['ensemble'].interfaces.keys():
    print(f"Interface: {interface_key}")

# Count trajectories at interface
n_trajs = len(storage.sets['ensemble'].interfaces['0.50'].trajectories)


# ============================================================================
# ITERATION PATTERNS
# ============================================================================

# Iterate over all trajectories at interface
interface = storage.sets['ensemble'].interfaces['0.50']
for traj_idx, traj_info in enumerate(interface.trajectories):
    n_points = traj_info.n_points
    print(f"Trajectory {traj_idx}: {n_points} frames")

# Iterate over all interfaces in set
set_data = storage.sets['ensemble']
for interface_key, interface_data in set_data.interfaces.items():
    print(f"Interface {interface_key}: {len(interface_data.trajectories)} trajectories")

# Iterate over all sets
for set_name, set_data in storage.sets.items():
    print(f"Set {set_name}")
    for interface_key, interface_data in set_data.interfaces.items():
        print(f"  Interface {interface_key}")


# ============================================================================
# COMMON WORKFLOWS
# ============================================================================

# Workflow 1: During simulation
# ----------

with DescriptorStorage(Path("descriptors"), mode='w', method_type='TPS') as storage:
    for step in range(10000):
        # run MC move
        trajectory = pathsampler.get_last_trajectory()
        
        # compute descriptors
        distances = np.array([dist_cv(s) for s in trajectory])
        
        # store
        storage.add_trajectory(
            set_name='tps_ensemble',
            interface_value=0.5,
            descriptors={'distance': distances.reshape(-1, 1)},
            n_points=len(trajectory),
            storage_index=step
        )
        
        # periodic flush
        if step % 50 == 0:
            storage.flush()


# Workflow 2: Post-simulation analysis
# -----------

storage = DescriptorStorage.load(Path("descriptors"), mode='r')

# Get all data at interface
all_dists = storage.get_interface_descriptors('tps_ensemble', '0.50', 'distance')

# Statistics
mean = np.mean(all_dists)
std = np.std(all_dists)
hist, bins = np.histogram(all_dists, bins=50)

# Plot
import matplotlib.pyplot as plt
plt.hist(all_dists, bins=50)
plt.xlabel('Distance')
plt.ylabel('Count')
plt.savefig('distance_histogram.pdf')


# Workflow 3: RETIS with weights
# -----------

storage = DescriptorStorage.load(Path("descriptors"), mode='a')

# Compute weights (e.g., from committor analysis)
n_trajs = len(storage.sets['ensemble'].interfaces['0.50'].trajectories)
weights = np.random.rand(n_trajs)

# Store
storage.set_trajectory_weights('ensemble', '0.50', weights)

# Use for analysis
point_weights = storage.get_interface_weights('ensemble', '0.50')
weighted_dists = storage.get_interface_descriptors('ensemble', '0.50', 'distance')
weighted_mean = np.sum(weighted_dists.flatten() * point_weights) / np.sum(point_weights)


# Workflow 4: Multiple descriptors
# -----------

with DescriptorStorage(Path("descriptors"), mode='w') as storage:
    for step in range(100):
        trajectory = ...
        
        storage.add_trajectory(
            set_name='ensemble',
            interface_value=0.5,
            descriptors={
                'distance': np.array([dist_cv(s) for s in trajectory]).reshape(-1, 1),
                'angle': np.array([angle_cv(s) for s in trajectory]).reshape(-1, 1),
                'force': np.array([force_cv(s) for s in trajectory]).reshape(-1, 3),
            },
            n_points=len(trajectory),
            storage_index=step
        )
        
        if step % 10 == 0:
            storage.flush()

# Access multi-dimensional
forces = storage.get_interface_descriptors('ensemble', '0.50', 'force')
# shape: (total_frames, 3)


# ============================================================================
# ERROR HANDLING
# ============================================================================

try:
    # Try to read
    storage = DescriptorStorage.load(path, mode='r')
except FileNotFoundError:
    print("Storage file not found")
    # Create new
    storage = DescriptorStorage(path, mode='w')

# Validate data shape
descriptors = np.random.rand(100)  # Wrong: 1D
# Should be:
descriptors = descriptors.reshape(-1, 1)  # Correct: 2D (frames, features)

# Ensure interface_key matches actual storage
available_keys = list(storage.sets['ensemble'].interfaces.keys())
assert '0.50' in available_keys, f"Available: {available_keys}"


# ============================================================================
# TIPS & TRICKS
# ============================================================================

# Tip 1: Use interface_value as string key
interface_value = 0.5
interface_key = f"{interface_value:.2f}"  # Use consistently

# Tip 2: Batch operations for speed
# DON'T:
for trajectory in trajectories:
    storage.add_trajectory(...)
    storage.flush()  # Too slow!

# DO:
for trajectory in trajectories:
    storage.add_trajectory(...)
    if (i+1) % 20 == 0:
        storage.flush()  # Flush in batches

# Tip 3: Check storage status
print(storage.summary())
print(f"Sets: {list(storage.sets.keys())}")
print(f"Interfaces: {list(storage.sets['ensemble'].interfaces.keys())}")

# Tip 4: Memory efficiency for large data
# Use compression:
storage = DescriptorStorage(path, mode='w', use_compression=True)

# Load in read mode (doesn't load all data):
storage = DescriptorStorage.load(path, mode='r')

# Tip 5: Organize by method
storage = DescriptorStorage(path, method_type='RETIS')  # Metadata includes method

# Tip 6: Multiple storage objects for different purposes
with DescriptorStorage(..., method_type='TPS') as tps_storage:
    # Fast TPS descriptor storage
    pass

# Later, load for analysis
storage = DescriptorStorage.load(..., mode='r')
print(f"Method: {storage.method_type}")


# ============================================================================
# DEBUGGING
# ============================================================================

# Check internal structure
storage = DescriptorStorage.load(path, mode='r')

# Print all data
for set_name, set_data in storage.sets.items():
    print(f"\nSet: {set_name}")
    for interface_key, interface_data in set_data.interfaces.items():
        print(f"  Interface: {interface_key}")
        print(f"    Trajectories: {len(interface_data.trajectories)}")
        for idx, traj_info in enumerate(interface_data.trajectories):
            print(f"      [{idx}] {traj_info.n_points} frames")

# Check available descriptors
first_interface = storage.sets['ensemble'].interfaces['0.50']
available_descriptors = list(first_interface.descriptors.keys())
print(f"Available descriptors: {available_descriptors}")

# Check descriptor shapes
for desc_name in available_descriptors:
    desc = storage.get_trajectory_descriptors('ensemble', '0.50', 0, desc_name)
    print(f"{desc_name}: shape {desc.shape}")

# Validate consistency
for set_name in storage.sets:
    for interface_key in storage.sets[set_name].interfaces:
        try:
            all_desc = storage.get_interface_descriptors(set_name, interface_key, 'distance')
            print(f"✓ {set_name} / {interface_key}: {all_desc.shape}")
        except Exception as e:
            print(f"✗ {set_name} / {interface_key}: {e}")

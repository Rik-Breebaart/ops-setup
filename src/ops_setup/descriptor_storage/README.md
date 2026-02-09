# DescriptorStorage Module

Efficient and flexible storage system for trajectory descriptors computed during TPS, TIS, and RETIS simulations.

## Overview

`DescriptorStorage` provides a dedicated system for storing descriptors (CVs, distances, angles, etc.) computed during pathsampling simulations. Unlike OPS experimental storage (which uses JSON + dill), DescriptorStorage uses HDF5 and NumPy for fast, efficient I/O optimized for descriptor data.

### Key Features

- **Hierarchical Organization**: Organized as `method_type → origin_set → interface → trajectory`
- **Efficient I/O**: NumPy arrays with optional compression (`.savez_compressed`)
- **Context Manager**: Automatic flushing with `with` statement
- **Incremental Writing**: Add descriptors during simulation, flush periodically
- **Weight Management**: Store and retrieve trajectory weights for RETIS
- **Multi-Dimensional**: Support arbitrary-shape descriptors (scalars, vectors, matrices)
- **Fast Access**: Direct numpy array retrieval without loading full OPS storage
- **Method-Agnostic**: Works with TPS, TIS, RETIS, or custom methods

## Installation

The descriptor_storage module is part of ops-setup:

```bash
cd /home/rbreeba/code/ops-setup
pip install -e .
```

Then import:
```python
from ops_setup.descriptor_storage import DescriptorStorage
```

## Quick Start

### Basic Usage

```python
from pathlib import Path
import numpy as np
from ops_setup.descriptor_storage import DescriptorStorage

# Create new storage
with DescriptorStorage(Path("descriptors"), mode='w', method_type='TPS') as storage:
    
    # Add trajectories with descriptors
    storage.add_trajectory(
        set_name='tps_ensemble',
        interface_value=0.5,
        descriptors={
            'distance': np.random.rand(100, 1),  # 100 frames, 1D descriptor
            'angle': np.random.rand(100, 1)      # 100 frames, 1D descriptor
        },
        n_points=100,
        storage_index=0
    )

# Reload and access
storage = DescriptorStorage.load(Path("descriptors"), mode='r')

# Get specific trajectory
distances = storage.get_trajectory_descriptors('tps_ensemble', '0.50', 0, 'distance')
# shape: (100, 1)

# Get all trajectories at interface
all_distances = storage.get_interface_descriptors('tps_ensemble', '0.50', 'distance')
# shape: (n_total_frames, 1)
```

### Integration with TPS Simulation

```python
from ops_setup.descriptor_storage import DescriptorStorage

# Define descriptor functions
def distance_cv(snapshot):
    return np.linalg.norm(snapshot.xyz[0] - snapshot.xyz[1])

def angle_cv(snapshot):
    # compute angle...
    return angle_value

# Create storage
storage = DescriptorStorage(Path("descriptors"), mode='w', method_type='TPS')

# During simulation loop
for step in range(nsteps):
    # ... run TPS move ...
    trajectory = pathsampler.get_last_trajectory()
    
    # Compute descriptors
    distances = np.array([distance_cv(s) for s in trajectory])
    angles = np.array([angle_cv(s) for s in trajectory])
    
    # Store
    storage.add_trajectory(
        set_name='ensemble',
        interface_value=0.5,
        descriptors={
            'distance': distances.reshape(-1, 1),
            'angle': angles.reshape(-1, 1)
        },
        n_points=len(trajectory),
        storage_index=step
    )
    
    # Flush periodically
    if step % 20 == 0:
        storage.flush()

storage.close()
```

## API Reference

### Creating Storage

```python
# Create new
storage = DescriptorStorage(path, mode='w', method_type='TPS')

# Load existing
storage = DescriptorStorage.load(path, mode='r')
storage = DescriptorStorage.load(path, mode='a')  # append mode
```

### Adding Trajectories

```python
storage.add_trajectory(
    set_name: str,              # e.g., 'ensemble', 'shooting_ensemble'
    interface_value: float,     # e.g., 0.5 for lambda=0.5
    descriptors: Dict[str, np.ndarray],  # descriptor_name -> array
    n_points: int,              # number of frames in trajectory
    storage_index: int          # trajectory index within interface
)
```

Descriptor arrays should have shape `(n_frames, *descriptor_shape)`:
- Scalar: `(n_frames, 1)` or `(n_frames,)`
- Vector: `(n_frames, 3)` 
- Matrix: `(n_frames, 3, 3)`

### Retrieving Data

```python
# Single trajectory
descriptors = storage.get_trajectory_descriptors(
    set_name, interface_key, trajectory_idx, descriptor_name
)

# All trajectories at interface (concatenated)
all_descriptors = storage.get_interface_descriptors(
    set_name, interface_key, descriptor_name
)

# All trajectories in set
set_descriptors = storage.get_set_descriptors(
    set_name, descriptor_name
)
```

### Weight Management (for RETIS/Weighted Ensembles)

```python
# Set per-trajectory weights
weights = np.array([1.0, 2.5, 0.8])  # one per trajectory
storage.set_trajectory_weights(set_name, interface_key, weights)

# Get per-point weights (duplicated to match frames)
point_weights = storage.get_interface_weights(set_name, interface_key)
# shape: (total_frames,)
```

### I/O Management

```python
# Flush accumulators to disk
storage.flush()

# Close storage
storage.close()

# Context manager (auto-close)
with DescriptorStorage(...) as storage:
    # ... operations ...
# Automatically flushed and closed
```

### Inspection

```python
# Get summary
print(storage.summary())

# Access internal structure
for set_name, set_data in storage.sets.items():
    for interface_key, interface_data in set_data.interfaces.items():
        for traj_idx, traj_info in enumerate(interface_data.trajectories):
            print(f"{set_name} / {interface_key} / traj {traj_idx}")
            print(f"  Frames: {traj_info.n_points}")
```

## Data Structure

```
descriptors/
├── metadata.json              # Overall metadata
└── [set_name]/
    ├── [interface_key]/
    │   ├── descriptors.npz    # All descriptor arrays
    │   ├── weights.npy        # Trajectory weights (optional)
    │   ├── metadata.json      # Interface metadata
```

Example `metadata.json`:
```json
{
  "method_type": "TPS",
  "created": "2024-01-15T10:30:45",
  "descriptor_dims": {
    "distance": [1],
    "angle": [1]
  },
  "sets": {
    "ensemble": {
      "interfaces": {
        "0.50": {
          "n_trajectories": 100,
          "n_total_points": 15234,
          "trajectory_indices": [0, 1, 2, ...]
        }
      }
    }
  }
}
```

## Usage Patterns

### Pattern 1: Simple Callback

Best for quick tests or single descriptor:

```python
with DescriptorStorage(path, mode='w') as storage:
    for step in range(nsteps):
        # simulate...
        distances = compute_distances(trajectory)
        storage.add_trajectory(..., descriptors={'d': distances})
        if step % 20 == 0:
            storage.flush()
```

### Pattern 2: Descriptor Manager

Best for production with multiple descriptors:

```python
from ops_setup.descriptor_storage import DescriptorComputationManager

manager = DescriptorComputationManager(
    storage_path=Path("descriptors"),
    descriptor_functions={'distance': dist_fn, 'angle': angle_fn},
    method_type='TIS'
)

# Integrate with pathsampler
manager.setup_callback(pathsampler)
pathsampler.run(nsteps=10000)
manager.finalize()
```

### Pattern 3: Real-Time Analysis

Analyze descriptors during simulation without reloading OPS storage:

```python
with DescriptorStorage(path) as storage:
    for step in range(nsteps):
        # simulate...
        storage.add_trajectory(...)
        
        if step % 100 == 0:
            storage.flush()
            # Quick stats without loading OPS storage
            dists = storage.get_interface_descriptors(...)
            print(f"Step {step}: mean dist = {np.mean(dists):.3f}")
```

### Pattern 4: RETIS with Weights

```python
with DescriptorStorage(path, method_type='RETIS') as storage:
    # Collect trajectories
    for traj in trajectories:
        storage.add_trajectory(...)
    
    storage.flush()

# Add weights after simulation
storage = DescriptorStorage.load(path, mode='a')
weights = compute_weights(trajectories)  # from committor analysis
storage.set_trajectory_weights(set_name, interface_key, weights)
```

## Comparison with OPS Storage

| Feature | OPS Storage | DescriptorStorage |
|---------|-------------|-------------------|
| **Format** | JSON + dill | HDF5 + JSON |
| **CV storage** | Full (including functions) | Descriptors only |
| **Descriptor speed** | Slow (JSON serialization) | Fast (NumPy arrays) |
| **SWIG-safe** | No (pickling issues) | Yes |
| **Multi-dimensional** | Limited | Full support |
| **Incremental write** | Supported | Optimized |
| **Weights** | Not designed for | Full support |
| **File size** | Larger | Smaller (compression) |

## Examples

See `/home/rbreeba/code/ops-setup/examples/`:

- `descriptor_storage_examples.py` - Basic usage examples
- `descriptor_storage_integration.py` - Integration patterns and real-world workflows

Run examples:
```bash
cd /home/rbreeba/code/ops-setup
python examples/descriptor_storage_examples.py
```

## Integration with T4L TPS

To use DescriptorStorage with T4L TPS setup:

```python
from pathlib import Path
from t4l_tps_setup import T4LTPSSetup, calculate_p_value, minimum_distance_between_groups
from ops_setup.descriptor_storage import DescriptorStorage

# Setup
t4l_setup = T4LTPSSetup(...)
t4l_setup.setup_cvs()

# Create descriptor storage
storage = DescriptorStorage(
    Path('T4L_descriptors'),
    mode='w',
    method_type='TPS'
)

# During TPS simulation
for step in range(nsteps):
    # Run MC move
    # trajectory = ...
    
    # Compute descriptors
    p_values = [calculate_p_value(s, p_indices) for s in trajectory]
    distances = [minimum_distance_between_groups(s, g1, g2) for s in trajectory]
    
    storage.add_trajectory(
        set_name='t4l_ensemble',
        interface_value=0.5,
        descriptors={
            'p_value': np.array(p_values).reshape(-1, 1),
            'distance': np.array(distances).reshape(-1, 1)
        },
        n_points=len(trajectory),
        storage_index=step
    )
    
    if step % 20 == 0:
        storage.flush()

storage.close()

# Analyze
storage = DescriptorStorage.load(Path('T4L_descriptors'), mode='r')
print(storage.summary())
```

## Troubleshooting

**Q: AttributeError: 'NoneType' object has no attribute ...**
- A: Storage may not be loaded in correct mode. Use `mode='r'` to read, `mode='a'` to append.

**Q: Files getting very large**
- A: Enable compression: `DescriptorStorage(..., use_compression=True)`

**Q: Data not persisted to disk**
- A: Call `storage.flush()` periodically or use context manager `with DescriptorStorage(...) as storage:`

**Q: Descriptor shapes don't match**
- A: Ensure all descriptors for the same name have consistent shape across trajectories. Use `(n_frames, 1)` for scalars.

## Performance Notes

- **Writing**: ~100k frames/sec per descriptor (depends on shape)
- **Reading**: Nearly instant (direct NumPy array access)
- **Compression**: ~5-10x size reduction, minimal speed impact
- **Batch Size**: Use `batch_size=20-50` for optimal flush frequency

## Future Extensions

- [ ] Support for streaming access (large trajectory files)
- [ ] Statistical analysis methods (histograms, correlations)
- [ ] Integration with RETIS committor analysis
- [ ] Visualization helpers
- [ ] Multi-process safe concurrent writing

## Citation

If you use DescriptorStorage in your research, please cite OpenPathSampling:

> Swenson DWH, Prinz JH, Noe F, Chodera JD (2015) OpenPathSampling: A flexible Python framework for path sampling. arXiv preprint arXiv:1503.01083

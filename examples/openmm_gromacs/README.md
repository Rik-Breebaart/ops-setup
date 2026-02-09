# OpenMM from GROMACS - Complete Documentation

## Overview

The `openmm_from_gromacs` module provides a bridge between GROMACS files and OpenPathSampling (OPS) for transition path sampling (TPS) simulations. It enables seamless integration of:

1. **GROMACS topology and coordinate files** → OpenMM system setup
2. **OpenMM MD simulations** → OPS engines for path sampling
3. **Custom CVs and states** → TPS networks

## Core Classes

### 1. `OpenMMGromacs` - Low-level OpenMM Setup

Basic class for setting up OpenMM simulations from GROMACS files.

**Use when:** You just want to run MD from GROMACS files with OpenMM.

```python
from ops_setup.engines import OpenMMGromacs

openmm = OpenMMGromacs(
    topology_file='system.top',
    structure_file='system.gro',
    forcefield_dir='amber99sb-ildn.ff/',
    config={
        'temperature': 300.0,
        'pressure': 1.0,
        'timestep': 0.002,
        'friction': 1.0,
        'platform': 'CUDA',
        'precision': 'mixed',
    }
)

# Minimize and warm up
openmm.minimize_energy()
openmm.warmup_nvt(n_steps=1000)

# Add reporters
openmm.add_reporter('StateData', 'output/energy.csv', interval=2500)
openmm.add_reporter('DCD', 'output/traj.dcd', interval=2500)

# Run simulation
openmm.run(n_steps=250000)  # 500 ps with dt=0.002 ps
```

**Configuration options:**
```python
config = {
    'temperature': 300.0,          # K
    'pressure': 1.0,               # bar
    'timestep': 0.002,             # ps
    'friction': 1.0,               # ps^-1
    'barostat_frequency': 25,      # steps
    'nonbondedCutoff': 1.1,        # nm
    'constraints': 'HBonds',       # HBonds, AllBonds, None
    'ewaldErrorTolerance': 1e-5,   # Ewald summation
    'platform': 'CUDA',            # CUDA, CPU, OpenCL
    'precision': 'mixed',          # mixed, double, single
}
```

### 2. `OpenMMGromacsTPS` - OPS-Ready Setup

Extends `OpenMMGromacs` to create an OpenPathSampling engine and define states.

**Use when:** You want to set up path sampling simulations with OPS.

```python
from ops_setup.engines import OpenMMGromacsTPS

# Define collective variables and state bounds
state_definitions = {
    'stateA': {
        'cvs': [cv1, cv2],                    # List of CVs
        'bounds': [(min1, max1), (min2, max2)]  # CV bounds
    },
    'stateB': {
        'cvs': [cv1, cv2],
        'bounds': [(min1_b, max1_b), (min2_b, max2_b)]
    }
}

tps_setup = OpenMMGromacsTPS(
    topology_file='system.top',
    structure_file='system.gro',
    forcefield_dir='ff/',
    state_definitions=state_definitions,
    n_frames_max=5000,
    n_steps_per_frame=500
)

# Access OPS components
engine = tps_setup.engine           # OPS engine
template = tps_setup.template       # Template snapshot
states = tps_setup.states           # (stateA, stateB) volumes

# Create TPS network
network = tps_setup.create_tps_network()
```

### 3. `GromacsCVFactory` - Collective Variable Factory

Convenience methods for creating common collective variables.

```python
from ops_setup.engines import GromacsCVFactory

factory = GromacsCVFactory(topology)

# Distance between two atoms
dist_cv = factory.distance_cv('dist_10_200', atom_indices=(10, 200))

# Position along axis
pos_cv = factory.position_cv('z_position_50', atom_index=50, axis='z')

# Minimum distance between atom groups
min_dist_cv = factory.minimum_distance_cv(
    'mouth_distance',
    group1=(5, 10, 15),
    group2=(195, 200, 205)
)

# Custom CV from function
def my_cv_func(frame, arg):
    # ... custom calculation ...
    return value

custom_cv = factory.custom_cv('my_cv', my_cv_func, arg=...)
```

## Collective Variables

### Factory Methods

#### `distance_cv(name, atom_indices)`
Distance between two atoms.

```python
cv = factory.distance_cv('distance', atom_indices=(10, 200))
```

#### `position_cv(name, atom_index, axis)`
Position along x/y/z axis.

```python
cv = factory.position_cv('z_pos', atom_index=50, axis='z')
```

#### `minimum_distance_cv(name, group1, group2)`
Minimum distance between two atom groups.

```python
cv = factory.minimum_distance_cv(
    'contact_distance',
    group1=(5, 10, 15),
    group2=(195, 200, 205)
)
```

#### `custom_cv(name, function, arg)`
Custom CV from user-defined function.

```python
def radius_of_gyration(frame, arg):
    xyz = frame.xyz
    com = xyz.mean(axis=0)
    rg_sq = ((xyz - com)**2).sum(axis=1).mean()
    return rg_sq**0.5

rg_cv = factory.custom_cv('rg', radius_of_gyration)
```

### Manual CV Definition

For more complex CVs, define them directly:

```python
import openpathsampling as paths

def proj_calc(frame, arg):
    """Custom projection calculation."""
    xyz = frame.xyz
    atom1_pos = xyz[arg[0]]
    atom2_pos = xyz[arg[1]]
    # ... calculation ...
    return projection

proj_cv = paths.FunctionCV(
    'projection',
    proj_calc,
    topology,
    arg=(atom_i, atom_j)
)
```

## Complete T4L Example

```python
from ops_setup.engines import (
    OpenMMGromacs,
    OpenMMGromacsTPS,
    GromacsCVFactory
)
import openpathsampling as paths

# ============ Step 1: Define CVs ============

# Load topology first
openmm_temp = OpenMMGromacs(
    'topology.top',
    'structure.gro',
    'ff/',
)

factory = GromacsCVFactory(openmm_temp.topology)

# P-value projection (custom)
def p_value_calc(frame, arg):
    boxsize = frame.box_vectors.diagonal()
    xyz = frame.xyz
    diff = boxsize / 2 - xyz[arg[1]]
    atoms = ([xyz[at] for at in arg] + diff) % boxsize
    com4 = sum(atoms[2:]) / 6
    d6067 = atoms[0] - atoms[1]
    d6704 = atoms[1] - com4
    p = sum(d6067 * d6704) / sum(d6067 ** 2)
    return p

p_cv = factory.custom_cv(
    'P_value',
    p_value_calc,
    arg=(942, 1057, 59, 60, 62, 64, 66, 68)
)

# Mouth distance (minimum distance)
mouth_cv = factory.minimum_distance_cv(
    'Mouth_distance',
    group1=(385, 386, 370, 373),
    group2=(2171, 2174, 2177, 2253)
)

# ============ Step 2: Define States ============

state_definitions = {
    'stateA': {  # Open state
        'cvs': [p_cv, mouth_cv],
        'bounds': [(-0.65, -0.55), (1.5, 2.0)]
    },
    'stateB': {  # Closed state
        'cvs': [p_cv, mouth_cv],
        'bounds': [(0.35, 0.6), (0.15, 0.3)]
    }
}

# ============ Step 3: Create TPS Setup ============

tps_setup = OpenMMGromacsTPS(
    'topology.top',
    'structure.gro',
    'ff/',
    state_definitions=state_definitions,
    n_frames_max=5000,
    n_steps_per_frame=500
)

# ============ Step 4: Run TPS ============

network = tps_setup.create_tps_network()

# Create initial trajectory (you need to provide this)
trajectory = paths.tools.ops_load_trajectory('initial.trr', top='structure.gro')

# Create move scheme
scheme = paths.OneWayShootingMoveScheme(network, tps_setup.engine)

# Run sampling
sampler = paths.PathSampling(
    storage=paths.Storage('tps_results.nc', 'w', tps_setup.template),
    move_scheme=scheme,
    sample_set=network.sampling_set(trajectory)
)

sampler.run(n_samples=10000)
```

## State Definition

States must be defined as intersections of collective variable constraints.

### Single CV
```python
state_definitions = {
    'stateA': {
        'cvs': [cv1],
        'bounds': [(min1, max1)]
    },
    'stateB': {
        'cvs': [cv1],
        'bounds': [(min1_b, max1_b)]
    }
}
```

### Multiple CVs (Intersection)
```python
state_definitions = {
    'stateA': {
        'cvs': [cv1, cv2, cv3],
        'bounds': [(min1, max1), (min2, max2), (min3, max3)]
    },
    'stateB': {
        'cvs': [cv1, cv2, cv3],
        'bounds': [(min1_b, max1_b), (min2_b, max2_b), (min3_b, max3_b)]
    }
}
```

The state is defined as: $\text{state} = (cv_1 \in [a_1, b_1]) \cap (cv_2 \in [a_2, b_2]) \cap \ldots$

## Configuration Options

### Temperature & Pressure
```python
config = {
    'temperature': 300.0,      # Kelvin
    'pressure': 1.0,           # bar (if using barostat)
}
```

### Integration
```python
config = {
    'timestep': 0.002,         # picoseconds
    'friction': 1.0,           # ps^-1 (Langevin friction)
    'barostat_frequency': 25,  # MC barostat update frequency
}
```

### Force Field & System
```python
config = {
    'constraints': 'HBonds',        # HBonds, AllBonds, None
    'ewaldErrorTolerance': 1e-5,   # Ewald summation tolerance
    'nonbondedCutoff': 1.1,        # nm
}
```

### Platform
```python
config = {
    'platform': 'CUDA',        # CUDA, CPU, OpenCL
    'precision': 'mixed',      # mixed, double, single
}
```

## Advanced Usage

### Custom Integrator
The current implementation uses VVVR integrator. To use a different integrator, subclass `OpenMMGromacs`:

```python
class MyOpenMMGromacs(OpenMMGromacs):
    def _setup_integrator(self):
        # Your custom integrator setup
        return my_integrator
```

### Energy Minimization
```python
openmm.minimize_energy(tolerance=10*unit.kilojoules/unit.mole)
```

### Multiple Reporters
```python
openmm.add_reporter('StateData', 'energy.csv', interval=2500, 
                   volume=True, density=True)
openmm.add_reporter('DCD', 'trajectory.dcd', interval=2500)
openmm.add_reporter('NetCDF', 'trajectory.nc', interval=2500)
openmm.add_reporter('PDB', 'final.pdb', interval=500000)
```

## Common Issues

### "No topology found"
Ensure GROMACS files are valid and paths are correct.

### "System has missing bonds"
Check GROMACS forcefield directory (`includeDir` parameter) - ensure all .itp files are present.

### "Memory errors on GPU"
- Reduce `n_frames_max` in `OpenMMGromacsTPS`
- Use `precision='single'` instead of `'mixed'`
- Reduce system size

### "CV values are NaN"
- Check atom indices in CV definition
- Ensure frame has valid coordinates
- Add error checking in custom CV functions

## File Locations in Project

- **Class definitions**: `/home/rbreeba/code/ops-setup/src/ops_setup/engines/openmm_from_gromacs.py`
- **T4L example**: `/home/rbreeba/Projects/T4L/examples/t4l_tps_setup.py`
- **General examples**: `/home/rbreeba/Projects/T4L/examples/openmm_gromacs_examples.py`
- **Documentation**: `/home/rbreeba/Projects/T4L/docs/openmm_gromacs_guide.md`

## References

- OpenPathSampling: https://github.com/openpathsampling/openpathsampling
- OpenMM: https://openmm.org/
- GROMACS: https://www.gromacs.org/


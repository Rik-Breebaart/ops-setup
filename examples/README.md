# OPS-Setup Examples

This directory contains examples demonstrating how to use the ops-setup package for Transition Path Sampling (TPS) and Transition Interface Sampling (TIS) simulations **without AIMMD components**.

These examples use simple toy potentials to demonstrate the core functionality of ops-setup, making it easy to understand the basic workflow before moving to more complex molecular systems.

## Structure

```
examples/
├── notebooks/          # Jupyter notebooks with detailed examples
│   ├── 01_basic_tps_toy_system.ipynb      # TPS with toy potentials
│   ├── 02_basic_tis_toy_system.ipynb      # TIS with toy potentials
│   └── README_notebooks.md                 # Notebook guides
│
└── scripts/            # Standalone Python scripts for quick runs
    ├── quick_tps_toy.py                   # TPS command-line tool
    ├── quick_tis_toy.py                   # TIS command-line tool
    └── README_scripts.md                   # Script documentation
```

## Quick Start

### Jupyter Notebooks

For interactive learning with visualizations, use the Jupyter notebooks:

```bash
# Navigate to the notebook directory
cd notebooks/

# Start Jupyter
jupyter notebook

# Open one of the notebooks to see step-by-step examples
```

**Recommended order:**
1. `01_basic_tps_toy_system.ipynb` - Learn TPS basics
2. `02_basic_tis_toy_system.ipynb` - Learn TIS basics with interfaces

### Command-Line Scripts

For quick testing or batch processing, use the Python scripts:

```bash
# Basic TPS with default potential (potential_1)
python scripts/quick_tps_toy.py

# TPS with specific potential
python scripts/quick_tps_toy.py potential_1 10

# TIS with default potential
python scripts/quick_tis_toy.py

# TIS with custom potential and more steps
python scripts/quick_tis_toy.py potential_2 20
```

## Available Toy Potentials

The ops-setup package includes several toy potentials suitable for testing:

| Potential | Dimensionality | Characteristics | Use Case |
|-----------|---|---|---|
| `potential_0` | 1D | Single barrier | Fastest testing, minimal setup |
| `potential_1` | 2D | Two minima with Gaussian barrier | Standard testing, good for TIS |
| `potential_2` | 2D | Shifted barrier, asymmetric | More challenging transitions |

## Workflow Comparison

### TPS Workflow

```
ToyTPSSetup
   ↓
Create Engine
   ↓
Generate Initial Trajectory
   ↓
Create Network (TPS)
   ↓
Create Move Scheme
   ↓
Run PathSampling
   ↓
Analyze Trajectories
```

### TIS Workflow

```
ToyTISSetup
   ↓
Create Engine with Interfaces
   ↓
Generate Initial Trajectory
   ↓
Create Network (TIS)
   ↓
Create Move Scheme (multi-ensemble)
   ↓
Run PathSampling
   ↓
Analyze by Interface Ensemble
```

## Code Examples

### Minimal TPS Example

```python
from ops_setup.systems.examples.toy_systems import ToyTPSSetup
import openpathsampling as paths

# Setup
tps = ToyTPSSetup(potential_name='potential_1')
paths.PathMover.engine = tps.md_engine

# Initial trajectory
init_traj = paths.Trajectory(tps.pes.simple_initial_path(200, tps.md_engine))

# Network and scheme
network = tps.create_network("TPS")
move_scheme = tps.create_move_scheme(network, "OneWay")

# Initial conditions
ic = move_scheme.initial_conditions_from_trajectories(init_traj)

# Run
storage = paths.Storage("tps.nc", "w", template=tps.template)
sampler = paths.PathSampling(storage, move_scheme, ic)
sampler.run(10)  # 10 MC steps
```

### Minimal TIS Example

```python
from ops_setup.systems.examples.toy_systems import ToyTISSetup
import openpathsampling as paths

# Setup with interfaces
tis = ToyTISSetup(
    potential_name='potential_1',
    interface_values=[0.2, 0.4, 0.6, 0.8]
)
paths.PathMover.engine = tis.md_engine

# Rest of workflow is same as TPS
# but TIS automatically handles multiple interface ensembles
network = tis.create_network("TIS")
move_scheme = tis.create_move_scheme(network, "OneWay")
# ... etc
```

## Key Concepts

### TPS (Transition Path Sampling)
- Samples direct A↔B transitions
- Single ensemble of paths
- Good for understanding transition mechanisms
- Faster setup, slower sampling

### TIS (Transition Interface Sampling)
- Uses ordered interfaces to decompose transition
- Multiple ensembles (one per interface)
- More efficient sampling
- Better for calculating transition rates
- More complex move scheme

## Next Steps

After mastering these toy examples:

1. **Move to Host-Guest System** - See `examples/host_guest/` for realistic OpenMM simulations
2. **AIMMD Integration** - See `aimmd-tis/examples/` for combining these methods with AIMMD learning
3. **Custom Systems** - Extend `ToyTPSSetup` or create new subclasses for your own potentials

## Troubleshooting

### Import Errors
```python
ImportError: cannot import name 'ToyTPSSetup'
```
Solution: Ensure ops-setup is installed: `pip install -e /path/to/ops-setup`

### Engine Not Set
```
RuntimeError: PathMover.engine not set
```
Solution: Always do `paths.PathMover.engine = tps.md_engine` before creating trajectories

### Initial Conditions Fail
```
Check initial_conditions.sanity_check()
```
Solution: Verify initial trajectory crosses from A to B correctly

## Performance Tips

1. **For Testing**: Use `potential_0` (1D) for fastest runs
2. **For Development**: Use `potential_1` (2D standard) as a good balance
3. **More Steps**: Increase `n_steps` in scripts to get better statistics
4. **Parallel Runs**: Run multiple instances with different random seeds for better coverage

## File Outputs

Each run creates:
- `tps_*.nc` or `tis_*.nc` - NetCDF storage file with all simulation data
  - Accessible via `paths.Storage()`
  - Contains trajectories, ensembles, move statistics, etc.

## Documentation

For more details:
- [ops-setup README](../../README.md) - Package overview
- [ops-setup QUICKSTART](../../QUICKSTART.md) - Getting started guide
- [OpenPathSampling Docs](https://openpathsampling.org/) - Core library documentation
- Individual notebook documentation - See code cell comments

## Contributing

To add new examples:
1. Create a new notebook or script in the appropriate directory
2. Include docstrings explaining what it demonstrates
3. Use consistent styling with existing examples
4. Test to ensure imports work correctly
5. Update this README

---

**Last Updated**: 2024
**ops-setup Version**: 1.0.0+

# OpenMM from GROMACS Examples

This directory contains examples for using the `openmm_from_gromacs` module to set up OpenMM simulations from GROMACS files and integrate with OpenPathSampling.

## Quick Start

```python
from ops_setup.engines import OpenMMGromacsTPS, GromacsCVFactory

# Define collective variables
factory = GromacsCVFactory(topology)
cv = factory.distance_cv('distance', (10, 200))

# Define states
state_defs = {
    'stateA': {'cvs': [cv], 'bounds': [(0.1, 0.2)]},
    'stateB': {'cvs': [cv], 'bounds': [(0.8, 1.0)]}
}

# Create TPS setup
tps = OpenMMGromacsTPS('system.top', 'system.gro', 'ff/', 
                       state_definitions=state_defs)
network = tps.create_tps_network()
```

## Files

- **README.md** (this file) - Complete API documentation and guide
- **general_examples.py** - 4 example patterns for different use cases

## Example Patterns

### 1. Minimal MD Setup
Just run MD from GROMACS files without path sampling.

### 2. Simple TPS
Two-state TPS with a single distance CV.

### 3. Advanced TPS
Multi-dimensional state space with multiple CVs.

### 4. Custom CV
Define custom collective variables from functions.

## See Also

For system-specific examples:
- T4L protein: `/home/rbreeba/Projects/T4L/t4l_setup/t4l_tps_setup.py`

For toy systems:
- `ops-setup/examples/scripts/quick_openmm_tps.py`

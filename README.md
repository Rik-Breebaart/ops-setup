# ops-setup

**Utilities and base classes for setting up TPS/TIS simulations with OpenPathSampling**

## Overview

`ops-setup` provides a structured, reusable framework for setting up Transition Path Sampling (TPS) and Transition Interface Sampling (TIS) simulations using [OpenPathSampling](http://openpathsampling.org/). The package is designed to:

- **Separate concerns**: Pure OPS/TPS/TIS functionality is independent from specific applications (like AIMMD)
- **Promote reusability**: System-specific setups inherit from generic base classes
- **Ensure consistency**: Standardized configuration files and setup patterns
- **Enhance reproducibility**: Clear templates and examples for new systems

## Installation

### Basic Installation

```bash
cd /path/to/ops-setup
pip install -e .
```

### With OpenMM Support

```bash
pip install -e ".[openmm]"
```

### With All Dependencies (including dev tools)

```bash
pip install -e ".[all]"
```

## Package Structure

```
ops-setup/
├── src/ops_setup/
│   ├── core/                  # Core TPS/TIS setup classes
│   │   ├── config_reader.py   # Configuration file utilities
│   │   ├── tps_setup.py       # Base TPS setup class
│   │   └── tis_setup.py       # TIS setup extension
│   ├── engines/               # MD engine implementations
│   │   └── openmm_engine.py   # OpenMM-based engines
│   ├── systems/               # System-specific implementations
│   │   └── examples/
│   │       ├── alanine_dipeptide/  # Alanine dipeptide in vacuum (C7eq/C7ax)
│   │       ├── host_guest/    # Host-guest binding example
│   │       └── toy_systems/   # Toy model examples
│   └── utils/                 # Utility functions
│       └── argument_parser.py # CLI argument parsing
└── examples/
    ├── config_files/          # Example configuration files
    └── notebooks/             # Tutorial notebooks
```

## Quick Start

### 0. Alanine dipeptide in vacuum (no files needed)

```python
from ops_setup.systems.examples.alanine_dipeptide import AlanineDipeptideVacuumSetup, transform_functions as tf

ad = AlanineDipeptideVacuumSetup()               # packaged config: 300 K, 2 fs, C7eq / C7ax
path = ad.generate_initial_path(seed=1)          # hot MD, first C7eq -> C7ax transition
network = ad.create_network("TPS")
scheme = ad.create_move_scheme(network, scheme_type="TwoWay")
descriptors = tf.descriptor_sincos(path)         # (n, 8): sin/cos of phi, psi, omega1, omega2
```

The system comes from openmmtools (`AlanineDipeptideVacuum`, amber ff96, HBonds). The states are φ/ψ boxes from the
`States` block of `config_alanine_dipeptide_vacuum.json`. `ad.beta` and `ad.kT` hold the inverse temperature and the
thermal energy. Notebook: `examples/notebooks/alanine_dipeptide/01_basic_tps_alanine_dipeptide.ipynb`; tests:
`tests/test_alanine_dipeptide.py`.

### 1. Basic TPS Setup

```python
from ops_setup.engines import AmberOpenMMSetup
from ops_setup.systems.examples.host_guest import HostGuestTPSSetup
from ops_setup.systems.examples.host_guest.transform_functions import cv_hg_distance

# Initialize the system
tps_setup = HostGuestTPSSetup(
    config_path="tps_config.json",
    cv_function=cv_hg_distance,
    resource_directory="./system_files/"
)

# Create TPS network and move scheme
network = tps_setup.create_network(network_type="TPS")
move_scheme = tps_setup.create_move_scheme(network, scheme_type="OneWay")

# Run path sampling
# ... (see examples for full workflow)
```

### 2. TIS Setup

```python
from ops_setup.systems.examples.host_guest import HostGuestTISSetup
from ops_setup.systems.examples.host_guest.transform_functions import cv_hg_distance

# Initialize TIS setup
tis_setup = HostGuestTISSetup(
    tps_config_path="tps_config.json",
    tis_config_path="tis_config.json",
    cv_function=cv_hg_distance,
    resource_directory="./system_files/"
)

# Create interface set and TIS network
interface_value = 0.8
interface_set = tis_setup.create_interface_set(
    cv=cv_hg_distance,
    interface_value=interface_value,
    direction="forward"
)

network = tis_setup.create_tis_network(interface_set, direction="forward")
move_scheme = tis_setup.create_tis_move_scheme(network)
```

### 3. Configuration Files

Configuration files are in JSON format. Example TPS config:

```json
{
  "system_name": "CB7-B2",
  "platform_name": "CUDA",
  "UNITS": {
    "size_unit": "nanometer",
    "press_unit": "bar",
    "temp_unit": "kelvin",
    "time_unit": "picosecond"
  },
  "Integrator_settings": {
    "temperature": 298.15,
    "pressure": 1.0,
    "dt": 0.002,
    "friction": 1.0,
    "barostat_frequency": 25,
    "constant_variable": "P"
  },
  "TPS_settings": {
    "n_frames_max": 5000,
    "n_steps_per_frame": 10
  },
  "system_files": {
    "topology_file": "complex.prmtop",
    "coordinate_file": "complex.inpcrd",
    "state_file": "equilibrated.state"
  },
  "system_parameters": {
    "nonbonded_cutoff": 1.0,
    "ewald_tolerance": 0.0005
  },
  "States": {
    "bound": 0.5,
    "unbound": 1.5
  }
}
```

## Creating Custom System Setups

To create a setup for a new system:

1. **Inherit from base classes**:

```python
from ops_setup.engines import OpenMMTPSSetup
import openpathsampling as paths

class MySystemSetup(OpenMMTPSSetup):
    def __init__(self, config_path, my_cv_function, **kwargs):
        self.my_cv = my_cv_function
        super().__init__(config_path, **kwargs)
    
    def _define_states(self):
        """Define system-specific states."""
        stateA = paths.CVDefinedVolume(
            self.my_cv, 
            lambda_min=0.0, 
            lambda_max=0.3
        ).named('stateA')
        
        stateB = paths.CVDefinedVolume(
            self.my_cv,
            lambda_min=0.7,
            lambda_max=float('inf')
        ).named('stateB')
        
        return (stateA, stateB)
```

2. **Create system-specific collective variables** in a separate module
3. **Provide configuration templates** for your system
4. **Document the required config parameters**

## Integration with AIMMD-TIS

This package is designed to work seamlessly with AIMMD-TIS workflows:

```python
from ops_setup.systems.examples.host_guest import HostGuestTISSetup
from aimmdTIS import AIMMD_TIS

# Setup TIS using ops-setup
tis_setup = HostGuestTISSetup(
    tps_config_path="tps_config.json",
    tis_config_path="tis_config.json",
    cv_function=cv_hg_distance,
    resource_directory="./system_files/"
)

# Use AIMMD for intelligent shooting point selection
aimmd_tis = AIMMD_TIS(
    engine=tis_setup.md_engine,
    AIMMD_model=trained_model,
    stateA=tis_setup.states[0],
    stateB=tis_setup.states[1],
    descriptor_transform=descriptor_transform
)

# Run AIMMD-enhanced TIS
# ... (see AIMMD-TIS documentation)
```

## Architecture

### Base Classes

- **`TPSSetupBase`**: Abstract base class for TPS simulations
  - Handles configuration loading
  - Defines interface for engine and state setup
  - Provides network and move scheme creation

- **`TISSetupBase`**: Extends `TPSSetupBase` for TIS
  - Adds interface management
  - Handles TIS-specific configuration
  - Creates TIS networks and schemes

- **`OpenMMTPSSetup`**: OpenMM implementation of TPS setup
  - Integrator configuration
  - Platform management
  - Template snapshot creation

- **`AmberOpenMMSetup`**: AMBER file format support
  - Loads .prmtop and .inpcrd files
  - Handles saved state files
  - Creates OpenMM system

### Design Philosophy

1. **Separation of Concerns**: Generic OPS functionality is separated from system-specific details
2. **Inheritance Over Composition**: System-specific setups inherit and extend base classes
3. **Configuration-Driven**: All simulation parameters are specified in JSON configs
4. **Extensibility**: Easy to add new systems, engines, or collective variables

## Examples

See the `examples/` directory for:
- Configuration file templates
- Jupyter notebook tutorials
- Complete workflow examples

## Contributing

Contributions are welcome! To add a new system:

1. Create a new directory under `src/ops_setup/systems/examples/your_system/`
2. Implement setup classes inheriting from base classes
3. Provide collective variable definitions
4. Include example configuration files
5. Add documentation and examples

## Related Projects

- [OpenPathSampling](http://openpathsampling.org/) - Core path sampling library
- [AIMMD](https://github.com/bio-phys/aimmd) - AI-guided molecular mechanism discovery
- [AIMMD-TIS](https://github.com/...) - AIMMD integration with TIS

## License

GPL-3.0

## Citation

If you use ops-setup in your research, please cite:

- OpenPathSampling: [citation]
- AIMMD (if applicable): Jung et al., Nature Computational Science 3, 334–345 (2023)

## Support

For questions, issues, or suggestions:
- Open an issue on GitHub
- Contact: [your contact info]

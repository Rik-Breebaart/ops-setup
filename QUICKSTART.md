# ops-setup Quick Start Guide

## Installation

```bash
# Navigate to ops-setup directory
cd /Users/rbreeba/code/ops-setup

# Install in development mode with OpenMM support
pip install -e ".[openmm]"

# Verify installation
python -c "import ops_setup; print(ops_setup.__version__)"
```

## Basic Usage Examples

### 1. Setup Host-Guest System for TPS

```python
from ops_setup.systems.examples.host_guest import HostGuestTPSSetup
from ops_setup.systems.examples.host_guest.transform_functions import cv_hg_distance
from pathlib import Path

# Setup the system
tps_setup = HostGuestTPSSetup(
    config_path="TPS_config.json",
    cv_function=cv_hg_distance,
    resource_directory=Path("./system_files/")
)

# Create TPS network
network = tps_setup.create_network(network_type="TPS")

# Create move scheme
move_scheme = tps_setup.create_move_scheme(network, scheme_type="OneWay")

# Access simulation components
engine = tps_setup.md_engine
template = tps_setup.template
states = tps_setup.states  # (bound_state, unbound_state)
```

### 2. Setup Host-Guest System for TIS

```python
from ops_setup.systems.examples.host_guest import HostGuestTISSetup
from ops_setup.systems.examples.host_guest.transform_functions import cv_hg_distance
from pathlib import Path
import openpathsampling as paths

# Setup TIS system
tis_setup = HostGuestTISSetup(
    tps_config_path="TPS_config.json",
    tis_config_path="TIS_config.json",
    cv_function=cv_hg_distance,
    resource_directory=Path("./system_files/")
)

# Create interface set
interface_value = 0.8
interface_set = tis_setup.create_interface_set(
    cv=cv_hg_distance,
    interface_value=interface_value,
    direction="forward"
)

# Create TIS network
network = tis_setup.create_tis_network(interface_set, direction="forward")

# Create move scheme for TIS
move_scheme = tis_setup.create_tis_move_scheme(network)
```

### 3. Use with AIMMD-TIS

```python
from ops_setup.systems.examples.host_guest import HostGuestTISSetup
from ops_setup.systems.examples.host_guest.transform_functions import (
    cv_hg_distance, descriptor_transform_HG_new_symmetric_continuous_waters_scaled
)
from aimmdTIS import AIMMD_setup
from pathlib import Path

# Setup TIS using ops-setup
tis_setup = HostGuestTISSetup(
    tps_config_path="TPS_config.json",
    tis_config_path="TIS_config.json",
    cv_function=cv_hg_distance,
    resource_directory=Path("./system_files/")
)

# Get descriptor dimension
test_descriptor = descriptor_transform_HG_new_symmetric_continuous_waters_scaled(
    tis_setup.template
)
descriptor_dim = len(test_descriptor)

# Setup AIMMD
aimmd_setup = AIMMD_setup(
    config_path="TPS_config.json",
    descriptor_dim=descriptor_dim,
    states=tis_setup.states,
    descriptor_transform=descriptor_transform_HG_new_symmetric_continuous_waters_scaled,
    print_config=True
)

# Now use AIMMD with TIS
# ...
```

### 4. Create Custom System Setup

```python
from ops_setup.engines import AmberOpenMMSetup
from ops_setup.core.config_reader import read_config
import openpathsampling as paths

class MyCustomSystemSetup(AmberOpenMMSetup):
    """Custom setup for your molecular system."""
    
    def __init__(self, config_path, my_cv_function, **kwargs):
        self.my_cv = my_cv_function
        super().__init__(config_path, **kwargs)
    
    def _define_states(self):
        """Define your custom states."""
        # Load bounds from config
        config = self.config
        bound = config.get('States', {}).get('bound', 0.5)
        unbound = config.get('States', {}).get('unbound', 1.5)
        
        stateA = paths.CVDefinedVolume(
            self.my_cv,
            lambda_min=0.0,
            lambda_max=bound
        ).named('stateA')
        
        stateB = paths.CVDefinedVolume(
            self.my_cv,
            lambda_min=unbound,
            lambda_max=float('inf')
        ).named('stateB')
        
        return (stateA, stateB)

# Usage
my_setup = MyCustomSystemSetup(
    config_path="config.json",
    my_cv_function=my_cv,
    resource_directory="./files/"
)
```

## Configuration Files

### Minimal TPS Configuration

```json
{
  "system_name": "MySystem",
  "platform_name": "CPU",
  "UNITS": {
    "size_unit": "nanometer",
    "temp_unit": "kelvin",
    "time_unit": "picosecond"
  },
  "Integrator_settings": {
    "temperature": 298.15,
    "dt": 0.002,
    "friction": 1.0,
    "constant_variable": "V"
  },
  "TPS_settings": {
    "n_frames_max": 5000,
    "n_steps_per_frame": 10
  },
  "system_files": {
    "topology_file": "system.prmtop",
    "coordinate_file": "system.inpcrd"
  },
  "States": {
    "bound": 0.5,
    "unbound": 1.5
  }
}
```

### TIS Configuration Addition

```json
{
  "TIS": {
    "Scheme": {
      "Shooting_Move": "OneWay",
      "selector": "uniform"
    },
    "interface_parameters": {
      "interfaces_forward": [0.6, 0.8, 1.0, 1.2],
      "interfaces_backward": [0.6, 0.8, 1.0, 1.2]
    }
  }
}
```

## File Organization

Place your system files in a resource directory:

```
./my_simulation/
├── TPS_config.json
├── TIS_config.json
├── system_files/
│   ├── system.prmtop
│   ├── system.inpcrd
│   └── equilibrated.state
├── run_script.py
└── output/
    └── (simulation results)
```

## Common Operations

### Print Configuration

```python
from ops_setup.core import print_config

tps_setup = HostGuestTPSSetup(...)
print_config(tps_setup.config)
```

### Access System Components

```python
# MD engine
engine = tps_setup.md_engine

# Snapshot template
template = tps_setup.template

# Stable states
stateA, stateB = tps_setup.states

# Topology
topology = tps_setup.topology

# Configuration
config = tps_setup.config
```

### Create CLI Parsers

```python
from ops_setup.utils import get_tps_parser, get_tis_parser

# For TPS simulations
tps_parser = get_tps_parser()
args = tps_parser.parse_args()

# For TIS simulations
tis_parser = get_tis_parser()
args = tis_parser.parse_args()
```

## Troubleshooting

### Import Error: "No module named 'ops_setup'"

```bash
# Make sure ops-setup is installed
cd /Users/rbreeba/code/ops-setup
pip install -e ".[openmm]"

# Check installation
python -c "import ops_setup; print(ops_setup.__version__)"
```

### Missing Configuration Keys

- Check that your JSON file has all required sections
- Use config templates from `examples/config_files/` as reference
- Use `validate_config_keys()` to check configuration

```python
from ops_setup.core import validate_config_keys

required = ['system_name', 'platform_name', 'Integrator_settings']
validate_config_keys(config, required)
```

### OpenMM Errors

- Ensure OpenMM is installed: `pip install openmm openmmtools`
- Check that platform is available: `python -c "from openmm import Platform; print(Platform.getPlatformNames())"`
- Verify file paths are correct and files exist

## Next Steps

1. **Review Documentation**: Read `README.md` for comprehensive guide
2. **Check Examples**: Look at configuration templates in `examples/config_files/`
3. **Development Guide**: See `DEVELOPMENT.md` for creating custom systems
4. **AIMMD Integration**: See examples showing AIMMD-TIS integration
5. **Run Tests**: Create test configurations and verify setup works

## Resources

- **README.md**: Complete package documentation
- **DEVELOPMENT.md**: Guide for adding new systems
- **REFACTORING_SUMMARY.md**: Details of the refactoring
- **examples/config_files/**: Configuration templates
- **src/ops_setup/systems/examples/host_guest/**: Example system implementation

## Getting Help

1. Check documentation in `README.md`
2. Review `DEVELOPMENT.md` for design patterns
3. Look at `examples/` directory for reference implementations
4. Check existing setup classes for similar patterns

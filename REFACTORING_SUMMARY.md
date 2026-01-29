# Refactoring Summary: ops-setup Package Creation

## Overview

A comprehensive refactoring has been completed to extract and reorganize OpenPathSampling (OPS) TPS/TIS functionality into a standalone, reusable `ops-setup` package. This separation provides clear architectural boundaries, improved maintainability, and enables reuse across multiple projects.

## What Was Done

### 1. Created ops-setup Package Structure

**Location**: `/Users/rbreeba/code/ops-setup/`

```
ops-setup/
├── src/ops_setup/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config_reader.py        (read_config, print_config, validation)
│   │   ├── tps_setup.py            (TPSSetupBase abstract class)
│   │   └── tis_setup.py            (TISSetupBase class with TIS features)
│   ├── engines/
│   │   ├── __init__.py
│   │   └── openmm_engine.py        (OpenMMTPSSetup, AmberOpenMMSetup)
│   ├── systems/
│   │   ├── __init__.py
│   │   └── examples/
│   │       ├── __init__.py
│   │       ├── host_guest/
│   │       │   ├── __init__.py
│   │       │   ├── setup.py        (HostGuestTPSSetup, HostGuestTISSetup)
│   │       │   └── transform_functions.py (CVs for host-guest)
│   │       └── toy_systems/
│   │           └── __init__.py
│   ├── utils/
│   │   ├── __init__.py
│   │   └── argument_parser.py      (CLI utilities)
│   └── __pycache__/
├── examples/
│   ├── config_files/
│   │   ├── TPS_template.json
│   │   ├── TPS_with_AIMMD_template.json
│   │   ├── TIS_template.json
│   │   └── toy_model_template.json
│   └── notebooks/                  (for future examples)
├── tests/                          (for future unit tests)
├── README.md                       (comprehensive user documentation)
├── DEVELOPMENT.md                  (developer guide)
└── pyproject.toml                  (package configuration)
```

### 2. Core Modules Created

#### **config_reader.py**
- `read_config()`: Load JSON configuration files
- `print_config()`: Pretty-print hierarchical configurations
- `validate_config_keys()`: Validate required configuration keys

#### **tps_setup.py**
- `TPSSetupBase`: Abstract base class for TPS simulations
  - Handles configuration loading
  - Defines interface for MD engine setup
  - Provides network and move scheme creation
  - Abstract methods: `_setup_integrator()`, `_setup_system()`, `_create_template()`, `_define_states()`

#### **tis_setup.py**
- `TISSetupBase`: Extends `TPSSetupBase` for TIS simulations
  - Adds TIS-specific configuration handling
  - Interface set creation
  - TIS network generation
  - TIS move scheme creation
  - Methods for managing interface values

#### **openmm_engine.py**
- `OpenMMTPSSetup`: OpenMM implementation of TPS
  - Integrator setup (VVVR)
  - Platform management
  - Template snapshot creation
  - System parameters from config
  
- `AmberOpenMMSetup`: Concrete AMBER support
  - Loads .prmtop and .inpcrd files
  - Supports saved state files
  - Barostat configuration

#### **argument_parser.py**
- `create_parser()`: Generic argument parser creation
- `get_tps_parser()`: Pre-configured TPS parser
- `get_tis_parser()`: Pre-configured TIS parser
- Common argument definitions

#### **host_guest/setup.py**
- `HostGuestTPSSetup`: System-specific TPS setup
- `HostGuestTISSetup`: System-specific TIS setup
- Bound/unbound state definitions using distance CV

### 3. Configuration Files

Example templates in `examples/config_files/`:
- **TPS_template.json**: Basic TPS configuration
- **TPS_with_AIMMD_template.json**: TPS with AIMMD settings
- **TIS_template.json**: TIS-specific parameters
- **toy_model_template.json**: Toy model configuration

### 4. Documentation

#### **README.md**
- Package overview and motivation
- Installation instructions
- Quick start examples
- Configuration documentation
- Custom system development guide
- AIMMD integration example

#### **DEVELOPMENT.md**
- Architecture overview
- Design patterns explanation
- Step-by-step guide for adding new systems
- Guide for adding new MD engines
- Configuration best practices
- Testing recommendations
- Common pitfalls and solutions
- Integration with AIMMD-TIS

### 5. Integration with aimmd-tis

Modified `/Users/rbreeba/code/aimmd-tis/src/aimmdTIS/Tools.py`:
- Updated `read_config()` and `print_config()` to import from `ops_setup.core`
- Added fallback for backwards compatibility
- Removed duplicate code

## Key Benefits

### 1. **Separation of Concerns**
- Pure OPS/TPS/TIS logic is decoupled from AIMMD
- Each package has clear responsibilities
- Changes in one package don't affect the other

### 2. **Reusability**
- ops-setup can be used for any OPS-based TPS/TIS project
- Not limited to AIMMD workflows
- System-specific code is clearly organized

### 3. **Consistency**
- Standardized configuration format (JSON)
- Common setup patterns across all systems
- Shared utilities for configuration and argument parsing

### 4. **Maintainability**
- Clear inheritance hierarchy
- Abstract base classes define interfaces
- Documentation is comprehensive

### 5. **Extensibility**
- Easy to add new systems (just inherit base classes)
- Easy to add new MD engines
- Configuration-driven customization

### 6. **Reproducibility**
- System configurations are explicit and documented
- Configuration templates for common systems
- Clear initialization patterns

## Architecture

### Inheritance Hierarchy

```
TPSSetupBase (abstract)
    ├── TISSetupBase (extends TPSSetupBase)
    │
    └── OpenMMTPSSetup (implements TPSSetupBase)
        ├── AmberOpenMMSetup (adds AMBER file support)
        │   └── HostGuestTPSSetup (system-specific)
        │
        └── [Other OpenMM systems]
```

### Design Patterns Used

1. **Template Method Pattern**: Base classes define setup sequence, subclasses implement specific steps
2. **Strategy Pattern**: Engines and systems are swappable implementations
3. **Configuration Pattern**: All parameters from JSON files
4. **Inheritance Pattern**: System-specific customization through class hierarchy

## How to Use

### Basic TPS with ops-setup

```python
from ops_setup.engines import AmberOpenMMSetup
import openpathsampling as paths

# Setup system
tps = AmberOpenMMSetup("config.json", resource_directory="./system_files/")

# Create network and move scheme
network = tps.create_network("TPS")
move_scheme = tps.create_move_scheme(network, "OneWay")

# Run sampling
# ...
```

### Host-Guest System

```python
from ops_setup.systems.examples.host_guest import HostGuestTPSSetup
from ops_setup.systems.examples.host_guest.transform_functions import cv_hg_distance

tps = HostGuestTPSSetup(
    config_path="tps_config.json",
    cv_function=cv_hg_distance,
    resource_directory="./system_files/"
)
```

### With AIMMD-TIS

```python
from ops_setup.systems.examples.host_guest import HostGuestTISSetup
from aimmdTIS import AIMMD_setup

tis = HostGuestTISSetup(
    "tps_config.json",
    "tis_config.json",
    cv_hg_distance,
    resource_directory="./system_files/"
)

# Use AIMMD on top of ops-setup
aimmd = AIMMD_setup(
    "tps_config.json",
    descriptor_dim,
    tis.states,
    descriptor_transform=descriptor_transform
)
```

## Configuration Example

```json
{
  "system_name": "CB7-B2",
  "platform_name": "CUDA",
  "UNITS": {
    "size_unit": "nanometer",
    "temp_unit": "kelvin",
    "time_unit": "picosecond"
  },
  "Integrator_settings": {
    "temperature": 298.15,
    "dt": 0.002,
    "friction": 1.0
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

## Next Steps

### For aimmd-tis
1. Update run scripts to import from ops-setup
2. Remove redundant setup code
3. Focus on AIMMD-specific functionality
4. Create examples showing AIMMD + ops-setup integration

### For other projects
1. ops-setup can now be installed as standalone package
2. Create system-specific setups by inheriting base classes
3. Share common OPS/TPS/TIS infrastructure

### For development
1. Add unit tests in `tests/` directory
2. Create Jupyter notebook examples in `examples/notebooks/`
3. Implement toy system examples
4. Add support for other MD engines (Gromacs, NAMD, etc.)

## Files Modified/Created

### Created
- All files under `/Users/rbreeba/code/ops-setup/src/ops_setup/`
- Configuration templates
- Documentation files

### Modified
- `/Users/rbreeba/code/aimmd-tis/src/aimmdTIS/Tools.py` - Updated imports

### Still in aimmd-tis (unchanged)
- `TIS_AIMMD_setup.py` - AIMMD-specific TIS integration
- `TIS_Analysis.py` - Analysis utilities
- `Toy_potentials.py` - Toy potential definitions
- `Training.py` - AIMMD training code
- `Toy_analysis.py` - Analysis and visualization
- Examples and run scripts

## Backwards Compatibility

- aimmd-tis still works as before
- `read_config()` and `print_config()` are available in both packages
- Fallback imports ensure compatibility if ops-setup is not installed

## Installation

```bash
# Install ops-setup standalone
cd /Users/rbreeba/code/ops-setup
pip install -e .

# Or with OpenMM support
pip install -e ".[openmm]"

# For development
pip install -e ".[all]"
```

## Summary of Benefits

✅ **Clean separation** of OPS/TPS/TIS from AIMMD  
✅ **Reusable** for any OPS-based project  
✅ **Well-documented** with guides and examples  
✅ **Extensible** architecture for new systems  
✅ **Configuration-driven** for reproducibility  
✅ **Consistent** patterns across implementations  
✅ **Maintainable** with clear code organization  

The refactoring maintains full compatibility while providing a solid foundation for future development and external use.

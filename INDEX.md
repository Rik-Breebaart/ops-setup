# ops-setup - Complete Documentation Index

## Quick Navigation

### For Users
- **[QUICKSTART.md](QUICKSTART.md)** - Get up and running in 5 minutes
- **[README.md](README.md)** - Complete user guide and API reference
- **[examples/config_files/](examples/config_files/)** - Configuration templates

### For Developers
- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Architecture and extension guide
- **[REFACTORING_SUMMARY.md](REFACTORING_SUMMARY.md)** - Detailed refactoring details

---

## Package Overview

**ops-setup** provides reusable utilities and base classes for setting up Transition Path Sampling (TPS) and Transition Interface Sampling (TIS) simulations using [OpenPathSampling](http://openpathsampling.org/).

## Installation

```bash
cd /Users/rbreeba/code/ops-setup
pip install -e ".[openmm]"
```

## Key Features

✅ **Modular Design** - Separate OPS/TPS/TIS from application-specific code  
✅ **Reusable** - Use for any OPS-based project  
✅ **Well-Documented** - Comprehensive guides and examples  
✅ **Extensible** - Easy to add new systems and engines  
✅ **Configuration-Driven** - JSON-based reproducible setups  

## Package Structure

```
src/ops_setup/
├── core/              # Core TPS/TIS setup classes
├── engines/           # MD engine implementations
├── systems/           # System-specific setups
│   └── examples/
│       ├── host_guest/    # Host-guest binding example
│       └── toy_systems/   # Toy models
└── utils/             # Utility functions
```

## Core Classes

### Base Classes

- **`TPSSetupBase`** ([src/ops_setup/core/tps_setup.py](src/ops_setup/core/tps_setup.py))
  - Abstract base class for TPS simulations
  - Defines interface for system setup
  - Handles configuration management

- **`TISSetupBase`** ([src/ops_setup/core/tis_setup.py](src/ops_setup/core/tis_setup.py))
  - Extends TPSSetupBase for TIS
  - Adds interface management
  - TIS-specific move schemes

### Concrete Implementations

- **`OpenMMTPSSetup`** ([src/ops_setup/engines/openmm_engine.py](src/ops_setup/engines/openmm_engine.py))
  - OpenMM implementation for TPS
  - Integrator and platform management

- **`AmberOpenMMSetup`** ([src/ops_setup/engines/openmm_engine.py](src/ops_setup/engines/openmm_engine.py))
  - AMBER topology file support (.prmtop, .inpcrd)
  - State file loading

- **`HostGuestTPSSetup`** ([src/ops_setup/systems/examples/host_guest/setup.py](src/ops_setup/systems/examples/host_guest/setup.py))
  - System-specific setup for host-guest binding
  - Bound/unbound state definitions

- **`HostGuestTISSetup`** ([src/ops_setup/systems/examples/host_guest/setup.py](src/ops_setup/systems/examples/host_guest/setup.py))
  - TIS for host-guest systems
  - Interface management

## Configuration

### Available Templates

- **[TPS_template.json](examples/config_files/TPS_template.json)** - Basic TPS configuration
- **[TPS_with_AIMMD_template.json](examples/config_files/TPS_with_AIMMD_template.json)** - With AIMMD settings
- **[TIS_template.json](examples/config_files/TIS_template.json)** - TIS parameters
- **[toy_model_template.json](examples/config_files/toy_model_template.json)** - Toy model example

### Configuration Structure

```json
{
  "system_name": "MySystem",
  "platform_name": "CUDA",
  "UNITS": { ... },
  "Integrator_settings": { ... },
  "TPS_settings": { ... },
  "TIS": { ... }
}
```

See [README.md - Configuration Files](README.md#3-configuration-files) for details.

## Usage Examples

### Basic TPS

```python
from ops_setup.systems.examples.host_guest import HostGuestTPSSetup
from ops_setup.systems.examples.host_guest.transform_functions import cv_hg_distance

tps = HostGuestTPSSetup(
    config_path="TPS_config.json",
    cv_function=cv_hg_distance,
    resource_directory="./system_files/"
)

network = tps.create_network(network_type="TPS")
move_scheme = tps.create_move_scheme(network, scheme_type="OneWay")
```

### TIS

```python
from ops_setup.systems.examples.host_guest import HostGuestTISSetup

tis = HostGuestTISSetup(
    tps_config_path="TPS_config.json",
    tis_config_path="TIS_config.json",
    cv_function=cv_hg_distance,
    resource_directory="./system_files/"
)

interface_set = tis.create_interface_set(cv_hg_distance, 0.8, "forward")
network = tis.create_tis_network(interface_set, "forward")
move_scheme = tis.create_tis_move_scheme(network)
```

### With AIMMD

```python
from aimmdTIS import AIMMD_setup

aimmd = AIMMD_setup(
    config_path="TPS_config.json",
    descriptor_dim=descriptor_dim,
    states=tis.states,
    descriptor_transform=descriptor_transform
)
```

See [QUICKSTART.md](QUICKSTART.md) for more examples.

## Creating Custom Systems

### Step-by-Step Guide

1. **Choose base class** - `AmberOpenMMSetup`, `OpenMMTPSSetup`, or `TPSSetupBase`
2. **Define collective variables** - Create CV module for your system
3. **Implement setup class** - Inherit and implement abstract methods
4. **Create configuration** - Use template and customize
5. **Document your system** - Add README and examples

See [DEVELOPMENT.md - Adding a New System](DEVELOPMENT.md#adding-a-new-system) for detailed instructions.

## API Reference

### Core Functions

- **`read_config(file_path)`** - Load JSON configuration
- **`print_config(config)`** - Pretty-print configuration
- **`validate_config_keys(config, required_keys)`** - Validate configuration

### Setup Classes

See class docstrings in:
- [src/ops_setup/core/tps_setup.py](src/ops_setup/core/tps_setup.py)
- [src/ops_setup/core/tis_setup.py](src/ops_setup/core/tis_setup.py)
- [src/ops_setup/engines/openmm_engine.py](src/ops_setup/engines/openmm_engine.py)

### Utility Functions

- **`create_parser(arguments_list)`** - Create CLI argument parser
- **`get_tps_parser()`** - Pre-configured TPS parser
- **`get_tis_parser()`** - Pre-configured TIS parser

See [src/ops_setup/utils/argument_parser.py](src/ops_setup/utils/argument_parser.py)

## Integration with AIMMD-TIS

ops-setup is designed to work seamlessly with AIMMD-TIS:

- **Pure OPS functionality**: All TPS/TIS logic in ops-setup
- **AIMMD integration**: Handled separately in aimmd-tis
- **Clear boundaries**: Each package has distinct responsibilities

See [README.md - Integration with AIMMD-TIS](README.md#integration-with-aimmd-tis)

## Architecture & Design

### Design Patterns

- **Template Method** - Base classes define setup sequence
- **Strategy** - Pluggable engines and systems
- **Configuration** - JSON-driven customization
- **Inheritance** - Extensible class hierarchy

### Class Hierarchy

```
TPSSetupBase
├── TISSetupBase
└── OpenMMTPSSetup
    ├── AmberOpenMMSetup
    │   └── HostGuestTPSSetup
    └── [Other systems]
```

See [DEVELOPMENT.md - Architecture Overview](DEVELOPMENT.md#architecture-overview)

## Documentation Files

| File | Purpose |
|------|---------|
| [README.md](README.md) | Complete user guide and API reference |
| [QUICKSTART.md](QUICKSTART.md) | Get started in 5 minutes |
| [DEVELOPMENT.md](DEVELOPMENT.md) | Architecture and extension guide |
| [REFACTORING_SUMMARY.md](REFACTORING_SUMMARY.md) | Detailed refactoring information |
| [INDEX.md](INDEX.md) | This file - Documentation index |

## Contributing

### To Add a New System

1. Create directory under `src/ops_setup/systems/examples/your_system/`
2. Implement setup classes inheriting from base classes
3. Define collective variables
4. Provide configuration templates
5. Document your system

See [DEVELOPMENT.md - Contributing](DEVELOPMENT.md#contributing-back)

### To Add a New Engine

1. Create module under `src/ops_setup/engines/`
2. Implement engine setup class extending `TPSSetupBase`
3. Implement all abstract methods
4. Write tests
5. Document engine-specific details

## Testing

### Run Tests

```bash
cd /Users/rbreeba/code/ops-setup
pytest tests/
```

### Writing Tests

See [DEVELOPMENT.md - Testing Your Implementation](DEVELOPMENT.md#testing-your-implementation)

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Import error | Run `pip install -e ".[openmm]"` in ops-setup directory |
| Missing dependencies | Install: `pip install openmm openmmtools mdtraj` |
| Configuration errors | Validate with `validate_config_keys()`, check templates |
| OpenMM platform errors | Check `Platform.getPlatformNames()` |

See [QUICKSTART.md - Troubleshooting](QUICKSTART.md#troubleshooting)

## Related Projects

- [OpenPathSampling](http://openpathsampling.org/) - Core path sampling library
- [AIMMD](https://github.com/bio-phys/aimmd) - AI-guided molecular discovery
- [AIMMD-TIS](../) - AIMMD + TIS integration

## License

GPL-3.0

## Citation

If you use ops-setup, please cite OpenPathSampling and relevant papers.

---

## Quick Links

- **Install**: `pip install -e ".[openmm]"`
- **Start**: Read [QUICKSTART.md](QUICKSTART.md)
- **Learn**: Read [README.md](README.md)
- **Extend**: Read [DEVELOPMENT.md](DEVELOPMENT.md)
- **Details**: Read [REFACTORING_SUMMARY.md](REFACTORING_SUMMARY.md)

---

**Last Updated**: January 2026  
**Version**: 0.1.0

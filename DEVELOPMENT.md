# ops-setup Development Guide

This guide explains the architecture and organization of ops-setup, and how to extend it for new systems and simulation types.

## Architecture Overview

### Core Concept

ops-setup separates **generic OPS/TPS/TIS functionality** from **system-specific implementations** through inheritance and composition.

```
Generic OPS Logic
    ↓
TPSSetupBase (abstract)
    ↓
TISSetupBase (extends TPSSetupBase)
    ↓
OpenMMTPSSetup (implements abstract methods)
    ↓
AmberOpenMMSetup (adds AMBER file support)
    ↓
System-Specific Setups (e.g., HostGuestTPSSetup)
```

### Key Design Patterns

#### 1. Template Method Pattern

Base classes define abstract methods that subclasses must implement:

```python
class TPSSetupBase:
    def __init__(self, config_path, ...):
        # Template method - defines initialization order
        self._extract_config()
        self.integrator = self._setup_integrator()  # Abstract
        # ... more setup
    
    def _setup_integrator(self):
        raise NotImplementedError("Subclasses must implement")
```

#### 2. Configuration-Driven Design

All parameters come from JSON config files:

```python
# Config is loaded and parsed
self.config = read_config(config_path)

# System-specific classes use config to customize behavior
def _setup_system(self):
    system_files = self.config.get('system_files', {})
    topology_file = system_files.get('topology_file')
```

#### 3. Inheritance for Extension

System-specific setups inherit from appropriate base class:

```python
# Example: Custom system
class MySystemTISSetup(TISSetupBase):
    def _define_states(self):
        # Custom state definitions
        pass
    
    def _setup_system(self):
        # Custom system initialization
        pass
```

## Adding a New System

### Step 1: Understand Your System

- What engine does it use? (OpenMM, Gromacs, toy model, etc.)
- What are the collective variables?
- What are the stable states?
- What files are needed? (topology, coordinates, etc.)

### Step 2: Choose Base Class

| System Type | Base Class | Location |
|------------|-----------|----------|
| OpenMM with generic topology | `OpenMMTPSSetup` | `engines/openmm_engine.py` |
| OpenMM with AMBER files | `AmberOpenMMSetup` | `engines/openmm_engine.py` |
| Custom engine | `TPSSetupBase` | `core/tps_setup.py` |
| Toy/test model | Create custom | `systems/examples/` |

### Step 3: Create System Module

Create a directory under `systems/examples/`:

```
systems/examples/my_system/
├── __init__.py
├── setup.py              # Main setup classes
├── collective_variables.py  # CV definitions
├── config_template.json  # Example configuration
└── README.md            # System-specific docs
```

### Step 4: Implement Setup Class

Example for a custom OpenMM system:

```python
# systems/examples/my_system/setup.py
from ops_setup.engines import OpenMMTPSSetup
from ops_setup.core.tis_setup import TISSetupBase
from .collective_variables import my_cv_definition

class MySystemTPSSetup(OpenMMTPSSetup):
    """Custom setup for my molecular system."""
    
    def __init__(self, config_path, resource_directory=None, **kwargs):
        self.my_cv = my_cv_definition
        super().__init__(config_path, resource_directory, **kwargs)
    
    def _setup_system(self):
        """Load custom topology and coordinates."""
        # Your custom logic here
        topology, system, positions = self._load_my_files()
        return topology, system, positions
    
    def _define_states(self):
        """Define stable states."""
        import openpathsampling as paths
        
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
    
    def _load_my_files(self):
        """Load system-specific file formats."""
        # Implementation for your file format
        pass
```

### Step 5: Define Collective Variables

Create a module for your collective variables:

```python
# systems/examples/my_system/collective_variables.py
import openpathsampling as paths

def my_distance_function(snapshot):
    """Compute a distance CV."""
    import numpy as np
    # Extract and compute distance
    return np.linalg.norm(...)

my_cv_definition = paths.CoordinateFunctionCV(
    name="my_distance",
    f=my_distance_function
).with_diskcache()
```

### Step 6: Create Configuration Template

```json
{
  "system_name": "MySystem",
  "platform_name": "CUDA",
  "UNITS": { ... },
  "Integrator_settings": { ... },
  "TPS_settings": { ... },
  "system_files": {
    "my_topology": "path/to/topology",
    "my_coordinates": "path/to/coords"
  },
  "States": {
    "stateA": 0.3,
    "stateB": 0.7
  }
}
```

### Step 7: Document Your System

Create a README explaining:
- System description
- Required files
- Configuration parameters
- Example usage
- Citations

## Extending for New Engines

### Adding a New MD Engine

If you want to support a new engine (e.g., Gromacs, NAMD):

1. Create `engines/my_engine.py`
2. Implement `MyEngineTPSSetup` extending `TPSSetupBase`
3. Implement required methods:
   - `_setup_integrator()`
   - `_setup_engine()`
   - `_setup_system()`
   - `_create_template()`
   - `_define_states()`

### Example: Custom Toy Engine

```python
# engines/toy_engine.py
from ops_setup.core.tps_setup import TPSSetupBase
import openpathsampling.engines.toy as toys

class ToyTPSSetup(TPSSetupBase):
    """TPS setup for toy models."""
    
    def _extract_config(self):
        super()._extract_config()
        # Extract toy-specific parameters
        self.toy_type = self.config.get('toy_type', 'linear')
    
    def _setup_integrator(self):
        integrator = toys.LangevinBAOABIntegrator(
            dt=0.05,
            temperature=self.temperature,
            gamma=2.5
        )
        return integrator
    
    def _setup_engine(self, integrator):
        # Toy engine setup
        pass
    
    # ... implement other abstract methods
```

## Configuration Best Practices

### 1. Organize by Hierarchy

```json
{
  "system_name": "...",
  "Integrator_settings": { ... },
  "TPS_settings": { ... },
  "TIS": {
    "Scheme": { ... },
    "interface_parameters": { ... }
  }
}
```

### 2. Use Sensible Defaults

```python
def _extract_config(self):
    self.n_frames_max = self.config.get('TPS_settings', {}).get(
        'n_frames_max', 5000  # Default value
    )
```

### 3. Validate Configuration

```python
from ops_setup.core import validate_config_keys

required_keys = ['system_name', 'platform_name']
validate_config_keys(self.config, required_keys)
```

## Testing Your Implementation

### Unit Tests

```python
# tests/test_my_system.py
import pytest
from ops_setup.systems.examples.my_system import MySystemTPSSetup

def test_my_system_initialization(tmp_path):
    config_path = tmp_path / "config.json"
    # Create test config
    
    setup = MySystemTPSSetup(config_path)
    assert setup.system is not None
    assert setup.md_engine is not None
    assert setup.states is not None

def test_states_are_valid(my_setup):
    stateA, stateB = my_setup.states
    assert stateA is not None
    assert stateB is not None
```

### Integration Tests

Test with actual path sampling:

```python
def test_tps_network_creation(my_setup):
    network = my_setup.create_network("TPS")
    assert network is not None
    
    move_scheme = my_setup.create_move_scheme(network)
    assert move_scheme is not None
```

## Common Pitfalls

1. **Hardcoded Paths**: Use `self.resource_directory` for all file paths
2. **Ignoring Units**: OpenMM requires explicit units; use `unit` module
3. **Missing Abstract Method**: Ensure all abstract methods are implemented
4. **Configuration Keys**: Use `.get()` with defaults for optional config
5. **CV Caching**: Remember to use `.with_diskcache()` for expensive CVs

## Documentation Structure

For each new system, provide:

```
systems/examples/my_system/
├── README.md              # System overview and usage
├── setup.py               # Implementation
├── collective_variables.py # CV definitions
├── config_template.json   # Example configuration
└── example_workflow.ipynb # Jupyter notebook example
```

## Integration with AIMMD-TIS

To make your system compatible with AIMMD-TIS:

1. Ensure `_define_states()` returns appropriate state volumes
2. Provide descriptor transformation function
3. Document AIMMD-specific configuration (if needed)
4. Create integration example showing both packages

Example integration:

```python
from ops_setup.systems.examples.my_system import MySystemTISSetup
from aimmdTIS import AIMMD_setup

# Setup using ops-setup
tis_setup = MySystemTISSetup(
    tps_config, tis_config, descriptor_transform
)

# Integrate with AIMMD
aimmd_setup = AIMMD_setup(
    tps_config,
    descriptor_dim,
    tis_setup.states,
    descriptor_transform=descriptor_transform
)
```

## Contributing Back

1. Follow the architecture patterns
2. Write clear docstrings
3. Add tests
4. Update documentation
5. Create PR with explanation

For questions, refer to existing system implementations or open an issue.

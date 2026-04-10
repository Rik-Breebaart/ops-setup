# TPS Setup Architecture Refactoring

## Problem
`OpenMMGromacsTPS` inherited from `TPSSetupBase` but never called `super().__init__()`, creating an awkward situation where:
- It inherited methods it didn't use
- It couldn't access utility methods like `_create_selector()`
- The inheritance was "fake" - only for code sharing, not for proper OOP design

## Solution: Mixin Architecture

### New Structure

```
TPSUtilitiesMixin          (provides common TPS utilities)
       ↑
       |
       +-- TPSSetupBase    (config-based initialization pattern)
       |
       +-- OpenMMGromacsTPS (GROMACS-specific initialization pattern)
               ↑
               |
               +-- T4LTPSSetup (T4L-specific CVs and states)
```

### Components

1. **`TPSUtilitiesMixin`** (`src/ops_setup/core/tps_utilities.py`)
   - Provides `_create_selector()` - shooting point selector creation
   - Provides `_create_velocity_modifier()` - velocity randomization for two-way shooting
   - Provides `create_move_scheme()` - move scheme creation
   - No initialization logic - pure utility methods
   - Expects `self.config` and `self.engine` (or `self.md_engine`) to exist

2. **`TPSSetupBase`** (`src/ops_setup/core/tps_setup.py`)
   - Inherits from `TPSUtilitiesMixin`
   - Config-driven initialization via `__init__(config_path)`
   - Calls abstract methods: `_setup_integrator()`, `_setup_system()`, `_create_template()`, `_define_states()`
   - Sets up `self.config`, `self.md_engine`, `self.selector` during init
   - Used by systems that fit the config-first pattern (e.g., host-guest with Amber)

3. **`OpenMMGromacsTPS`** (`src/ops_setup/engines/openmm_from_gromacs.py`)
   - Inherits from `TPSUtilitiesMixin` **only** (not from TPSSetupBase)
   - Has its own initialization pattern (wraps `OpenMMGromacs`)
   - Stores `self.config` when loaded from JSON
   - Gets utility methods from mixin without forced initialization pattern
   - Clean separation of concerns

4. **`T4LTPSSetup`** (`Projects/T4L/t4l_setup/t4l_tps_setup_class.py`)
   - Inherits from `OpenMMGromacsTPS`
   - Adds T4L-specific CVs and state definitions
   - Automatically has access to `_create_selector()` via the mixin chain

### Benefits

1. **No fake inheritance** - Classes only inherit when they actually use the parent's initialization
2. **Code reuse** - Utility methods shared via mixin without forcing initialization patterns
3. **Flexibility** - Different setup classes can have different initialization approaches
4. **Clean architecture** - Single responsibility (mixin = utilities, base = config pattern, GROMACS = wrapper pattern)
5. **Easy testing** - Mixin can be mixed into any class for testing
6. **Extensibility** - New setup patterns can mix in utilities without conforming to TPSSetupBase

### Migration Guide

If you have existing code using `OpenMMGromacsTPS`:
- **No changes needed** - it still works the same way
- Now has access to `_create_selector()` and `create_move_scheme()`
- Just ensure you pass `config_path` or set `self.config` manually

If you're creating a new TPS setup:
- **Use TPSSetupBase** if you want config-driven initialization
- **Use TPSUtilitiesMixin** if you have a custom initialization pattern
- Both give you the same utility methods

### Example Usage

```python
# Option 1: Config-driven (inherits TPSSetupBase)
class MyAmberTPS(TPSSetupBase):
    def __init__(self, config_path):
        super().__init__(config_path)  # Calls all the setup methods
    
    def _setup_system(self):
        # Implement abstract method
        ...

# Option 2: Custom init (uses mixin only)
class MyCustomTPS(TPSUtilitiesMixin):
    def __init__(self, topology, system, ...):
        self.config = {...}
        self.engine = create_engine(...)
        # Custom initialization
    
    # Can still use _create_selector(), create_move_scheme()

# Both patterns work!
setup1 = MyAmberTPS("config.json")
setup2 = MyCustomTPS(topology, system)

selector1 = setup1._create_selector(collective_variable=cv, selector_type='gaussian')
selector2 = setup2._create_selector(collective_variable=cv, selector_type='gaussian')
```

### Files Modified

- ✅ Created: `src/ops_setup/core/tps_utilities.py` (new mixin)
- ✅ Modified: `src/ops_setup/core/tps_setup.py` (now inherits from mixin, removed duplicates)
- ✅ Modified: `src/ops_setup/engines/openmm_from_gromacs.py` (now inherits from mixin only)
- ✅ No changes needed: `Projects/T4L/t4l_setup/t4l_tps_setup_class.py` (automatically benefits)

## Testing

Run the T4L test to verify everything works:
```bash
cd /home/rbreeba/Projects/T4L/scripts/tps_sandbox
python test_t4l_tps_example.py
```

The test calls `t4l._create_selector()` which now properly resolves through the mixin chain.

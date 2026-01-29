# Quick Reference: What's New in ops-setup

## New Example Scripts

### 1. Pure OpenMM TPS (No AIMMD)
**File:** `ops-setup/examples/scripts/quick_openmm_tps.py`

```bash
# Run TPS with default settings
python quick_openmm_tps.py path/to/config.json 5

# With custom output
python quick_openmm_tps.py config.json 10 \
  --storage my_tps_run.nc \
  --resources /path/to/system/files
```

**What it does:**
- Reads OpenMM configuration from JSON
- Sets up integrator, system, template
- Creates TPS network between states A and B
- Runs Monte Carlo path sampling
- Saves results to NetCDF

**Configuration needed:**
```json
{
  "system_name": "YourSystem",
  "platform_name": "CUDA",
  "Integrator_settings": { "temperature": 300, "dt": 0.001 },
  "TPS_settings": { "n_frames_max": 5000 },
  "States": { "bound": 0.3, "unbound": 0.7 }
}
```

---

### 2. Pure OpenMM TIS (No AIMMD)
**File:** `ops-setup/examples/scripts/quick_openmm_tis.py`

```bash
# Run TIS for a single interface
python quick_openmm_tis.py tps.json tis.json 0.6 5

# With custom storage
python quick_openmm_tis.py tps.json tis.json 0.8 10 \
  --storage my_tis_run_int_80.db \
  --resources /path/to/system/files
```

**What it does:**
- Reads both TPS and TIS configurations
- Sets up a single-interface TIS run
- Stores results per interface in a separate storage file
- Saves results to experimental Storage format

**Configuration needed:**
```json
TPS config (same as above) + TIS config:

{
  "TIS": {
    "Scheme": {
      "Shooting_Move": "OneWay",
      "selector": "uniform"
    },
    "interface_parameters": {
      "interfaces_forward": [0.4, 0.6, 0.8, 1.0]
    }
  }
}
```

---

## Comparison: Old vs New Approach

### Before (aimmd-tis examples):
```python
# setup_utilities.py
from TIS_AIMMD_toy_framework import TIS_AIMMD_setup, read_config
from examples.HostGuest.setup_utilities import TPS_setup, TIS_setup, AIMMD_setup

# AIMMD_TIS_run.py
TIS_utils = TIS_setup(config_path, ...)  # Embedded in aimmd-tis
AIMMD_set = AIMMD_setup(config_path, ...)
TIS_Framework = TAI.AIMMD_TIS(engine, model, ...)
```

### Now (ops-setup approach):
```python
# quick_openmm_tps.py
from ops_setup.engines.openmm_engine import OpenMMTPSSetup

# Simple and clean
tps_setup = OpenMMTPSSetup(config_path, resource_dir)
# Already has: engine, integrator, template, states, network methods
```

---

## Key Files Structure

```
ops-setup/
├── src/ops_setup/
│   ├── engines/
│   │   └── openmm_engine.py          ← Core OpenMM setup classes
│   ├── core/
│   │   ├── tps_setup.py              ← Base TPS class
│   │   ├── tis_setup.py              ← Base TIS class
│   │   └── config_reader.py          ← JSON config handling
│   └── systems/
│       └── examples/toy_systems/     ← Toy potential systems
│
└── examples/
    ├── scripts/
    │   ├── quick_openmm_tps.py       ← NEW: Pure OpenMM TPS
    │   ├── quick_openmm_tis.py       ← NEW: Pure OpenMM TIS
    │   ├── quick_tps_toy.py          ← Toy systems TPS
    │   └── quick_tis_toy.py          ← Toy systems TIS
    └── config_files/
        ├── TPS_template.json
        ├── TIS_template.json
        └── ... (AIMMD templates coming soon)
```

---

## Next: aimmd-tis Integration (Planned)

**When approved, I'll create:**

```
aimmd-tis/
├── src/aimmdTIS/
│   └── openmm_setup.py               ← NEW: AIMMD + OpenMM classes
│       └── OpenMMTPSAIMDDSetup(OpenMMTPSSetup)
│       └── OpenMMTISAIMDDSetup(OpenMMTISSetup)
│
├── examples/AIMMD_TIS_openmm_run_scripts/
│   ├── aimmd_openmm_tps_setup.py    ← NEW: Simplified setup
│   ├── aimmd_openmm_tis_setup.py    ← NEW: Simplified setup
│   ├── aimmd_openmm_tps_run.py      ← NEW: Cleaner TPS runner
│   ├── aimmd_openmm_tis_run.py      ← NEW: Cleaner TIS runner
│   └── setup_utilities.py            ← OLD (deprecated)
```

---

## Decision Points for User

Before implementing Phase 2 (aimmd-tis changes), confirm:

1. **Inherit from ops-setup or use utilities?**
   - Recommend: Full inheritance (cleaner)

2. **Keep setup_utilities.py or remove?**
   - Recommend: Keep as deprecated, mark in code

3. **Single or separate config for AIMMD settings?**
   - Recommend: Single JSON with optional AIMMD section

4. **Support multiple systems?**
   - Recommend: Alanine dipeptide + host-guest templates

5. **Backward compatibility timeline?**
   - Recommend: Keep old scripts working for 1 version

---

## For More Details

**See these documents:**

1. **COMPREHENSIVE_MIGRATION_PLAN.md**
   - Full technical plan (40+ sections)
   - Detailed phase breakdown
   - Known challenges & solutions
   - Implementation timeline

2. **IMPLEMENTATION_SUMMARY.md**
   - Overview of completed work
   - Next steps with decisions needed
   - Architecture overview

---

## Example: From Configuration to Running Simulation

### Step 1: Create config file (my_tps.json)
```json
{
  "system_name": "AlanineDipeptide",
  "platform_name": "CUDA",
  "UNITS": {
    "size_unit": "nanometer",
    "temp_unit": "kelvin",
    "time_unit": "picosecond"
  },
  "Integrator_settings": {
    "temperature": 300,
    "dt": 0.002,
    "friction": 1.0
  },
  "TPS_settings": {
    "n_frames_max": 5000,
    "n_steps_per_frame": 1,
    "shooting_scheme": "TwoWay"
  },
  "States": {
    "bound": -100,
    "unbound": 100
  }
}
```

### Step 2: Run simulation
```bash
python quick_openmm_tps.py my_tps.json 10 \
  --storage tps_results.nc \
  --resources ./system_files
```

### Step 3: Analyze results
```python
import openpathsampling as paths

storage = paths.Storage("tps_results.nc")
print(f"Steps: {len(storage.steps)}")
print(f"Engine: {storage.engine}")
print(f"Network: {storage.network}")

# Access all data from storage
for step in storage.steps:
    traj = step.active[0].trajectory
    print(f"Trajectory length: {len(traj)}")
```

---

## Common Issues & Solutions

### Issue: "System resource files not found"
**Solution:** Ensure topology/coordinate files are in `--resources` directory

### Issue: "No initial trajectory generated"
**Solution:** 
- Check integrator parameters (dt, temperature)
- Ensure system setup is correct
- Provide pre-equilibrated structure

### Issue: "TPS acceptance rate too low"
**Solution:**
- Increase n_steps_per_frame
- Adjust shooting point selector
- Use different TwoWay/OneWay scheme

---

## Production Tips

1. **GPU Usage:** Set `platform_name: "CUDA"` for speed
2. **Long Runs:** Use HPC submission scripts
3. **Parallel:** Different interface values in separate jobs for TIS
4. **Checkpoint:** Monitor *.nc or *.db files regularly
5. **Analysis:** Use OPS built-in tools for trajectory analysis


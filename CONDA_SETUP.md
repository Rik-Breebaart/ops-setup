# Setting up Conda Environments

This guide explains how to create and activate conda environments for ops-setup and aimmd-tis.

## Quick Start

### For ops-setup Only (TPS/TIS without AIMMD)

```bash
# Create environment from file
cd /Users/rbreeba/code/ops-setup
conda env create -f environment.yml

# Activate environment
conda activate ops-setup

# Install ops-setup in development mode
pip install -e ".[openmm]"

# Verify installation
python -c "from ops_setup.systems.examples.host_guest import HostGuestTPSSetup; print('✓ ops-setup ready')"
```

### For aimmd-tis (TPS/TIS with AIMMD learning)

```bash
# Create environment from file
cd /Users/rbreeba/code/aimmd-tis
conda env create -f environment.yml

# Activate environment
conda activate aimmd-tis

# Install ops-setup (dependency)
pip install -e /Users/rbreeba/code/ops-setup[openmm]

# Install aimmd (if not already installed)
pip install -e /Users/rbreeba/code/aimmd

# Install aimmd-tis
pip install -e .

# Verify installation
python -c "from aimmdTIS import AIMMD_TIS; print('✓ aimmd-tis ready')"
```

---

## Detailed Instructions

### Option 1: Using Conda Environment Files

#### For ops-setup

```bash
# Step 1: Navigate to ops-setup directory
cd /Users/rbreeba/code/ops-setup

# Step 2: Create environment from environment.yml
conda env create -f environment.yml

# Step 3: Activate environment
conda activate ops-setup

# Step 4: Install ops-setup in editable mode
pip install -e ".[openmm]"

# Step 5: Verify installation
python << 'EOF'
import ops_setup
import openpathsampling as paths
print(f"✓ ops-setup v{ops_setup.__version__}")
print(f"✓ OpenPathSampling installed")
EOF
```

#### For aimmd-tis

```bash
# Step 1: Navigate to aimmd-tis directory
cd /Users/rbreeba/code/aimmd-tis

# Step 2: Create environment from environment.yml
conda env create -f environment.yml

# Step 3: Activate environment
conda activate aimmd-tis

# Step 4: Install ops-setup (required dependency)
pip install -e /Users/rbreeba/code/ops-setup[openmm]

# Step 5: Install aimmd package
pip install -e /Users/rbreeba/code/aimmd

# Step 6: Install aimmd-tis in editable mode
pip install -e .

# Step 7: Verify installation
python << 'EOF'
import ops_setup
import aimmd
import aimmdTIS
print("✓ ops-setup installed")
print("✓ aimmd installed")
print("✓ aimmd-tis installed")
EOF
```

---

### Option 2: Creating Environments Manually

#### For ops-setup

```bash
# Create environment with specific Python version
conda create -n ops-setup python=3.10 -c conda-forge -c defaults

# Activate it
conda activate ops-setup

# Install core dependencies
conda install -c conda-forge numpy scipy matplotlib jupyter ipython pytest

# Install OpenPathSampling
conda install -c conda-forge openpathsampling

# Install OpenMM stack
conda install -c conda-forge openmm openmmtools mdtraj

# Install ops-setup
cd /Users/rbreeba/code/ops-setup
pip install -e ".[openmm]"
```

#### For aimmd-tis

```bash
# Create environment with specific Python version
conda create -n aimmd-tis python=3.10 -c conda-forge -c defaults

# Activate it
conda activate aimmd-tis

# Install scientific computing
conda install -c conda-forge numpy scipy matplotlib jupyter ipython pytest

# Install OpenPathSampling
conda install -c conda-forge openpathsampling

# Install OpenMM stack
conda install -c conda-forge openmm openmmtools mdtraj

# Install PyTorch (for AIMMD machine learning)
conda install -c conda-forge pytorch::pytorch pytorch::pytorch-cuda=11.8

# Install aimmd dependencies
conda install -c conda-forge h5py networkx pyyaml

# Install packages from your repositories
pip install -e /Users/rbreeba/code/ops-setup[openmm]
pip install -e /Users/rbreeba/code/aimmd
pip install -e /Users/rbreeba/code/aimmd-tis
```

---

## Conda Environment Management

### View All Environments

```bash
conda env list
```

### Activate Environment

```bash
conda activate ops-setup
# or
conda activate aimmd-tis
```

### Deactivate Environment

```bash
conda deactivate
```

### Remove Environment

```bash
conda remove -n ops-setup --all
# or
conda remove -n aimmd-tis --all
```

### Update Environment

```bash
# Update from environment file
conda env update -f environment.yml --prune

# Or update specific packages
conda install -c conda-forge numpy scipy --update-all
```

### Export Environment (Create backup)

```bash
# Save current environment
conda env export -n ops-setup > ops-setup-backup.yml
conda env export -n aimmd-tis > aimmd-tis-backup.yml
```

### Clone Environment

```bash
# Clone existing environment
conda create -n ops-setup-dev --clone ops-setup
```

---

## Troubleshooting

### Issue: "conda: command not found"

**Solution**: Install Miniconda or Anaconda
```bash
# Check if conda is installed
conda --version

# If not, install Miniconda
# Download from: https://docs.conda.io/en/latest/miniconda.html
```

### Issue: Environment creation fails

**Solution**: Update conda first
```bash
conda update -n base -c defaults conda
```

### Issue: Package not found

**Solution**: Add conda-forge channel
```bash
conda config --add channels conda-forge
conda config --set channel_priority flexible
```

### Issue: "Module not found" after environment creation

**Solution**: Ensure pip packages are installed
```bash
conda activate your-env
pip install -e /path/to/package[extras]
```

### Issue: PyTorch not installing correctly

**Solution**: Be specific about CUDA version
```bash
# For CUDA 11.8
conda install pytorch torchvision torchaudio pytorch-cuda=11.8 -c pytorch -c nvidia

# For CPU-only
conda install pytorch torchvision torchaudio cpuonly -c pytorch
```

---

## Verification Scripts

### Test ops-setup

```bash
conda activate ops-setup
python << 'EOF'
print("Testing ops-setup installation...")

# Test imports
from ops_setup.core import TPSSetupBase, TISSetupBase, read_config
from ops_setup.engines import AmberOpenMMSetup
from ops_setup.systems.examples.host_guest import HostGuestTPSSetup
from ops_setup.utils import create_parser
import openpathsampling as paths

print("✓ ops_setup.core imports work")
print("✓ ops_setup.engines imports work")
print("✓ ops_setup.systems imports work")
print("✓ ops_setup.utils imports work")
print("✓ OpenPathSampling available")
print("\n✅ ops-setup is ready to use!")
EOF
```

### Test aimmd-tis

```bash
conda activate aimmd-tis
python << 'EOF'
print("Testing aimmd-tis installation...")

# Test ops-setup
from ops_setup.systems.examples.host_guest import HostGuestTPSSetup
print("✓ ops-setup available")

# Test aimmd
import aimmd
from aimmd.pytorch import TIS_EEScalePytorchRCModel
print("✓ aimmd available")

# Test aimmd-tis
import aimmdTIS
from aimmdTIS import AIMMD_TIS
print("✓ aimmd-tis available")

print("\n✅ All packages ready for AIMMD-TIS!")
EOF
```

---

## Recommended Workflow

### Development Setup

If you're developing ops-setup and/or aimmd-tis:

```bash
# Create separate environments for development
conda env create -f /Users/rbreeba/code/ops-setup/environment.yml -n ops-setup-dev
conda env create -f /Users/rbreeba/code/aimmd-tis/environment.yml -n aimmd-tis-dev

# Install in editable mode with all extras
conda activate ops-setup-dev
pip install -e "/Users/rbreeba/code/ops-setup[openmm,dev]"

conda activate aimmd-tis-dev
pip install -e "/Users/rbreeba/code/ops-setup[openmm,dev]"
pip install -e "/Users/rbreeba/code/aimmd[dev]"
pip install -e "/Users/rbreeba/code/aimmd-tis[dev]"
```

### User Setup

If you're just using the packages:

```bash
# Simple, minimal environment
conda env create -f /Users/rbreeba/code/ops-setup/environment.yml -n ops-setup
conda activate ops-setup
pip install /Users/rbreeba/code/ops-setup[openmm]
```

---

## Environment.yml File Locations

- **ops-setup**: `/Users/rbreeba/code/ops-setup/environment.yml`
- **aimmd-tis**: `/Users/rbreeba/code/aimmd-tis/environment.yml`

Both files are version-controlled with the packages, so you can always recreate identical environments.

---

## Tips and Best Practices

### 1. Keep Environments Separate
- Use different environments for different projects
- Prevents dependency conflicts
- Easy to test multiple versions

### 2. Export Environment After Installing Packages
```bash
conda env export > my-env-backup.yml
```

### 3. Use `--prune` When Updating
```bash
conda env update -f environment.yml --prune
```
Removes packages no longer in the file.

### 4. Create Minimal Environments
Remove unused packages to save space:
```bash
conda clean --all
```

### 5. Document Your Environment
```bash
# List packages with versions
conda list --explicit > env-explicit.txt
```

---

## Getting Help

```bash
# Get conda help
conda help

# Get info about specific command
conda create --help

# List available environments
conda env list

# Get environment info
conda info
```

---

## Summary

| Task | Command |
|------|---------|
| Create from file | `conda env create -f environment.yml` |
| Activate | `conda activate env-name` |
| Deactivate | `conda deactivate` |
| List all | `conda env list` |
| Remove | `conda remove -n env-name --all` |
| Install package | `conda install package-name` |
| Update all | `conda update --all` |
| Export | `conda env export > file.yml` |
| Clone | `conda create -n new-name --clone old-name` |

For more information, see [Conda Documentation](https://docs.conda.io/)

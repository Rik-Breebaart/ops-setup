#!/usr/bin/env python
"""
Quick TPS Example with OpenMM

This script demonstrates how to quickly set up and run a basic TPS simulation
using OpenMM with the ops-setup configuration framework.

This example uses a simple Alanine dipeptide system (or any system you configure).

Usage:
    python quick_openmm_tps.py [config_file] [n_steps]

Examples:
    python quick_openmm_tps.py tps_config.json 5
    python quick_openmm_tps.py ../config_files/TPS_with_AIMMD_template.json 10
"""

import sys
import argparse
import numpy as np
import openpathsampling as paths
from pathlib import Path

try:
    from ops_setup.engines.openmm_engine import OpenMMTPSSetup
except ImportError:
    raise ImportError(
        "ops_setup is required. Please install from the ops-setup package."
    )


def run_quick_openmm_tps(config_file, n_steps=5, storage_file=None, 
                          resource_directory=None):
    """
    Run a quick TPS simulation with OpenMM.
    
    Parameters
    ----------
    config_file : str or Path
        Path to the JSON configuration file.
    n_steps : int
        Number of MC steps to run (default: 5).
    storage_file : str, optional
        Path to save NetCDF storage. Default: f"openmm_tps_{system_name}.nc"
    resource_directory : str or Path, optional
        Directory containing system resource files (topology, coordinates, etc.).
        Default uses directory of config file.
    
    Returns
    -------
    None
    """
    
    config_file = Path(config_file)
    
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_file}")
    
    # Default resource directory is the config directory
    if resource_directory is None:
        resource_directory = config_file.parent
    else:
        resource_directory = Path(resource_directory)
    
    print(f"\n{'='*70}")
    print(f"Quick TPS Simulation with OpenMM")
    print(f"{'='*70}\n")
    
    # Create OpenMM TPS setup
    print(f"Creating OpenMM TPS setup from configuration...")
    print(f"  Config file: {config_file}")
    print(f"  Resource directory: {resource_directory}\n")
    
    try:
        tps_setup = OpenMMTPSSetup(
            config_path=config_file,
            resource_directory=resource_directory,
            print_config_flag=True
        )
    except Exception as e:
        print(f"ERROR: Failed to create OpenMM TPS setup")
        print(f"  {type(e).__name__}: {e}")
        raise
    
    print(f"\n  System: {tps_setup.system_name}")
    print(f"  Platform: {tps_setup.platform_name}")
    print(f"  Engine: {tps_setup.md_engine.name}")
    print(f"  Max frames: {tps_setup.n_frames_max}")
    print(f"  Steps per frame: {tps_setup.n_steps_per_frame}")
    
    # Set storage file name
    if storage_file is None:
        storage_file = f"openmm_tps_{tps_setup.system_name}.nc"
    
    storage_file = Path(storage_file)
    
    # Create initial trajectory
    print(f"\nCreating initial trajectory...")
    paths.PathMover.engine = tps_setup.md_engine
    
    # Generate initial trajectory by shooting between states
    try:
        # Attempt to generate trajectory from equilibration between states
        print(f"  Shooting path from state A to state B...")
        n_snapshots = tps_setup.n_frames_max // 10  # Use reasonable initial path length
        
        # Get initial snapshot by running short trajectory
        init_snap = tps_setup.md_engine.current_snapshot
        traj_list = [init_snap]
        
        # Run short trajectory to get initial conditions
        for _ in range(n_snapshots):
            snap = tps_setup.md_engine.step(init_snap)
            traj_list.append(snap)
            init_snap = snap
        
        init_traj = paths.Trajectory(traj_list)
        print(f"  Initial trajectory: {len(init_traj)} snapshots")
        
    except Exception as e:
        print(f"  WARNING: Could not auto-generate initial trajectory: {e}")
        print(f"  Please provide initial trajectory or check trajectory generation setup")
        raise
    
    # Create network and move scheme
    print(f"\nSetting up TPS network and move scheme...")
    network = tps_setup.create_network("TPS")
    print(f"  Network created: {type(network).__name__}")
    
    move_scheme = tps_setup.create_move_scheme(network, tps_setup.shooting_scheme)
    print(f"  Move scheme: {tps_setup.shooting_scheme}")
    print(f"  Selector: {tps_setup.tps_selector}")
    
    # Create storage
    print(f"\nCreating storage: {storage_file}")
    storage = paths.Storage(str(storage_file), "w", template=tps_setup.template)
    storage.save(tps_setup.md_engine)
    storage.save(move_scheme)
    storage.save(network)
    
    # Create initial conditions
    print(f"\nPreparing initial conditions...")
    initial_conditions = move_scheme.initial_conditions_from_trajectories(init_traj)
    try:
        initial_conditions.sanity_check()
        print(f"  Initial conditions prepared and validated")
    except Exception as e:
        print(f"  WARNING: Initial conditions sanity check failed: {e}")
        print(f"  Continuing anyway...")
    
    # Run TPS
    print(f"\nRunning TPS simulation for {n_steps} MC steps...")
    print(f"{'  Step':<8} {'Acc Rate':<12} {'Traj Length':<15}")
    print(f"  {'-'*35}")
    
    try:
        sampler = paths.PathSampling(storage, move_scheme, initial_conditions)
        sampler.run(n_steps)
    except Exception as e:
        print(f"\nERROR during TPS simulation: {type(e).__name__}: {e}")
        storage.close()
        raise
    
    # Summary
    print(f"\n{'='*70}")
    print(f"TPS Simulation Complete!")
    print(f"{'='*70}")
    print(f"  Total MC steps: {len(storage.steps)}")
    print(f"  Storage file: {storage_file}")
    
    # Calculate acceptance rate
    if hasattr(move_scheme, 'acceptance_rate'):
        print(f"  Overall acceptance rate: {move_scheme.acceptance_rate:.1%}")
    
    # Analyze trajectories
    n_accepted = 0
    traj_lengths = []
    
    for step in storage.steps:
        if step.active[0].is_accepted:
            n_accepted += 1
        traj_lengths.append(len(step.active[0].trajectory))
    
    if traj_lengths:
        print(f"  Accepted trajectories: {n_accepted}/{len(storage.steps)}")
        print(f"  Trajectory length stats:")
        print(f"    Min: {min(traj_lengths)}, Max: {max(traj_lengths)}, "
              f"Avg: {np.mean(traj_lengths):.1f}")
    
    print(f"\nTo load and analyze results:")
    print(f"  import openpathsampling as paths")
    print(f"  storage = paths.Storage('{storage_file}')")
    print(f"  # Access trajectories, engine, network, move_scheme, etc.")
    print()
    
    storage.close()


def main():
    """Parse command line arguments and run TPS."""
    parser = argparse.ArgumentParser(
        description="Quick TPS simulation with OpenMM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python quick_openmm_tps.py tps_config.json 5
  python quick_openmm_tps.py ../config_files/TPS_template.json 10 \\
    --storage tps_results.nc --resources /path/to/resources
        """
    )
    
    parser.add_argument('config', help='Path to TPS configuration JSON file')
    parser.add_argument('n_steps', type=int, nargs='?', default=5,
                        help='Number of MC steps to run (default: 5)')
    parser.add_argument('-s', '--storage', help='Output storage file path')
    parser.add_argument('-r', '--resources', help='Path to system resource files')
    
    args = parser.parse_args()
    
    try:
        run_quick_openmm_tps(
            config_file=args.config,
            n_steps=args.n_steps,
            storage_file=args.storage,
            resource_directory=args.resources
        )
    except Exception as e:
        print(f"\nFATAL ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

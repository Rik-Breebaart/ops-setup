#!/usr/bin/env python
"""
Quick TIS Example with OpenMM

This script demonstrates how to quickly set up and run a TIS (Transition Interface 
Sampling) simulation using OpenMM with the ops-setup configuration framework.

TIS uses interfaces to explore the transition region more efficiently than TPS.

Usage:
    python quick_openmm_tis.py [tps_config] [tis_config] [interface_value] [n_steps]

Examples:
    python quick_openmm_tis.py tps_config.json tis_config.json 0.6 5
    python quick_openmm_tis.py ../config_files/TPS_template.json \
                               ../config_files/TIS_template.json 0.8 10
"""

import sys
import argparse
import numpy as np
import openpathsampling as paths
from pathlib import Path

try:
    from ops_setup.engines.openmm_engine import OpenMMTISSetup
except ImportError:
    raise ImportError(
        "ops_setup is required. Please install from the ops-setup package."
    )


def run_quick_openmm_tis(tps_config_file, tis_config_file, interface_value=0.6,
                         n_steps=5, storage_file=None, resource_directory=None):
    """
    Run a quick TIS simulation with OpenMM.
    
    Parameters
    ----------
    tps_config_file : str or Path
        Path to the TPS JSON configuration file.
    tis_config_file : str or Path
        Path to the TIS JSON configuration file.
    interface_value : float
        Single interface value to run (default: 0.6).
    n_steps : int
        Number of MC steps to run (default: 5).
    storage_file : str, optional
        Path to save storage. Default: f"openmm_tis_{system_name}.db"
    resource_directory : str or Path, optional
        Directory containing system resource files.
        Default uses TPS config directory.
    
    Returns
    -------
    None
    """
    
    tps_config_file = Path(tps_config_file)
    tis_config_file = Path(tis_config_file)
    
    if not tps_config_file.exists():
        raise FileNotFoundError(f"TPS config file not found: {tps_config_file}")
    if not tis_config_file.exists():
        raise FileNotFoundError(f"TIS config file not found: {tis_config_file}")
    
    # Default resource directory
    if resource_directory is None:
        resource_directory = tps_config_file.parent
    else:
        resource_directory = Path(resource_directory)
    
    print(f"\n{'='*70}")
    print(f"Quick TIS Simulation with OpenMM")
    print(f"{'='*70}\n")
    
    # Create OpenMM TIS setup
    print(f"Creating OpenMM TIS setup from configuration...")
    print(f"  TPS Config: {tps_config_file}")
    print(f"  TIS Config: {tis_config_file}")
    print(f"  Resources: {resource_directory}\n")
    
    try:
        tis_setup = OpenMMTISSetup(
            tps_config_path=tps_config_file,
            tis_config_path=tis_config_file,
            resource_directory=resource_directory,
            print_config_flag=True
        )
    except Exception as e:
        print(f"ERROR: Failed to create OpenMM TIS setup")
        print(f"  {type(e).__name__}: {e}")
        raise
    
    print(f"\n  System: {tis_setup.system_name}")
    print(f"  Platform: {tis_setup.platform_name}")
    print(f"  Engine: {tis_setup.md_engine.name}")
    print(f"  Interfaces (forward): {tis_setup.interface_values_forward}")
    print(f"  Interfaces (backward): {tis_setup.interface_values_backward}")
    print(f"  Interface for this run: {interface_value}")
    
    # Set storage file name
    if storage_file is None:
        interface_indicator = int(round(interface_value * 100))
        storage_file = f"openmm_tis_{tis_setup.system_name}_int_{interface_indicator}.db"
    
    storage_file = Path(storage_file)
    
    # Create initial trajectory
    print(f"\nCreating initial trajectory...")
    paths.PathMover.engine = tis_setup.md_engine
    
    try:
        # Generate initial trajectory
        print(f"  Shooting path from state A to state B...")
        n_snapshots = tis_setup.n_frames_max // 10
        
        init_snap = tis_setup.md_engine.current_snapshot
        traj_list = [init_snap]
        
        for _ in range(n_snapshots):
            snap = tis_setup.md_engine.step(init_snap)
            traj_list.append(snap)
            init_snap = snap
        
        init_traj = paths.Trajectory(traj_list)
        print(f"  Initial trajectory: {len(init_traj)} snapshots")
        
    except Exception as e:
        print(f"  WARNING: Could not auto-generate initial trajectory: {e}")
        print(f"  Please provide initial trajectory or check setup")
        raise
    
    # Create network and move scheme
    print(f"\nSetting up TIS network and move scheme...")
    
    # Create interface set
    cv = tis_setup._get_collective_variable()  # Needs to be implemented in TIS setup
    interface_set = tis_setup.create_interface_set(
        cv,
        interface_value,
        direction="forward"
    )
    
    # Create TIS network
    network = tis_setup.create_tis_network(interface_set, direction="forward")
    print(f"  Network created: {type(network).__name__}")
    print(f"  Number of ensembles: {len(network.ensembles)}")
    
    move_scheme = tis_setup.create_move_scheme(network, tis_setup.shooting_move)
    print(f"  Move scheme: {tis_setup.shooting_move}")
    print(f"  Selector: {tis_setup.tps_selector}")
    
    # Create storage
    print(f"\nCreating storage: {storage_file}")
    from openpathsampling.experimental.storage import Storage
    storage = Storage(str(storage_file), "w")
    storage.save(tis_setup.template)
    storage.save(tis_setup.md_engine)
    storage.save(move_scheme)
    storage.save(network)
    
    # Create initial conditions
    print(f"\nPreparing initial conditions...")
    initial_conditions = move_scheme.initial_conditions_from_trajectories(init_traj)
    try:
        initial_conditions.sanity_check()
        print(f"  Initial conditions prepared and validated")
    except Exception as e:
        print(f"  WARNING: Sanity check failed: {e}")
    
    # Run TIS
    print(f"\nRunning TIS simulation for {n_steps} MC steps...")
    print(f"{'  Step':<8} {'Acc Rate':<12} {'Ensembles':<12}")
    print(f"  {'-'*32}")
    
    try:
        sampler = paths.PathSampling(storage, move_scheme, initial_conditions)
        sampler.run(n_steps)
    except Exception as e:
        print(f"\nERROR during TIS simulation: {type(e).__name__}: {e}")
        storage.close()
        raise
    
    # Summary
    print(f"\n{'='*70}")
    print(f"TIS Simulation Complete!")
    print(f"{'='*70}")
    print(f"  Total MC steps: {len(storage.steps)}")
    print(f"  Storage file: {storage_file}")
    
    if hasattr(move_scheme, 'acceptance_rate'):
        print(f"  Overall acceptance rate: {move_scheme.acceptance_rate:.1%}")
    
    # Ensemble statistics
    print(f"\nEnsemble Statistics:")
    print(f"{'  Ensemble':<20} {'Samples':<12}")
    print(f"  {'-'*32}")
    
    for i, ensemble in enumerate(network.ensembles):
        if i < len(move_scheme.movers):
            mover = move_scheme.movers[i]
            if hasattr(mover, 'statistics'):
                stats = mover.statistics
                n_trials = getattr(stats, 'n_trials', 0)
            else:
                n_trials = 0
            print(f"  Ensemble {i:<14} {n_trials:<12}")
    
    # Trajectory statistics
    traj_lengths = []
    for step in storage.steps:
        if step.active:
            traj_lengths.append(len(step.active[0].trajectory))
    
    if traj_lengths:
        print(f"\nTrajectory Statistics:")
        print(f"  Min length: {min(traj_lengths)}")
        print(f"  Max length: {max(traj_lengths)}")
        print(f"  Avg length: {np.mean(traj_lengths):.1f}")
        print(f"  Std length: {np.std(traj_lengths):.1f}")
    
    print(f"\nTo load and analyze results:")
    print(f"  from openpathsampling.experimental.storage import Storage")
    print(f"  storage = Storage('{storage_file}')")
    print(f"  # Access trajectories, engine, network, move_scheme, etc.")
    print()
    
    storage.close()


def main():
    """Parse command line arguments and run TIS."""
    parser = argparse.ArgumentParser(
        description="Quick TIS simulation with OpenMM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python quick_openmm_tis.py tps_config.json tis_config.json 0.6 5
    python quick_openmm_tis.py ../config_files/TPS_template.json \
                                                         ../config_files/TIS_template.json 0.8 10 \
                                                         --storage tis_results_int_80.db --resources /path/resources
        """
    )
    
    parser.add_argument('tps_config', help='Path to TPS configuration JSON file')
    parser.add_argument('tis_config', help='Path to TIS configuration JSON file')
    parser.add_argument('interface_value', type=float, nargs='?', default=0.6,
                        help='Single interface value to run (default: 0.6)')
    parser.add_argument('n_steps', type=int, nargs='?', default=5,
                        help='Number of MC steps to run (default: 5)')
    parser.add_argument('-s', '--storage', help='Output storage file path')
    parser.add_argument('-r', '--resources', help='Path to system resource files')
    
    args = parser.parse_args()
    
    try:
        run_quick_openmm_tis(
            tps_config_file=args.tps_config,
            tis_config_file=args.tis_config,
            interface_value=args.interface_value,
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

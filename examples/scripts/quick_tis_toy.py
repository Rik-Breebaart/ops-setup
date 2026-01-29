#!/usr/bin/env python
"""
Quick TIS Example with Toy Potentials

This script demonstrates how to quickly set up and run a basic TIS simulation
using the ops-setup toy systems without any AIMMD components.

TIS uses interfaces to explore the transition region more efficiently than TPS.

Usage:
    python quick_tis_toy.py [potential_name] [interface_value] [n_steps]

Examples:
    python quick_tis_toy.py potential_1 0.4 5      # 2D potential, single interface
    python quick_tis_toy.py potential_2 0.6 10     # 2D with barrier shift
"""

import sys
import numpy as np
import openpathsampling as paths
from pathlib import Path

# Import from ops-setup
from ops_setup.systems.examples.toy_systems import (
    ToyTISSetup,
    potential_1,
    potential_2,
)


def run_quick_tis(potential_name="potential_1", interface_value=0.4, n_steps=5, storage_file=None):
    """
    Run a quick TIS simulation with a toy potential.
    
    Parameters
    ----------
    potential_name : str
        Name of the toy potential to use
        Options: 'potential_1' (2D), 'potential_2' (2D with shift)
    interface_value : float
        Single interface value to run (default: 0.4)
    n_steps : int
        Number of MC steps to run (default: 5)
    storage_file : str, optional
        Path to save NetCDF storage. Default: f"tis_{potential_name}.nc"
    
    Returns
    -------
    None
    """
    
    # Validate potential name
    valid_potentials = ["potential_1", "potential_2"]
    if potential_name not in valid_potentials:
        raise ValueError(
            f"Unknown potential for TIS: {potential_name}. "
            f"Valid options: {valid_potentials} (2D potentials only)"
        )
    
    if storage_file is None:
        interface_indicator = int(round(interface_value * 100))
        storage_file = f"tis_{potential_name}_int_{interface_indicator}.nc"
    
    print(f"\n{'='*60}")
    print(f"Quick TIS Simulation with {potential_name}")
    print(f"{'='*60}\n")
    
    # Create TIS setup
    print(f"Creating TIS setup for {potential_name}...")
    tis_setup = ToyTISSetup(
        potential_name=potential_name,
        potential_kwargs={},
        integrator_params={
            'dt': 0.05,
            'temperature': 1.0,
            'gamma': 2.5
        },
        interface_values=[interface_value]
    )
    
    print(f"  System: {tis_setup.system_name}")
    print(f"  Engine: {tis_setup.md_engine.name}")
    print(f"  Interface: {interface_value}")
    print(f"  Order parameter: x-coordinate")
    
    # Create initial trajectory
    print(f"\nCreating initial trajectory...")
    paths.PathMover.engine = tis_setup.md_engine
    
    init_traj = paths.Trajectory(
        tis_setup.pes.simple_initial_path(200, tis_setup.md_engine)
    )
    print(f"  Initial trajectory: {len(init_traj)} snapshots")
    
    # Create network and move scheme
    print(f"\nSetting up TIS network and move scheme...")
    network = tis_setup.create_network("TIS")
    move_scheme = tis_setup.create_move_scheme(network, "OneWay")
    
    print(f"  Number of ensembles: {len(network.ensembles)}")
    
    # Create storage
    print(f"\nCreating storage: {storage_file}")
    storage = paths.Storage(storage_file, "w", template=tis_setup.template)
    storage.save(tis_setup.md_engine)
    storage.save(move_scheme)
    storage.save(network)
    
    # Create initial conditions
    print(f"\nPreparing initial conditions...")
    initial_conditions = move_scheme.initial_conditions_from_trajectories(init_traj)
    initial_conditions.sanity_check()
    print(f"  Initial conditions prepared and validated")
    
    # Run TIS
    print(f"\nRunning TIS simulation for {n_steps} MC steps...")
    print(f"{'  Step':<8} {'Acc Rate':<12}")
    print(f"  {'-'*20}")
    
    sampler = paths.PathSampling(storage, move_scheme, initial_conditions)
    sampler.run(n_steps)
    
    # Summary
    print(f"\n{'='*60}")
    print(f"TIS Simulation Complete!")
    print(f"{'='*60}")
    print(f"  Total MC steps: {len(storage.steps)}")
    print(f"  Storage file: {storage_file}")
    print(f"  Overall acceptance rate: {move_scheme.acceptance_rate:.1%}")
    
    # Analyze trajectories by ensemble
    print(f"\nEnsemble Statistics:")
    print(f"{'  Ensemble':<20} {'Samples':<10} {'Acc Rate':<12}")
    print(f"  {'-'*42}")
    
    for i, ensemble in enumerate(network.ensembles):
        ensemble_stats = move_scheme.movers[i].statistics
        print(f"  Ensemble {i:<14} {ensemble_stats.n_trials:<10} "
              f"{ensemble_stats.acceptance_rate:.1%}" if hasattr(ensemble_stats, 'acceptance_rate') else "")
    
    # Trajectory length statistics
    traj_lengths = [
        len(step.active[0].trajectory) 
        for step in storage.steps
    ]
    print(f"\nTrajectory Statistics:")
    print(f"  Min length: {min(traj_lengths)}")
    print(f"  Max length: {max(traj_lengths)}")
    print(f"  Avg length: {np.mean(traj_lengths):.1f}")
    print(f"  Std length: {np.std(traj_lengths):.1f}")
    
    print(f"\nTo load and analyze results:")
    print(f"  import openpathsampling as paths")
    print(f"  storage = paths.Storage('{storage_file}')")
    print(f"  # Access trajectories, ensembles, network, etc.")
    print()
    
    storage.close()


def main():
    """Parse command line arguments and run TIS."""
    
    potential_name = "potential_1"  # Default
    interface_value = 0.4  # Default
    n_steps = 5  # Default
    
    if len(sys.argv) > 1:
        potential_name = sys.argv[1]
    
    if len(sys.argv) > 2:
        try:
            interface_value = float(sys.argv[2])
        except ValueError:
            print(f"Error: interface_value must be a float, got '{sys.argv[2]}'")
            sys.exit(1)

    if len(sys.argv) > 3:
        try:
            n_steps = int(sys.argv[3])
        except ValueError:
            print(f"Error: n_steps must be an integer, got '{sys.argv[3]}'")
            sys.exit(1)
    
    try:
        run_quick_tis(potential_name, interface_value, n_steps)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

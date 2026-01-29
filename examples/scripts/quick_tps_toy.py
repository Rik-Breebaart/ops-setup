#!/usr/bin/env python
"""
Quick TPS Example with Toy Potentials

This script demonstrates how to quickly set up and run a basic TPS simulation
using the ops-setup toy systems without any AIMMD components.

Usage:
    python quick_tps_toy.py [potential_name] [n_steps]

Examples:
    python quick_tps_toy.py potential_0 5          # 1D potential
    python quick_tps_toy.py potential_1 10         # 2D potential
    python quick_tps_toy.py potential_2 10         # 2D with barrier shift
"""

import sys
import numpy as np
import openpathsampling as paths
from pathlib import Path

# Import from ops-setup
from ops_setup.systems.examples.toy_systems import (
    ToyTPSSetup,
    potential_0,
    potential_1,
    potential_2,
)


def run_quick_tps(potential_name="potential_1", n_steps=5, storage_file=None):
    """
    Run a quick TPS simulation with a toy potential.
    
    Parameters
    ----------
    potential_name : str
        Name of the toy potential to use
        Options: 'potential_0' (1D), 'potential_1' (2D), 'potential_2' (2D)
    n_steps : int
        Number of MC steps to run (default: 5)
    storage_file : str, optional
        Path to save NetCDF storage. Default: f"tps_{potential_name}.nc"
    
    Returns
    -------
    None
    """
    
    # Validate potential name
    valid_potentials = ["potential_0", "potential_1", "potential_2"]
    if potential_name not in valid_potentials:
        raise ValueError(
            f"Unknown potential: {potential_name}. "
            f"Valid options: {valid_potentials}"
        )
    
    if storage_file is None:
        storage_file = f"tps_{potential_name}.nc"
    
    print(f"\n{'='*60}")
    print(f"Quick TPS Simulation with {potential_name}")
    print(f"{'='*60}\n")
    
    # Create TPS setup
    print(f"Creating TPS setup for {potential_name}...")
    tps_setup = ToyTPSSetup(
        potential_name=potential_name,
        potential_kwargs={},
        integrator_params={
            'dt': 0.05,
            'temperature': 1.0,
            'gamma': 2.5
        }
    )
    
    print(f"  System: {tps_setup.system_name}")
    print(f"  Engine: {tps_setup.md_engine.name}")
    
    # Create initial trajectory
    print(f"\nCreating initial trajectory...")
    paths.PathMover.engine = tps_setup.md_engine
    
    n_snapshots = 150 if potential_name == "potential_0" else 200
    init_traj = paths.Trajectory(
        tps_setup.pes.simple_initial_path(n_snapshots, tps_setup.md_engine)
    )
    print(f"  Initial trajectory: {len(init_traj)} snapshots")
    
    # Create network and move scheme
    print(f"\nSetting up TPS network and move scheme...")
    network = tps_setup.create_network("TPS")
    move_scheme = tps_setup.create_move_scheme(network, "OneWay")
    
    # Create storage
    print(f"\nCreating storage: {storage_file}")
    storage = paths.Storage(storage_file, "w", template=tps_setup.template)
    storage.save(tps_setup.md_engine)
    storage.save(move_scheme)
    storage.save(network)
    
    # Create initial conditions
    print(f"\nPreparing initial conditions...")
    initial_conditions = move_scheme.initial_conditions_from_trajectories(init_traj)
    initial_conditions.sanity_check()
    print(f"  Initial conditions prepared and validated")
    
    # Run TPS
    print(f"\nRunning TPS simulation for {n_steps} MC steps...")
    print(f"{'  Step':<8} {'Acc Rate':<12}")
    print(f"  {'-'*20}")
    
    sampler = paths.PathSampling(storage, move_scheme, initial_conditions)
    sampler.run(n_steps)
    
    # Summary
    print(f"\n{'='*60}")
    print(f"TPS Simulation Complete!")
    print(f"{'='*60}")
    print(f"  Total MC steps: {len(storage.steps)}")
    print(f"  Storage file: {storage_file}")
    print(f"  Overall acceptance rate: {move_scheme.acceptance_rate:.1%}")
    
    # Analyze trajectories
    n_accepted = sum(
        1 for step in storage.steps 
        if step.active[0].is_accepted
    )
    print(f"  Accepted trajectories: {n_accepted}/{len(storage.steps)}")
    
    # Trajectory length statistics
    traj_lengths = [
        len(step.active[0].trajectory) 
        for step in storage.steps
    ]
    print(f"  Trajectory lengths: min={min(traj_lengths)}, max={max(traj_lengths)}, avg={np.mean(traj_lengths):.1f}")
    
    print(f"\nTo load and analyze results:")
    print(f"  import openpathsampling as paths")
    print(f"  storage = paths.Storage('{storage_file}')")
    print(f"  # Access trajectories, engine, network, move_scheme, etc.")
    print()
    
    storage.close()


def main():
    """Parse command line arguments and run TPS."""
    
    potential_name = "potential_1"  # Default
    n_steps = 5  # Default
    
    if len(sys.argv) > 1:
        potential_name = sys.argv[1]
    
    if len(sys.argv) > 2:
        try:
            n_steps = int(sys.argv[2])
        except ValueError:
            print(f"Error: n_steps must be an integer, got '{sys.argv[2]}'")
            sys.exit(1)
    
    try:
        run_quick_tps(potential_name, n_steps)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

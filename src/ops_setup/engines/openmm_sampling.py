"""
Shared OpenMM sampling utilities for ops-setup examples.

"""

from pathlib import Path

import openpathsampling as paths
import openpathsampling.engines.openmm as ops_openmm
from openpathsampling.experimental.storage import Storage


def load_initial_trajectory(traj_path: Path):
    """
    Load an initial trajectory from OPS Storage (.nc) or experimental Storage (.db).

    Parameters
    ----------
    traj_path : Path
        Path to storage file containing trajectory.

    Returns
    -------
    Trajectory
        OpenMM-compatible trajectory.
    """
    if traj_path is None:
        raise ValueError("traj_path is required to load initial trajectory.")

    traj_path = Path(traj_path)
    if traj_path.suffix == ".nc":
        old_store = paths.Storage(traj_path)
        init_traj = old_store.tag["trajectory"]
        mdtraj_traj = init_traj.to_mdtraj()
        old_store.close()
        return ops_openmm.trajectory_from_mdtraj(mdtraj_traj)

    if traj_path.suffix == ".db":
        old_store = Storage(traj_path)
        init_traj = old_store.trajectories[-1]
        mdtraj_traj = init_traj.to_mdtraj()
        old_store.close()
        return ops_openmm.trajectory_from_mdtraj(mdtraj_traj)

    raise ValueError("Unsupported file type. Use .nc or .db for trajectory storage.")

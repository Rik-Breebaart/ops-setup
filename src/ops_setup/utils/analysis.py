import numpy as np
import mdtraj as md
import pandas as pd
import openpathsampling as paths



def get_box_lengths(ops_traj):
    """
    Get box lengths from an OPS trajectory.

    Parameters
    ----------
    ops_traj : OPS trajectory
        OpenPathSampling trajectory

    Returns
    -------
    np.ndarray
        Box lengths (3,)
    """

    # Get box from first frame (assumes constant box)

    try:
        box = ops_traj[0].box_vectors._value
    except AttributeError:
        box = ops_traj[0].box_vectors

    #check if box rectangleangular
    if not np.allclose(box - np.diag(np.diagonal(box)), 0):
        return False, None

    box_lengths = box.diagonal()

    return True, box_lengths


def center_ops_trajectory(
    ops_traj,
    center_atom_idx=None,
):
    """
    Convert and center an entire OPS trajectory into an MDTraj trajectory.

    Parameters
    ----------
    ops_traj : OPS trajectory
        OpenPathSampling trajectory
    center_atom_idx : int or None
        If provided, center on this atom index.
        If None, use geometric center (mean).

    Returns
    -------
    mdtraj.Trajectory
        Centered MDTraj trajectory
    """

    n_frames = len(ops_traj)

    # Get box lengths
    rectangle, box_lengths = get_box_lengths(ops_traj)
    if not rectangle:
        mdtraj_traj = ops_traj.to_mdtraj()
        mdtraj_traj.image_molecules(anchor_molecules=[center_atom_idx] if center_atom_idx is not None else None)
        mdtraj_traj.center_coordinates(mass_weighted=False)
        mdtraj_traj.wrap()

    else:
        # --- Build topology once ---
        topology_omm = paths.engines.openmm.tools.to_openmm_topology(
            ops_traj[0]
        )
        topology_md = md.Topology.from_openmm(topology_omm)

        # --- Allocate coordinate array ---
        n_atoms = ops_traj[0].xyz.shape[0]
        xyz = np.zeros((n_frames, n_atoms, 3))

        # --- Loop over frames ---
        for i, snapshot in enumerate(ops_traj):


            coords = snapshot.xyz.copy()

            # Determine center
            if center_atom_idx is not None:
                center = coords[center_atom_idx]
            else:
                center = coords.mean(axis=0)

            box_center = box_lengths / 2.0

            # Translate
            centered = coords - center + box_center

            # Apply PBC
            centered = centered % box_lengths

            xyz[i] = centered

        # --- Create MDTraj trajectory ---
        mdtraj_traj = md.Trajectory(
            xyz=xyz,
            topology=topology_md,
            unitcell_lengths=np.tile(box_lengths, (n_frames, 1)),
            unitcell_angles=np.tile([90.0, 90.0, 90.0], (n_frames, 1)),
        )

        # --- Fix formal charges (OPS → pandas.NA issue) ---
        for atom in mdtraj_traj.topology.atoms:
            if atom.formal_charge is pd.NA:
                atom.formal_charge = None

    return mdtraj_traj

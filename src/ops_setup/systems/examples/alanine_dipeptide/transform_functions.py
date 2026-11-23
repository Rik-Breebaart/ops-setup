"""Collective variables and descriptors for alanine dipeptide (ACE-ALA-NME).

Atom indices follow the openmmtools ``AlanineDipeptideVacuum`` topology (amber ff96),
which is also the order of the OPS alanine dipeptide tutorial:

    0 HH31  1 CH3  2 HH32  3 HH33  4 C  5 O  6 N  7 H  8 CA  9 HA  10 CB  11-13 HB
    14 C  15 O  16 N  17 H  18 CH3  19-21 HH3

All functions are plain numpy on coordinates; nothing is loaded at import.
"""
import numpy as np
import openpathsampling as paths

# backbone dihedrals: phi (C-N-CA-C), psi (N-CA-C-N), and the two peptide bonds
PHI = (4, 6, 8, 14)
PSI = (6, 8, 14, 16)
OMEGA_1 = (1, 4, 6, 8)        # CH3(ACE)-C-N-CA
OMEGA_2 = (8, 14, 16, 18)     # CA-C-N-CH3(NME)
BACKBONE_DIHEDRALS = {"phi": PHI, "psi": PSI, "omega1": OMEGA_1, "omega2": OMEGA_2}

DESCRIPTOR_LABELS = [f"{f}({name})" for f in ("sin", "cos") for name in BACKBONE_DIHEDRALS]


def dihedrals(coordinates, idx):
    """Dihedral angle (radians, in (-pi, pi]) of the atoms ``idx`` for coordinates of
    shape ``(n_frames, n_atoms, 3)`` (or ``(n_atoms, 3)`` for one frame)."""
    X = np.asarray(coordinates, dtype=float)
    single = X.ndim == 2
    X = X[None] if single else X
    b0 = X[:, idx[0]] - X[:, idx[1]]
    b1 = X[:, idx[2]] - X[:, idx[1]]
    b2 = X[:, idx[3]] - X[:, idx[2]]
    b1 = b1 / np.linalg.norm(b1, axis=-1, keepdims=True)
    v = b0 - np.sum(b0 * b1, axis=-1, keepdims=True) * b1
    w = b2 - np.sum(b2 * b1, axis=-1, keepdims=True) * b1
    ang = np.arctan2(np.sum(np.cross(b1, v) * w, axis=-1), np.sum(v * w, axis=-1))
    return float(ang[0]) if single else ang


def dihedral_cv(snapshot, idx):
    """Dihedral of one snapshot (radians); the function behind the phi/psi CVs."""
    return dihedrals(np.asarray(snapshot.coordinates), idx)


def make_dihedral_cv(name, idx):
    """An OPS CV for one backbone dihedral, in radians."""
    return paths.CoordinateFunctionCV(name, dihedral_cv, idx=list(idx))


def _coordinates(trajectory):
    return np.array([np.asarray(s.coordinates) for s in trajectory])


def backbone_dihedrals(trajectory):
    """``(n_frames, 4)``: phi, psi, omega1, omega2 in radians."""
    X = _coordinates(trajectory)
    return np.stack([dihedrals(X, idx) for idx in BACKBONE_DIHEDRALS.values()], axis=1)


def descriptor_sincos(trajectory):
    """``(n_frames, 8)``: sin and cos of the four backbone dihedrals
    (``DESCRIPTOR_LABELS``); periodic-safe input for a committor model."""
    a = backbone_dihedrals(trajectory)
    return np.concatenate([np.sin(a), np.cos(a)], axis=1)

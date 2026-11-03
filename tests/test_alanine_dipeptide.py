"""Alanine dipeptide in vacuum (ops_setup.systems.examples.alanine_dipeptide)."""
import contextlib
import io

import numpy as np
import pytest

pytest.importorskip("openmm")
pytest.importorskip("openmmtools")

from openmm import unit
import openpathsampling as paths

from ops_setup.systems.examples.alanine_dipeptide import (AlanineDipeptideVacuumSetup, DEFAULT_CONFIG,
                                                          transform_functions as tf)


@pytest.fixture(scope="module")
def ad():
    with contextlib.redirect_stdout(io.StringIO()):
        return AlanineDipeptideVacuumSetup()


@pytest.fixture(scope="module")
def path(ad):
    return ad.generate_initial_path(seed=1)


def test_packaged_config_and_setup(ad):
    assert DEFAULT_CONFIG.exists()
    assert ad.template.box_vectors is None                        # vacuum: no box
    assert ad.md_engine.snapshot_timestep.value_in_unit(unit.picosecond) == pytest.approx(0.02)
    assert (ad.beta * 300.0 * unit.kelvin * unit.BOLTZMANN_CONSTANT_kB) == pytest.approx(1.0)
    assert ad.kT.value_in_unit(unit.kilojoule_per_mole) == pytest.approx(2.4943, abs=1e-3)
    assert [s.name for s in ad.states] == ["C7eq", "C7ax"]
    assert isinstance(ad.create_network("TPS"), paths.TPSNetwork)


def test_dihedral_atoms_are_the_backbone(ad):
    names = [f"{a.residue.name}:{a.name}" for a in ad._topology.atoms()]
    assert [names[i] for i in tf.PHI] == ["ACE:C", "ALA:N", "ALA:CA", "ALA:C"]
    assert [names[i] for i in tf.PSI] == ["ALA:N", "ALA:CA", "ALA:C", "NME:N"]
    assert [names[i] for i in tf.OMEGA_1] == ["ACE:CH3", "ACE:C", "ALA:N", "ALA:CA"]
    assert [names[i] for i in tf.OMEGA_2][:3] == ["ALA:CA", "ALA:C", "NME:N"]


def test_dihedrals_match_mdtraj(path):
    md = pytest.importorskip("mdtraj")
    traj = path.to_mdtraj()
    ref = md.compute_dihedrals(traj, [tf.PHI, tf.PSI, tf.OMEGA_1, tf.OMEGA_2])
    assert np.allclose(tf.backbone_dihedrals(path), ref, atol=1e-5)
    d = tf.descriptor_sincos(path)
    assert d.shape == (len(path), 8) and len(tf.DESCRIPTOR_LABELS) == 8
    assert np.allclose(d[:, :4] ** 2 + d[:, 4:] ** 2, 1.0)


def test_states_from_the_config(ad):
    """The state volumes equal the config's phi/psi boxes, with the periodic wrap of
    psi in [30, 210] deg through +-180 deg, on every frame of a hot trajectory."""
    A, B = ad.states
    assert A(ad.template) and not B(ad.template)                  # template: phi = psi = 180 deg
    hot = ad.generate_initial_path(seed=2, trim=False)
    phi, psi = np.degrees(tf.backbone_dihedrals(hot)[:, :2].T)

    def in_box(name):
        (p0, p1), (s0, s1) = ad.state_ranges[name]
        wrap = lambda a, lo, hi: (a - lo) % 360.0 <= (hi - lo) % 360.0 or np.isclose(hi - lo, 360.0)
        return np.array([wrap(f, p0, p1) and wrap(y, s0, s1) for f, y in zip(phi, psi)])
    for vol, name in ((A, "C7eq"), (B, "C7ax")):
        assert np.array_equal(np.array([bool(vol(s)) for s in hot]), in_box(name))
    assert in_box("C7eq").any() and in_box("C7ax").any()
    assert not np.any(in_box("C7eq") & in_box("C7ax"))


def test_initial_path_is_one_transition(ad, path):
    A, B = ad.states
    ends = [A(path[0]), B(path[0]), A(path[-1]), B(path[-1])]
    assert ends in ([True, False, False, True], [False, True, True, False])
    assert not any(A(s) or B(s) for s in path[1:-1])


def test_dynamics_at_300K(ad, path):
    eng = ad.md_engine
    traj = eng.generate(path[0], [paths.LengthEnsemble(50).can_append])
    X = np.array([np.asarray(s.coordinates) for s in traj])
    assert len(traj) == 50 and np.all(np.isfinite(X))

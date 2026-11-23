"""CB7-B2 host-guest in explicit water, NPT (ops_setup.systems.examples.host_guest)."""
import contextlib
import io
import json

import numpy as np
import pytest

pytest.importorskip("openmm")
pytest.importorskip("openmmtools")

from ops_setup.systems.examples.host_guest import HostGuestNPTSetup, read_storage_trajectory
from ops_setup.systems.examples.host_guest import setup as hg_setup
from ops_setup.systems.examples.host_guest import transform_functions as tf


def _quiet(f, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()):
        return f(*a, **k)


@pytest.fixture(scope="module")
def hg():
    return _quiet(HostGuestNPTSetup)


@pytest.fixture(scope="module")
def path(hg):
    return hg.generate_initial_path()


def test_packaged_config_and_resources(hg):
    assert hg_setup.DEFAULT_CONFIG.exists()
    assert (tf.RESOURCE_DIR / "HostGuest.pdb").exists()
    assert hg.resource_directory == tf.RESOURCE_DIR
    assert [s.name for s in hg.states] == ["bound", "unbound"]
    assert hg.template.box_vectors is not None                  # periodic


def test_storage_reader_needs_no_ops_deserialisation():
    x, v, b = read_storage_trajectory(tf.RESOURCE_DIR / "initialPathNPT.db")
    assert x.shape == v.shape and x.shape[1:] == (4491, 3) and b.shape == (len(x), 3, 3)


def test_initial_path_goes_from_bound_to_unbound(hg, path):
    bound, unbound = hg.states
    assert bound(path[0]) and unbound(path[-1])
    assert not any(bound(s) or unbound(s) for s in path[1:-1])
    assert all(s.engine is hg.md_engine for s in path)
    d = np.ravel(tf.cv_hg_distance(path))
    assert d[0] <= 0.05 and d[-1] >= 1.0


def test_descriptors_and_npt_dynamics(hg, path):
    D = np.asarray(tf.descriptor_transform_HG_continuous_waters_7_descriptors_symmetriced_or(path[:3]))
    assert D.shape == (3, 7) and np.all(np.isfinite(D))
    traj = _quiet(hg.md_engine.generate, path[10], running=[lambda t, trusted=False: len(t) < 3])
    assert len(traj) == 3


def test_relative_resource_directory_and_barostat_seed(tmp_path):
    cfg = json.loads(hg_setup.DEFAULT_CONFIG.read_text())
    import os
    cfg["system_files"]["resource_directory"] = os.path.relpath(tf.RESOURCE_DIR, tmp_path)
    cfg["Integrator_settings"]["barostat_random_seed"] = 17
    p = tmp_path / "hg.json"
    p.write_text(json.dumps(cfg))
    s = _quiet(HostGuestNPTSetup, config_path=p, print_config_flag=False)
    baro = [f for f in s.system.getForces() if f.__class__.__name__ == "MonteCarloBarostat"]
    assert len(baro) == 1 and baro[0].getRandomNumberSeed() == 17
    assert s.resource_directory.resolve() == tf.RESOURCE_DIR

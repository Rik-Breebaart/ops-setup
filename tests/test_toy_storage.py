"""The toy potentials serialise as their constructor arguments, so OPS storage can save and rebuild them."""
import json

import numpy as np
import pytest
from types import SimpleNamespace

from ops_setup.systems.examples.toy_systems import toy_potentials as tp

POTENTIALS = [
    (tp.potential_0, dict(A=1.0, x0=1.0)), (tp.potential_1, {}), (tp.potential_2, dict(a=2, b=1)),
    pytest.param(tp.potential_3, dict(a=2, b=1), marks=pytest.mark.xfail(
        strict=True, reason="potential_3 draws its oscillator omegas from the caller's unseeded RNG")),
    (tp.potential_4_linear, {}), (tp.potential_5_Z_pot, {}), (tp.potential_linear_q, {}),
    (tp.potential_WQ, dict(rotation_degrees=0, scale=1.5)), (tp.potential_Face, dict(scale=1.3)),
    (tp.potential_MullerBrown, dict(d=1.1)),
]


@pytest.mark.parametrize("cls,kw", POTENTIALS, ids=lambda v: getattr(v, "__name__", ""))
def test_round_trip_keeps_the_potential_and_the_callers_rng(cls, kw):
    np.random.seed(7)
    before = np.random.get_state()[1].copy()
    pes = cls(n_harmonics=3, seed=11, **kw)
    assert np.array_equal(np.random.get_state()[1], before)          # building a PES leaves the caller's RNG alone

    dct = json.loads(json.dumps(pes.to_dict()))                         # JSON-safe
    assert dct == dict(n_harmonics=3, seed=11, **kw) | {k: v for k, v in dct.items() if k not in kw}
    again = cls.from_dict(dct)
    rng = np.random.default_rng(0)
    for _ in range(5):
        x = rng.uniform(-1, 1, pes.n_dims_pot + 3)
        snap = SimpleNamespace(positions=x, mass=pes.topology.masses)    # what the toy PES terms read
        assert again.V(snap) == pes.V(snap)
        assert np.array_equal(again.dVdx(snap), pes.dVdx(snap))

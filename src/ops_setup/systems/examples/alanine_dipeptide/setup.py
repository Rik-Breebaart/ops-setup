"""Alanine dipeptide in vacuum (openmmtools ``AlanineDipeptideVacuum``, amber ff96).

States are boxes in the backbone dihedrals (phi, psi), read from the ``States`` block
of the config; the default config (``config_alanine_dipeptide_vacuum.json``, shipped
with the package) defines C7eq and C7ax at 300 K::

    from ops_setup.systems.examples.alanine_dipeptide import AlanineDipeptideVacuumSetup
    ad = AlanineDipeptideVacuumSetup()                 # packaged default config
    path = ad.generate_initial_path(seed=1)            # hot MD, first C7eq <-> C7ax transition
    network = ad.create_network("TPS")
"""
import contextlib
import io
from collections import namedtuple
from pathlib import Path
from typing import Any, Optional, Tuple

import numpy as np
import openpathsampling as paths
from openmm import app
from simtk import unit

from ops_setup.engines.openmm_engine import OpenMMTPSSetup
from . import transform_functions as tf

DEFAULT_CONFIG = Path(__file__).with_name("config_alanine_dipeptide_vacuum.json")


def _first_transition(trajectory, state_a, state_b):
    """The first piece of ``trajectory`` that goes from one state to the other: from
    its last frame in the start state to its first frame in the end state."""
    label = [1 if state_a(s) else 2 if state_b(s) else 0 for s in trajectory]
    last_state, last_i = 0, None
    for i, lab in enumerate(label):
        if lab == 0:
            continue
        if last_state and lab != last_state:
            return paths.Trajectory(list(trajectory[last_i:i + 1]))
        last_state, last_i = lab, i
    raise ValueError("the trajectory contains no transition between the states")


class AlanineDipeptideVacuumSetup(OpenMMTPSSetup):
    """TPS setup for alanine dipeptide in vacuum.

    Parameters
    ----------
    config_path : str or Path, optional
        JSON config; default the packaged ``config_alanine_dipeptide_vacuum.json``.
    print_config_flag : bool
        Whether to print the configuration.

    Attributes (beyond :class:`OpenMMTPSSetup`)
    -------------------------------------------
    phi_cv, psi_cv : CoordinateFunctionCV
        backbone dihedrals in radians.
    state_names : tuple
        names of the two states, in config order (state A first).
    """

    def __init__(self, config_path: Optional[Path] = None, print_config_flag: bool = True):
        super().__init__(config_path or DEFAULT_CONFIG, print_config_flag)

    def _extract_config(self) -> None:
        super()._extract_config()
        states = self.config.get("States") or {
            "C7eq": {"phi": [-180.0, -50.0], "psi": [30.0, 210.0]},
            "C7ax": {"phi": [40.0, 90.0], "psi": [-100.0, -40.0]},
        }
        if len(states) != 2:
            raise ValueError("the States block must define exactly two states")
        self.state_names = tuple(states)
        self.state_ranges = {name: (tuple(r["phi"]), tuple(r["psi"])) for name, r in states.items()}
        self.constraints = self.config.get("system_parameters", {}).get("constraints", "HBonds")
        self.initial_path_settings = self.config.get("initial_path", {})

    def _setup_system(self) -> Tuple[Any, Any, Any]:
        from openmmtools.testsystems import AlanineDipeptideVacuum
        constraints = None if self.constraints in (None, "None") else getattr(app, self.constraints)
        ad = AlanineDipeptideVacuum(constraints=constraints)
        return ad.topology, ad.system, ad.positions

    def _create_template(self):
        """Non-periodic template: a vacuum system has no box (the base class's
        ``periodic=True`` would push the system's default box into the context)."""
        import openpathsampling.engines.openmm as eng
        local = namedtuple("LocalTestSystem", ["name", "system", "topology", "positions"])
        return eng.snapshot_from_testsystem(
            local(name=self.system_name, system=self.system, topology=self._topology,
                  positions=self.positions), periodic=False)

    def _define_states(self):
        self.phi_cv = tf.make_dihedral_cv("phi", tf.PHI)
        self.psi_cv = tf.make_dihedral_cv("psi", tf.PSI)
        deg = np.pi / 180.0
        volumes = []
        for name in self.state_names:
            (p0, p1), (s0, s1) = self.state_ranges[name]
            vol = (paths.PeriodicCVDefinedVolume(self.phi_cv, p0 * deg, p1 * deg, -np.pi, np.pi)
                   & paths.PeriodicCVDefinedVolume(self.psi_cv, s0 * deg, s1 * deg, -np.pi, np.pi))
            volumes.append(vol.named(name))
        return tuple(volumes)

    def generate_initial_path(self, temperature: Optional[float] = None, max_frames: Optional[int] = None,
                              seed: Optional[int] = None, trim: bool = True):
        """An initial path between the two states, as in the OPS alanine dipeptide
        tutorial: MD at a high temperature (default ``initial_path.temperature`` of the
        config, 800 K) from the template until both states have been visited.

        Returns the first transition (from the last frame in one state to the first
        frame in the other) if ``trim``, else the whole hot trajectory.  The frames
        belong to the hot engine; shooting from them at the setup's temperature
        redraws the velocities.

        ``seed`` sets the integrator's random seed.  The run is reproducible only with
        one OpenMM CPU thread (``OPENMM_CPU_THREADS=1``); with more threads the force
        summation order varies and the trajectories diverge."""
        import openpathsampling.engines.openmm as eng
        from openmmtools.integrators import VVVRIntegrator
        temperature = temperature or self.initial_path_settings.get("temperature", 800.0)
        max_frames = max_frames or self.initial_path_settings.get("max_frames", 100000)
        integ = VVVRIntegrator(temperature * self.temp_unit, self.friction, self.dt)
        integ.setConstraintTolerance(1e-5)
        if seed is not None:
            integ.setRandomNumberSeed(int(seed))
        hot = eng.Engine(topology=self.topology, system=self.system, integrator=integ,
                         openmm_properties=self._get_platform_properties(),
                         options={"n_frames_max": int(max_frames),
                                  "n_steps_per_frame": self.n_steps_per_frame})
        hot.name = f"hot_{int(temperature)}K"
        hot.initialize(self.platform_name)
        visit_all = paths.VisitAllStatesEnsemble(list(self.states))
        with contextlib.redirect_stdout(io.StringIO()):       # OPS reports every 10 frames
            traj = hot.generate(self.template, [visit_all.can_append])
        return _first_transition(traj, *self.states) if trim else traj

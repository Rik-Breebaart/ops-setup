"""
Host-Guest system setup for TPS/TIS simulations.

This module provides a specific implementation of the OpenMM TPS/TIS setup
for host-guest binding systems (e.g., CB7-B2).
"""

from pathlib import Path
from typing import Tuple, Any, Optional
import openpathsampling as paths

from ops_setup.engines.openmm_engine import AmberOpenMMSetup
from ops_setup.core.tis_setup import TISSetupBase


class HostGuestTPSSetup(AmberOpenMMSetup):
    """
    TPS setup for host-guest binding systems.
    
    This class extends AmberOpenMMSetup to add host-guest specific
    state definitions and collective variables.
    
    Parameters
    ----------
    config_path : str or Path
        Path to the JSON configuration file.
    cv_function : callable
        Collective variable function for defining states.
    resource_directory : str or Path, optional
        Directory containing system resource files.
    print_config_flag : bool, optional
        Whether to print configuration upon initialization.
        
    Additional Configuration Required
    ---------------------------------
    The config should include:
    - States.bound: Maximum distance for bound state
    - States.unbound: Minimum distance for unbound state
    """
    
    def __init__(self, config_path: Path, cv_function,
                 print_config_flag: bool = True):
        """Initialize host-guest TPS setup."""
        self.cv_function = cv_function
        self.bound_distance = None
        self.unbound_distance = None
        
        super().__init__(config_path, print_config_flag)
    
    def _extract_config(self) -> None:
        """Extract host-guest specific configuration."""
        super()._extract_config()
        
        # Extract state boundaries
        states_config = self.config.get('States', {})
        self.bound_distance = states_config.get('bound', 0.5)
        self.unbound_distance = states_config.get('unbound', 1.5)
    
    def _define_states(self) -> Tuple[Any, Any]:
        """
        Define bound and unbound states for host-guest system.
        
        Returns
        -------
        tuple
            (bound_state, unbound_state) volume definitions.
        """
        print("Defining bound and unbound states...")
        
        bound = paths.CVDefinedVolume(
            self.cv_function,
            lambda_min=0.0,
            lambda_max=self.bound_distance
        ).named('bound')
        
        unbound = paths.CVDefinedVolume(
            self.cv_function,
            lambda_min=self.unbound_distance,
            lambda_max=float("inf")
        ).named('unbound')
        
        return (bound, unbound)


class HostGuestTISSetup(TISSetupBase):
    """
    TIS setup for host-guest binding systems.
    
    This class combines TIS functionality with host-guest specific setup.
    
    Parameters
    ----------
    tps_config_path : str or Path
        Path to the TPS configuration file.
    tis_config_path : str or Path
        Path to the TIS configuration file.
    cv_function : callable
        Collective variable function for defining states.
    resource_directory : str or Path, optional
        Directory containing system resource files.
    print_config_flag : bool, optional
        Whether to print configuration.
    """
    
    def __init__(self, tps_config_path: Path, tis_config_path: Path,
                 cv_function, 
                 print_config_flag: bool = True):
        """Initialize host-guest TIS setup."""
        self.cv_function = cv_function
        self.bound_distance = None
        self.unbound_distance = None
        
        # Store paths to use in parent init
        self._tps_config_path = tps_config_path
        
        # Initialize using special method to handle multiple inheritance
        self._init_as_host_guest(tps_config_path, tis_config_path, print_config_flag)
    
    def _init_as_host_guest(self, tps_config_path, tis_config_path,
                            print_config_flag):
        """Custom initialization to properly setup host-guest TIS."""
        # First setup as OpenMM system
        from ops_setup.engines.openmm_engine import OpenMMTPSSetup
        OpenMMTPSSetup.__init__(self, tps_config_path,
                                print_config_flag)
        
        # Then add TIS configuration
        from ops_setup.core.config_reader import read_config, print_config
        self.tis_config = read_config(tis_config_path)
        if print_config_flag:
            print("\nTIS Configuration:")
            print_config(self.tis_config)
        
        # Extract TIS parameters
        self._extract_tis_config()
    
    def _extract_config(self) -> None:
        """Extract configuration including host-guest specific parameters."""
        # Get OpenMM configuration
        from ops_setup.engines.openmm_engine import OpenMMTPSSetup
        OpenMMTPSSetup._extract_config(self)
        
        # Extract state boundaries
        states_config = self.config.get('States', {})
        self.bound_distance = states_config.get('bound', 0.05)
        self.unbound_distance = states_config.get('unbound', 1.0)
    
    def _setup_system(self) -> Tuple[Any, Any, Any]:
        """Set up system from AMBER files (same as AmberOpenMMSetup)."""
        from ops_setup.engines.openmm_engine import AmberOpenMMSetup
        return AmberOpenMMSetup._setup_system(self)
    
    def _define_states(self) -> Tuple[Any, Any]:
        """Define bound and unbound states."""
        print("Defining bound and unbound states...")
        
        bound = paths.CVDefinedVolume(
            self.cv_function,
            lambda_min=0.0,
            lambda_max=self.bound_distance
        ).named('bound')
        
        unbound = paths.CVDefinedVolume(
            self.cv_function,
            lambda_min=self.unbound_distance,
            lambda_max=float("inf")
        ).named('unbound')
        
        return (bound, unbound)


DEFAULT_CONFIG = Path(__file__).with_name("config_host_guest_npt.json")


def read_storage_trajectory(db_path, index: int = -1):
    """One trajectory of an OPS experimental storage (``.db``) as arrays, read straight from its
    SQLite tables: ``(coordinates, velocities, box_vectors)`` in nm, nm/ps and nm, float32,
    shapes (n, atoms, 3), (n, atoms, 3) and (n, 3, 3).

    Opening the file with OPS' ``Storage`` deserialises every stored object, including CVs whose
    code was marshalled by the Python that wrote the file; that fails under another Python
    version ("bad marshal data").  The snapshot tables need no deserialisation.  A reversed
    snapshot shares its forward copy's statics and kinetics, with the velocities negated."""
    import json
    import sqlite3
    import numpy as np
    con = sqlite3.connect(f"file:{Path(db_path)}?mode=ro", uri=True)
    try:
        tables = [r[0] for r in con.execute(
            "select name from sqlite_master where type='table' and name like 'snapshot%'")]
        snaps = {}
        for t in tables:
            k = t[len("snapshot"):]
            statics = {str(u): (c, b) for u, c, b in
                       con.execute(f"select uuid, coordinates, box_vectors from statics{k}")}
            kinetics = {str(u): v for u, v in con.execute(f"select uuid, velocities from kinetics{k}")}
            for u, s, kin, rev in con.execute(f"select uuid, statics, kinetics, is_reversed from {t}"):
                snaps[str(u)] = (statics[str(s)], kinetics[str(kin)], bool(rev))
        rows = [r[0] for r in con.execute("select snapshots from trajectories order by idx")]
    finally:
        con.close()
    if not rows:
        raise ValueError(f"{db_path} holds no trajectory")
    ids = [s[len("UUID("):-1] if str(s).startswith("UUID(") else str(s) for s in json.loads(rows[index])]
    xs, vs, bs = [], [], []
    for u in ids:
        (c, b), v, rev = snaps[u]
        x = np.frombuffer(c, np.float32)
        xs.append(x.reshape(-1, 3))
        vel = np.frombuffer(v, np.float32).reshape(-1, 3)
        vs.append(-vel if rev else vel)
        bs.append(np.frombuffer(b, np.float32).reshape(3, 3))
    return np.array(xs), np.array(vs), np.array(bs)


def _first_transition(trajectory, state_a, state_b):
    """The first piece of ``trajectory`` from its last frame in one state to its first frame in
    the other state."""
    label = [1 if state_a(s) else 2 if state_b(s) else 0 for s in trajectory]
    last_state, last_i = 0, None
    for i, lab in enumerate(label):
        if lab == 0:
            continue
        if last_state and lab != last_state:
            return paths.Trajectory(list(trajectory[last_i:i + 1]))
        last_state, last_i = lab, i
    raise ValueError("the trajectory contains no transition between the states")


class HostGuestNPTSetup(HostGuestTPSSetup):
    """CB7-B2 host-guest binding in explicit water (NPT) with the packaged defaults, for programs
    that build a set-up from its class name alone (e.g. aimmd-RFPS-TIS's ``ops_setup_system``).

    * ``config_path``: default the packaged ``config_host_guest_npt.json``; a config without a
      ``resource_directory`` uses the repository's ``examples/resource_files/host_guest``.
    * ``cv_function``: the state CV, default the host-guest COM distance
      (``transform_functions.cv_hg_distance``).  States: bound = distance <= ``States.bound``,
      unbound = distance >= ``States.unbound``; state A is bound.
    * :meth:`generate_initial_path`: the stored NPT transition path (``initial_path.storage``),
      oriented bound -> unbound and trimmed to the transition."""

    def __init__(self, config_path: Optional[Path] = None, cv_function=None,
                 print_config_flag: bool = True):
        from . import transform_functions as tf
        self.resource_dir_default = tf.RESOURCE_DIR
        super().__init__(config_path or DEFAULT_CONFIG,
                         cv_function if cv_function is not None else tf.cv_hg_distance,
                         print_config_flag=print_config_flag)

    def _extract_config(self) -> None:
        super()._extract_config()
        files = self.config.setdefault("system_files", {})
        if not files.get("resource_directory"):
            files["resource_directory"] = str(self.resource_dir_default)
        self.initial_path_settings = self.config.get("initial_path", {})

    @property
    def resource_directory(self) -> Path:
        d = Path(self.config["system_files"]["resource_directory"])
        if not d.is_absolute() and getattr(self, "config_path", None) is not None:
            d = self.config_path.parent / d
        return d

    def generate_initial_path(self, seed=None, storage: Optional[str] = None, trim: bool = True):
        """The stored transition path as a trajectory of this set-up's engine, oriented from the
        bound to the unbound state (a path stored the other way is reversed, its velocities
        negated) and, if ``trim``, cut to the first transition.  ``storage``: an OPS ``.db`` file
        (default ``initial_path.storage`` of the config, in the resource directory); its last
        trajectory is used.  ``seed`` is accepted for the common interface and unused: the path
        is read, not generated."""
        import numpy as np
        from simtk import unit
        db = Path(storage or self.initial_path_settings.get("storage", "initialPathNPT.db"))
        if not db.is_absolute():
            db = self.resource_directory / db
        x, v, b = read_storage_trajectory(db)
        bound, unbound = self.states
        cls = type(self.template)

        def build(xs, vs, bs):
            return paths.Trajectory([cls.construct(coordinates=xi * unit.nanometer,
                                                   velocities=vi * unit.nanometer / unit.picosecond,
                                                   box_vectors=bi * unit.nanometer,
                                                   engine=self.md_engine)
                                     for xi, vi, bi in zip(xs, vs, bs)])
        traj = build(x, v, b)
        if unbound(traj[0]) or (not bound(traj[0]) and bound(traj[-1])):
            traj = build(x[::-1], -v[::-1], b[::-1])           # time-reversed: bound -> unbound
        return _first_transition(traj, bound, unbound) if trim else traj

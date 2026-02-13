"""
OpenMM engine setup from GROMACS files for OPS simulations.

This module provides classes for setting up OpenMM-based molecular dynamics
simulations from GROMACS topology and coordinate files, integrated with
OpenPathSampling for path sampling simulations.
"""

from pathlib import Path
from typing import Optional, Tuple, Any, Dict, Callable, List
import json
from collections import namedtuple
import warnings

from ..core.config_reader import read_config
from ..core.tps_utilities import TPSUtilitiesMixin

try:
    from openmm import app
    import openmm as mm
    from openmmtools.integrators import VVVRIntegrator
    from openmm.unit import nanometers, picoseconds, kelvin, bar, kilojoule, mole
    import openpathsampling as paths
    import openpathsampling.engines.openmm as eng
except ImportError:
    raise ImportError(
        "OpenMM and related packages are required. "
        "Please install: openmm, openmmtools, and openpathsampling"
    )

warnings.filterwarnings("ignore")


class OpenMMGromacs:
    """
    Core class for setting up OpenMM simulations from GROMACS files.
    
    This class handles the low-level setup of OpenMM simulations from GROMACS
    topology (.top) and coordinate (.gro) files, including:
    - Loading GROMACS files
    - Creating OpenMM system with proper force fields
    - Setting up integrator and simulation context
    - Configuring reporters
    
    Parameters
    ----------
    topology_file : str or Path
        Path to GROMACS topology file (.top)
    structure_file : str or Path
        Path to GROMACS coordinate file (.gro)
    forcefield_dir : str or Path
        Directory containing forcefield files (e.g., amber99sb-ildn.ff)
    config : dict, optional
        Configuration dictionary with keys:
        - 'temperature': float (K)
        - 'pressure': float (bar)
        - 'timestep': float (ps)
        - 'friction': float (ps^-1)
        - 'barostat_frequency': int
        - 'nonbondedCutoff': float (nm)
        - 'platform': str ('CUDA', 'CPU', 'OpenCL')
        - 'precision': str ('mixed', 'double', 'single')
        
    Attributes
    ----------
    topology : Topology
        OpenMM topology object
    system : System
        OpenMM system object with forces
    positions : ndarray
        Atomic positions
    temperature : Quantity
        Simulation temperature with units
    pressure : Quantity
        Simulation pressure with units
    dt : Quantity
        Integration timestep with units
    friction : Quantity
        Friction coefficient with units
    platform : Platform
        OpenMM platform (CUDA, CPU, etc.)
    integrator : Integrator
        VVVR integrator instance
    simulation : Simulation
        OpenMM simulation object
    """
    
    def __init__(self, 
                 topology_file: Path,
                 structure_file: Path,
                 forcefield_dir: Path,
                 config: Dict[str, Any] = None,
                 initial_positions: Optional[Any] = None):
        """Initialize OpenMM simulation from GROMACS files.
        
        Parameters
        ----------
        initial_positions : array-like, optional
            Initial positions to use. If None, uses positions from structure_file.
        """
        
        self.topology_file = Path(topology_file)
        self.structure_file = Path(structure_file)
        self.forcefield_dir = Path(forcefield_dir)
        self.initial_positions = initial_positions
        
        # Default configuration
        default_config = {
            'temperature': 300.0,
            'pressure': 1.0,
            'timestep': 0.002,
            'friction': 1.0,
            'barostat_frequency': 25,
            'nonbondedCutoff': 1.1,
            'platform': 'CUDA',
            'precision': 'mixed',
            'constraints': 'HBonds',
            'ewaldErrorTolerance': 1e-5,
        }
        
        if config:
            default_config.update(config)
        self.config = default_config
        
        # Set up units
        self._setup_units()
        
        # Load GROMACS files
        self._load_gromacs_files()
        
        # Create system
        self._create_system()
        
        # Setup integrator and platform
        self._setup_integrator()
        self._setup_platform()
        
        # Create simulation
        self._create_simulation()
    
    def _setup_units(self) -> None:
        """Setup unit system."""
        self.temperature = self.config['temperature'] * kelvin
        self.pressure = self.config['pressure'] * bar
        self.dt = self.config['timestep'] * picoseconds
        self.friction = self.config['friction'] / picoseconds
        self.barostat_frequency = self.config['barostat_frequency']
        self.nonbondedCutoff = self.config['nonbondedCutoff'] * nanometers
    
    def _load_gromacs_files(self) -> None:
        """Load GROMACS topology and coordinate files."""
        print(f"Loading GROMACS files:")
        print(f"  Topology: {self.topology_file}")
        print(f"  Structure: {self.structure_file}")
        print(f"  Force field dir: {self.forcefield_dir}")
        
        self.gro = app.GromacsGroFile(str(self.structure_file))
        self.gmx = app.GromacsTopFile(
            str(self.topology_file),
            periodicBoxVectors=self.gro.getPeriodicBoxVectors(),
            includeDir=str(self.forcefield_dir)
        )
        
        self.topology = self.gmx.topology
        self.positions = self.gro.positions
        self.box_vectors = self.gro.getPeriodicBoxVectors()
        
        print(f"  Loaded {self.topology.getNumAtoms()} atoms")
    
    def _create_system(self) -> None:
        """Create OpenMM system with forces."""
        print("Creating OpenMM system...")
        
        constraint_type = getattr(app, self.config.get('constraints', 'HBonds'))
        
        self.system = self.gmx.createSystem(
            nonbondedMethod=app.PME,
            nonbondedCutoff=self.nonbondedCutoff,
            constraints=constraint_type,
            ewaldErrorTolerance=self.config.get('ewaldErrorTolerance', 1e-5)
        )
        
        # Add barostat for NPT
        self.system.addForce(
            mm.MonteCarloBarostat(self.pressure, self.temperature, self.barostat_frequency)
        )
        
        print("System created successfully")
    
    def _setup_integrator(self) -> None:
        """Setup VVVR integrator."""
        print("Setting up VVVR integrator...")
        self.integrator = VVVRIntegrator(
            self.temperature,
            self.friction,
            self.dt
        )
        self.integrator.setConstraintTolerance(1e-5)
    
    def _setup_platform(self) -> None:
        """Setup OpenMM platform."""
        platform_name = self.config['platform']
        print(f"Setting up {platform_name} platform...")
        
        self.platform = mm.Platform.getPlatformByName(platform_name)
        
        self.platform_properties = {}
        if platform_name == 'CUDA':
            self.platform_properties = {'CudaPrecision': self.config['precision']}
        elif platform_name == 'OpenCL':
            self.platform_properties = {'OpenCLPrecision': self.config['precision']}
    
    def _create_simulation(self) -> None:
        """Create OpenMM simulation."""
        print("Creating OpenMM simulation...")
        
        self.simulation = app.Simulation(
            self.topology,
            self.system,
            self.integrator,
            platform=self.platform,
            platformProperties=self.platform_properties
        )
        
        # Use provided initial positions or default from structure file
        positions_to_use = self.initial_positions if self.initial_positions is not None else self.positions
        
        # Set initial positions
        self.simulation.context.setPositions(positions_to_use)
        
        # Set periodic box vectors if available
        if self.box_vectors is not None:
            self.simulation.context.setPeriodicBoxVectors(*self.box_vectors)
    
    def get_current_positions(self):
        """Get current positions from simulation context.
        
        Returns
        -------
        positions : Quantity
            Current atomic positions with units
        """
        state = self.simulation.context.getState(getPositions=True)
        return state.getPositions()
    
    def set_positions(self, positions):
        """Set positions in simulation context.
        
        Parameters
        ----------
        positions : array-like
            Atomic positions to set
        """
        self.simulation.context.setPositions(positions)
        # Update stored positions
        self.positions = positions
    
    def minimize_energy(self, tolerance=10) -> None:
        """
        Perform energy minimization.
        
        Parameters
        ----------
        tolerance : Quantity, optional
            Energy tolerance for minimization
        """
        print("Minimizing energy...")
        state = self.simulation.context.getState(getEnergy=True)
        print(f"  Potential energy before: {state.getPotentialEnergy()}")
        
        self.simulation.minimizeEnergy(tolerance=tolerance)
        
        state = self.simulation.context.getState(getEnergy=True, getPositions=True)
        print(f"  Potential energy after: {state.getPotentialEnergy()}")
        
        # Update stored positions with minimized coordinates
        self.positions = state.getPositions()
    
    def warmup_nvt(self, n_steps: int = 1000) -> None:
        """
        Perform NVT warmup.
        
        Parameters
        ----------
        n_steps : int, optional
            Number of steps for warmup. Default is 1000.
        """
        print(f"Running NVT warmup for {n_steps} steps...")
        self.simulation.context.setVelocitiesToTemperature(self.temperature)
        self.simulation.step(n_steps)
    
    def add_reporter(self, reporter_type: str, output_path: Path, 
                     interval: int = 2500, **kwargs) -> None:
        """
        Add reporter to simulation.
        
        Parameters
        ----------
        reporter_type : str
            Type of reporter: 'StateData', 'DCD', 'NetCDF', 'PDB'
        output_path : Path
            Path for output file
        interval : int, optional
            Reporting interval in steps. Default is 2500.
        **kwargs : dict
            Additional arguments passed to reporter
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if reporter_type == 'StateData':
            self.simulation.reporters.append(
                app.StateDataReporter(str(output_path), interval,
                                     step=True, potentialEnergy=True,
                                     kineticEnergy=True, temperature=True,
                                     volume=True, density=True,
                                     progress=True, remainingTime=True,
                                     **kwargs)
            )
        elif reporter_type == 'DCD':
            self.simulation.reporters.append(
                app.DCDReporter(str(output_path), interval)
            )
        elif reporter_type == 'PDB':
            self.simulation.reporters.append(
                app.PDBReporter(str(output_path), interval)
            )
        elif reporter_type == 'NetCDF':
            try:
                from parmed.openmm.reporters import NetCDFReporter
                self.simulation.reporters.append(
                    NetCDFReporter(str(output_path), interval, vels=True)
                )
            except ImportError:
                print("NetCDF reporter requires 'parmed' package")
    
    def run(self, n_steps: int) -> None:
        """
        Run MD simulation.
        
        Parameters
        ----------
        n_steps : int
            Number of steps to run
        """
        print(f"Running simulation for {n_steps} steps...")
        self.simulation.step(n_steps)


class OpenMMGromacsTPS(TPSUtilitiesMixin):
    """
    TPS-ready OpenMM setup from GROMACS files.
    
    This class wraps OpenMMGromacs to provide functionality for transition path
    sampling, including OPS engine creation and state definition.
    
    Parameters
    ----------
    topology_file : str or Path
        Path to GROMACS topology file
    structure_file : str or Path
        Path to GROMACS coordinate file
    forcefield_dir : str or Path
        Directory containing forcefield files
    state_definitions : dict
        Dictionary defining stable states. Format:
        {
            'stateA': {
                'cvs': [cv1, cv2, ...],
                'bounds': [(min1, max1), (min2, max2), ...]
            },
            'stateB': {...}
        }
    config : dict, optional
        Configuration dictionary (see OpenMMGromacs)
    config_path : str or Path, optional
        Path to JSON configuration file (loads system files and engine settings)
    n_frames_max : int, optional
        Maximum frames in trajectory. Default is 5000.
    n_steps_per_frame : int, optional
        MD steps between frames. Default is 1.
        
    Attributes
    ----------
    openmm : OpenMMGromacs
        Core OpenMM setup object
    engine : Engine
        OpenPathSampling engine
    states : tuple
        (stateA, stateB) volume definitions
    template : Snapshot
        Template snapshot
    """
    
    def __init__(self,
                 topology_file: Optional[Path],
                 structure_file: Optional[Path],
                 forcefield_dir: Optional[Path],
                 state_definitions: Dict[str, Any],
                 config: Optional[Dict[str, Any]] = None,
                 n_frames_max: Optional[int] = 5000,
                 n_steps_per_frame: Optional[int] = 1,
                 initial_positions: Optional[Any] = None,
                 config_path: Optional[Path] = None):
        """Initialize TPS-ready OpenMM setup from GROMACS.
        
        Parameters
        ----------
        initial_positions : array-like, optional
            Initial positions to use for template. If None, uses positions from structure_file.
        """
        
        self.state_definitions = state_definitions
        self.initial_positions = initial_positions
        self.config = {}  # Store full config for selector/scheme access

        if config_path is not None:
            config_path = Path(config_path)
            print(f"Loading OpenMM GROMACS config from: {config_path}")
            full_config = read_config(config_path)
            self.config = full_config  # Store for later access

            system_files = full_config.get('system_files', {})
            resource_dir = Path(system_files.get('resource_directory', '.'))
            if topology_file is None:
                topology_file = resource_dir / system_files.get('topology_file')
            if structure_file is None:
                structure_file = resource_dir / system_files.get('structure_file')
            if forcefield_dir is None:
                forcefield_dir = resource_dir / system_files.get('forcefield_dir')

            tps_settings = full_config.get('TPS_settings', {})
            if n_frames_max is None:
                n_frames_max = tps_settings.get('n_frames_max', 5000)
            if n_steps_per_frame is None:
                n_steps_per_frame = tps_settings.get('n_steps_per_frame', 1)

            if config is None:
                integrator_settings = full_config.get('Integrator_settings', {})
                system_parameters = full_config.get('system_parameters', {})
                config = {
                    'temperature': integrator_settings.get('temperature', 300.0),
                    'pressure': integrator_settings.get('pressure', 1.0),
                    'timestep': integrator_settings.get('dt', 0.002),
                    'friction': integrator_settings.get('friction', 1.0),
                    'barostat_frequency': integrator_settings.get('barostat_frequency', 25),
                    'platform': full_config.get('platform_name', 'CUDA'),
                    'precision': system_parameters.get('precision', 'mixed'),
                    'nonbondedCutoff': system_parameters.get('nonbondedCutoff', 1.1),
                    'ewaldErrorTolerance': system_parameters.get('ewaldErrorTolerance', 1e-5),
                    'constraints': system_parameters.get('constraints', 'HBonds'),
                }

        if topology_file is None or structure_file is None or forcefield_dir is None:
            raise ValueError(
                "Must provide either config_path or all of: "
                "topology_file, structure_file, forcefield_dir"
            )

        self.n_frames_max = n_frames_max
        self.n_steps_per_frame = n_steps_per_frame
        
        # Create core OpenMM setup
        self.openmm = OpenMMGromacs(
            topology_file, structure_file, forcefield_dir, config
        )
        
        # Create template and define states
        self._create_template()
        self.topology = self.template.topology
        
        # Create OPS engine
        self._create_ops_engine()
        
        # Define states
        self._define_states()
    
    def _create_ops_engine(self) -> None:
        """Create OpenPathSampling engine from OpenMM simulation."""
        print("Creating OPS engine from OpenMM simulation...")
        
        # Create a fresh integrator for OPS (can't reuse one already bound to a context)
        ops_integrator = VVVRIntegrator(
            self.openmm.temperature,
            self.openmm.friction,
            self.openmm.dt
        )
        ops_integrator.setConstraintTolerance(1e-5)
        
        engine_options = {
            'n_frames_max': self.n_frames_max,
            'n_steps_per_frame': self.n_steps_per_frame
        }
        
        self.engine = eng.Engine(
            topology=self.template.topology,
            system=self.openmm.system,
            integrator=ops_integrator,
            openmm_properties=self.openmm.platform_properties,
            options=engine_options
        )
        self.engine.name = 'openmm_gromacs_engine'
        self.engine.initialize(self.openmm.platform)
    
    def _create_template(self) -> None:
        """Create snapshot template from initial configuration."""
        print("Creating snapshot template...")
        
        import numpy as np
        
        # Use provided initial positions or default from structure file
        if self.initial_positions is not None:
            positions = self.initial_positions
        else:
            positions = self.openmm.positions
        
        # Convert positions to numpy array if needed (OPS requires .shape attribute)
        if hasattr(positions, '_value'):
            # OpenMM Quantity object
            pos_array = np.array(positions._value) * positions.unit
        elif not hasattr(positions, 'shape'):
            # List or other iterable - convert to numpy array with units
            import openmm.unit as unit
            pos_values = np.array([[p.x, p.y, p.z] for p in positions])
            pos_array = pos_values * unit.nanometer
        else:
            pos_array = positions
        
        testsystem = namedtuple(
            'GromacsSys',
            ['name', 'system', 'topology', 'positions']
        )
        
        test_sys = testsystem(
            name='gromacs_system',
            system=self.openmm.system,
            topology=self.openmm.topology,
            positions=pos_array
        )
        
        self.template = eng.snapshot_from_testsystem(test_sys)
    
    def _define_states(self) -> None:
        """Define stable states from state_definitions."""
        print("Defining stable states...")
        
        state_volumes = []
        
        for state_name in ['stateA', 'stateB']:
            if state_name not in self.state_definitions:
                raise ValueError(f"Missing state definition: {state_name}")
            
            state_def = self.state_definitions[state_name]
            cvs = state_def.get('cvs', [])
            bounds = state_def.get('bounds', [])
            
            if len(cvs) != len(bounds):
                raise ValueError(
                    f"Number of CVs ({len(cvs)}) != number of bounds ({len(bounds)})"
                    f" for {state_name}"
                )
            
            # Create volume as intersection of CV bounds
            volume = None
            for cv, (min_val, max_val) in zip(cvs, bounds):
                cv_volume = paths.CVDefinedVolume(cv, min_val, max_val)
                if volume is None:
                    volume = cv_volume
                else:
                    volume = volume & cv_volume
            
            volume = volume.named(state_name)
            state_volumes.append(volume)
        
        self.states = tuple(state_volumes)
        print(f"States defined: {[s.name for s in self.states]}")
    
    def create_tps_network(self) -> paths.TPSNetwork:
        """
        Create TPS network from defined states.
        
        Returns
        -------
        TPSNetwork
            Transition path sampling network
        """
        return paths.TPSNetwork(
            initial_states=self.states[0],
            final_states=self.states[1]
        ).named('TPS_network')


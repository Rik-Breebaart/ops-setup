"""
OpenMM engine utilities for OPS simulations.

This module provides utilities and base classes for setting up OpenMM-based
MD engines for use with OpenPathSampling.
"""

from pathlib import Path
from typing import Optional, Tuple, Any, Dict
from collections import namedtuple

try:
    from openmm import app
    import openmm as mm
    from openmmtools.integrators import VVVRIntegrator
    from simtk import unit
    import openpathsampling.engines.openmm as eng
except ImportError:
    raise ImportError(
        "OpenMM and related packages are required. "
        "Please install: openmm, openmmtools, and openpathsampling"
    )

from ..core.tps_setup import TPSSetupBase
from ..core.config_reader import read_config


class OpenMMTPSSetup(TPSSetupBase):
    """
    TPS setup class for OpenMM-based simulations.
    
    This class implements the abstract methods from TPSSetupBase for
    OpenMM molecular dynamics simulations.
    
    Parameters
    ----------
    config_path : str or Path
        Path to the JSON configuration file.
    print_config_flag : bool, optional
        Whether to print configuration upon initialization.
        
    Additional Attributes
    ----------------------
    temperature : Quantity
        Simulation temperature with units.
    pressure : Quantity
        Simulation pressure with units (if NPT).
    dt : Quantity
        Integration timestep with units.
    friction : Quantity
        Friction coefficient for Langevin dynamics.
    barostat_frequency : int
        Frequency of barostat updates (if NPT).
    constant_variable : str
        Thermodynamic ensemble ('P' for NPT, 'V' for NVT).
    """
    
    def __init__(self, config_path: Path, 
                 print_config_flag: bool = True):
        """Initialize OpenMM TPS setup."""
        # Will be set in _extract_config before super().__init__() calls them
        self.temperature = None
        self.pressure = None
        self.dt = None
        self.friction = None
        self.barostat_frequency = None
        self.constant_variable = None
        
        super().__init__(config_path, print_config_flag)
    
    def _extract_config(self) -> None:
        """Extract OpenMM-specific configuration parameters."""
        # Call parent method
        super()._extract_config()
        
        # Extract unit definitions
        units_config = self.config.get('UNITS', {})
        self.size_unit = getattr(unit, units_config.get('size_unit', 'nanometer'))
        self.press_unit = getattr(unit, units_config.get('press_unit', 'bar'))
        self.temp_unit = getattr(unit, units_config.get('temp_unit', 'kelvin'))
        self.time_unit = getattr(unit, units_config.get('time_unit', 'picosecond'))
        
        # Extract integrator settings
        integrator_config = self.config.get("Integrator_settings", {})
        self.pressure = integrator_config.get('pressure', 1.0) * self.press_unit
        self.temperature = integrator_config.get('temperature', 300.0) * self.temp_unit
        self.dt = integrator_config.get("dt", 0.002) * self.time_unit
        self.friction = integrator_config.get("friction", 1.0) / self.time_unit
        self.barostat_frequency = integrator_config.get("barostat_frequency", 25)
        self.constant_variable = integrator_config.get("constant_variable", "V")
    
    def _setup_integrator(self):
        """
        Set up VVVR integrator for OpenMM.
        
        Returns
        -------
        VVVRIntegrator
            Configured VVVR integrator.
        """
        print("Setting up VVVR integrator...")
        integrator = VVVRIntegrator(
            self.temperature,
            self.friction,
            self.dt
        )
        integrator.setConstraintTolerance(0.00001)
        return integrator
    
    def _setup_engine(self, integrator):
        """
        Set up the OpenMM engine for OPS.
        
        Parameters
        ----------
        integrator : Integrator
            OpenMM integrator object.
            
        Returns
        -------
        Engine
            OpenPathSampling OpenMM engine.
        """
        print(f"Setting up OpenMM engine on {self.platform_name} platform...")
        platform = mm.Platform.getPlatformByName(self.platform_name)
        
        engine_options = {
            'n_frames_max': self.n_frames_max,
            'n_steps_per_frame': self.n_steps_per_frame
        }
        
        engine = eng.Engine(
            topology=self.topology,
            system=self.system,
            integrator=integrator,
            openmm_properties=self._get_platform_properties(),
            options=engine_options
        )
        engine.name = 'default'
        engine.initialize(platform)
        
        return engine
    
    def _setup_system(self) -> Tuple[Any, Any, Any]:
        """
        Set up the molecular system.
        
        This is a template method that should be overridden by system-specific
        subclasses to load the appropriate topology and coordinates.
        
        Returns
        -------
        tuple
            (topology, system, positions)
            
        Raises
        ------
        NotImplementedError
            This method must be implemented by subclasses.
        """
        raise NotImplementedError(
            "Subclasses must implement _setup_system() to load "
            "system-specific topology and coordinates."
        )
    
    def _create_template(self):
        """
        Create a template snapshot from the system.
        
        Returns
        -------
        Snapshot
            OpenMM snapshot template.
        """
        print("Creating snapshot template...")
        testsystem = namedtuple(
            'LocalTestSystem', 
            ['name', 'system', 'topology', 'positions']
        )
        test_system = testsystem(
            name=self.system_name,
            system=self.system,
            topology=self._topology,
            positions=self.positions
        )
        return eng.snapshot_from_testsystem(test_system)
    
    def _define_states(self) -> Tuple[Any, Any]:
        """
        Define stable states.
        
        This is a template method that should be overridden by system-specific
        subclasses to define appropriate state volumes.
        
        Returns
        -------
        tuple
            (stateA, stateB)
            
        Raises
        ------
        NotImplementedError
            This method must be implemented by subclasses.
        """
        raise NotImplementedError(
            "Subclasses must implement _define_states() to define "
            "system-specific stable states."
        )
    
    def _get_platform_properties(self) -> Dict[str, str]:
        """
        Get OpenMM platform-specific properties.
        
        Returns
        -------
        dict
            Platform properties for OpenMM.
        """
        if self.platform_name == 'OpenCL':
            return {
                'OpenCLPrecision': 'mixed',
                'OpenCLDeviceIndex': '0'
            }
        elif self.platform_name == 'CUDA':
            return {'CudaPrecision': 'mixed'}
        elif self.platform_name == 'CPU':
            return {}
        else:
            return {}


class AmberOpenMMSetup(OpenMMTPSSetup):
    """
    OpenMM TPS setup for AMBER topology and coordinate files.
    
    This class provides a concrete implementation for systems using
    AMBER prmtop/inpcrd files.
    
    Additional Configuration Required
    ---------------------------------
    The config file should specify:
    - topology_file: Name of the .prmtop file
    - coordinate_file: Name of the .inpcrd file
    - state_file: (optional) Name of saved state file to load
    """
    
    def _setup_system(self) -> Tuple[Any, Any, Any]:
        """
        Set up system from AMBER files.
        
        Returns
        -------
        tuple
            (topology, system, positions)
        """
        print("Extracting topology and creating system from AMBER files...")
        
        # Get file names from config

        system_files = self.config.get('system_files', {})
        resource_directory = Path(system_files.get('resource_directory', ''))
        topology_file = system_files.get('topology_file', 'system.prmtop')
        coordinate_file = system_files.get('coordinate_file', 'system.inpcrd')
        state_file = system_files.get('state_file', None)
        
        # Load topology and coordinates
        prmtop = app.AmberPrmtopFile(
            str(resource_directory / topology_file)
        )
        inpcrd = app.AmberInpcrdFile(
            str(resource_directory / coordinate_file)
        )
        
        # Create system with specified parameters
        system_params = self.config.get('system_parameters', {})
        system = prmtop.createSystem(
            nonbondedMethod=app.PME,
            nonbondedCutoff=system_params.get('nonbonded_cutoff', 1.0) * unit.nanometers,
            constraints=app.HBonds,
            rigidWater=True,
            ewaldErrorTolerance=system_params.get('ewald_tolerance', 0.0005)
        )
        
        # Add barostat if NPT
        if self.constant_variable == "P":
            system.addForce(
                mm.MonteCarloBarostat(
                    self.pressure,
                    self.temperature,
                    self.barostat_frequency
                )
            )
        
        # Initialize simulation to get positions
        init_simulation = app.Simulation(
            prmtop.topology,
            system,
            self.integrator_temp
        )
        init_simulation.context.setPositions(inpcrd.positions)
        
        # Load state file if provided
        if state_file:
            init_simulation.loadState(str(resource_directory / state_file))
            
            # Update box vectors if present
            new_box_vectors = init_simulation.context.getState(
                getParameters=True
            ).getPeriodicBoxVectors()
            init_simulation.topology.setPeriodicBoxVectors(new_box_vectors)
        
        # Get final positions
        positions = init_simulation.context.getState(
            getPositions=True
        ).getPositions(asNumpy=True)
        
        return prmtop.topology, system, positions


#TODO include openmm gromacs based system setup class here as well (used for T4L setup)
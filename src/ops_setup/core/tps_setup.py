"""
Base TPS (Transition Path Sampling) setup class.

This module provides a base class for setting up TPS simulations with
OpenPathSampling, designed to be inherited and customized for specific systems.
"""

from pathlib import Path
from typing import Optional, Tuple, Any
import openpathsampling as paths
from .config_reader import read_config, print_config


class TPSSetupBase:
    """
    Base class for TPS simulation setup.
    
    This class provides the basic structure for TPS simulations but requires
    subclassing to implement system-specific methods for engine and state setup.
    
    Parameters
    ----------
    config_path : str or Path
        Path to the JSON configuration file.
    resource_directory : str or Path, optional
        Directory containing system resource files (topology, coordinates, etc.).
    print_config : bool, optional
        Whether to print the configuration upon initialization. Default is True.
        
    Attributes
    ----------
    config : dict
        Configuration dictionary loaded from JSON file.
    resource_directory : Path
        Path to resource files directory.
    system_name : str
        Name of the system being simulated.
    platform_name : str
        Name of the simulation platform (e.g., 'CUDA', 'CPU', 'OpenCL').
    n_frames_max : int
        Maximum number of frames in a trajectory.
    n_steps_per_frame : int
        Number of MD steps between saved frames.
    md_engine : Engine
        OpenPathSampling engine for running MD.
    states : tuple
        Tuple of stable state volumes (stateA, stateB).
    template : Snapshot
        Template snapshot for the system.
    topology : Topology
        System topology.
    """
    
    def __init__(self, config_path: Path, resource_directory: Path = None, 
                 print_config_flag: bool = True):
        """Initialize the TPS setup from configuration file."""
        self.resource_directory = Path(resource_directory) if resource_directory else Path("")
        self.config = read_config(config_path)
        
        if print_config_flag:
            print_config(self.config)
        
        # Extract basic configuration
        self._extract_config()
        
        # Initialize components (to be implemented by subclasses)
        self.integrator_temp = self._setup_integrator()
        self._topology, self.system, self.positions = self._setup_system()
        self.template = self._create_template()
        self.topology = self.template.topology
        self.integrator = self._setup_integrator()
        self.md_engine = self._setup_engine(self.integrator)
        self.states = self._define_states()
        self.selector = self._create_selector()
    
    def _extract_config(self) -> None:
        """
        Extract configuration parameters from the config dictionary.
        
        This method should be overridden if additional config parameters
        are needed.
        """
        # System name
        print("extracting config")
        self.system_name = self.config.get('system_name', 'default_system')
        self.platform_name = self.config.get("platform_name", "CPU")
        
        # TPS Specific settings
        tps_settings = self.config.get("TPS_settings", {})
        self.n_frames_max = tps_settings.get("n_frames_max", 5000)
        self.n_steps_per_frame = tps_settings.get("n_steps_per_frame", 1)
        self.shooting_scheme = tps_settings.get("shooting_scheme", "TwoWay")
        self.tps_selector = tps_settings.get("selector", "uniform")
        self.tps_selector_params = tps_settings.get("selector_params", {})
    
    def _setup_integrator(self):
        """
        Set up the integrator for MD simulation.
        
        This method MUST be implemented by subclasses.
        
        Returns
        -------
        Integrator
            The integrator object for MD simulation.
            
        Raises
        ------
        NotImplementedError
            If not implemented by subclass.
        """
        raise NotImplementedError(
            "Subclasses must implement _setup_integrator() method"
        )
    
    def _setup_engine(self, integrator):
        """
        Set up the MD engine.
        
        This method MUST be implemented by subclasses.
        
        Parameters
        ----------
        integrator : Integrator
            The integrator to use with the engine.
            
        Returns
        -------
        Engine
            The OpenPathSampling engine.
            
        Raises
        ------
        NotImplementedError
            If not implemented by subclass.
        """
        raise NotImplementedError(
            "Subclasses must implement _setup_engine() method"
        )
    
    def _setup_system(self) -> Tuple[Any, Any, Any]:
        """
        Set up the molecular system (topology, system, positions).
        
        This method MUST be implemented by subclasses.
        
        Returns
        -------
        tuple
            (topology, system, positions) for the molecular system.
            
        Raises
        ------
        NotImplementedError
            If not implemented by subclass.
        """
        raise NotImplementedError(
            "Subclasses must implement _setup_system() method"
        )
    
    def _create_template(self):
        """
        Create a template snapshot for the system.
        
        This method MUST be implemented by subclasses.
        
        Returns
        -------
        Snapshot
            Template snapshot for the system.
            
        Raises
        ------
        NotImplementedError
            If not implemented by subclass.
        """
        raise NotImplementedError(
            "Subclasses must implement _create_template() method"
        )
    
    def _define_states(self) -> Tuple[Any, Any]:
        """
        Define the stable states for TPS.
        
        This method MUST be implemented by subclasses.
        
        Returns
        -------
        tuple
            (stateA, stateB) volume definitions.
            
        Raises
        ------
        NotImplementedError
            If not implemented by subclass.
        """
        raise NotImplementedError(
            "Subclasses must implement _define_states() method"
        )

    def _create_selector(self, selector_type=None, **kwargs):
        """
        Create a shooting point selector.

        Parameters
        ----------
        selector_type : str, optional
            Type of selector ('uniform', 'gaussian'). If None, uses config value.
        **kwargs : dict
            Additional parameters for selector creation.
            For gaussian: collectivevariable, width, origin_shift

        Returns
        -------
        ShootingPointSelector or None
            Selector for choosing shooting points.
        """
        if selector_type is None:
            selector_type = (self.tps_selector or "uniform").lower()
        else:
            selector_type = selector_type.lower()

        if selector_type == "uniform":
            return paths.UniformSelector()

        if selector_type == "gaussian":
            gaussian_cls = getattr(paths, "GaussianBiasSelector", None)
            if gaussian_cls is None:
                raise ValueError("Gaussian selector requested but paths.GaussianBiasSelector is unavailable")
            if 'collectivevariable' not in kwargs:
                raise ValueError("CV must be provided to create GaussianBiasSelector")
            collectivevariable = kwargs['collectivevariable']
            if collectivevariable is None:
                raise ValueError("collectivevariable cannot be None for GaussianBiasSelector")
            width = kwargs.get("width", None)
            origin_shift = kwargs.get("origin_shift", None)
            if width is None:
                width = self.tps_selector_params.get("width", 0.1)
            if origin_shift is None:
                origin_shift = self.tps_selector_params.get("origin_shift", 0.0)

            return gaussian_cls(collectivevariable, alpha=1/(2*width**2), l_0=origin_shift)

        raise ValueError(f"Unknown selector type '{selector_type}'")

    def _create_velocity_modifier(self):
        """
        Create a velocity randomizer for two-way shooting.

        Returns
        -------
        RandomVelocities or None
            Modifier to randomize velocities, or None if beta is unavailable.
        """
        beta = getattr(self.integrator, "beta", None)

        if beta is None and hasattr(self.integrator, "getTemperature"):
            openmm_unit = None
            try:
                from openmm import unit as openmm_unit
            except Exception:
                try:
                    from simtk import unit as openmm_unit
                except Exception:
                    openmm_unit = None

            if openmm_unit is not None:
                beta = 1.0 / (self.integrator.getTemperature() * openmm_unit.BOLTZMANN_CONSTANT_kB)

        if beta is None:
            return None

        return paths.RandomVelocities(beta=beta, engine=self.md_engine)
    
    def _get_platform_properties(self) -> dict:
        """
        Get platform-specific properties for MD engine.
        
        Can be overridden by subclasses for custom platform settings.
        
        Returns
        -------
        dict
            Dictionary of platform properties.
        """
        if self.platform_name == 'OpenCL':
            return {'OpenCLPrecision': 'mixed'}
        elif self.platform_name == 'CUDA':
            return {'CudaPrecision': 'mixed'}
        elif self.platform_name == 'CPU':
            return {}
        else:
            return {}
    
    def create_network(self, network_type: str = "TPS"):
        """
        Create a path sampling network.
        
        Parameters
        ----------
        network_type : str, optional
            Type of network to create ('TPS' or 'TIS'). Default is 'TPS'.
            
        Returns
        -------
        Network
            OpenPathSampling network object.
        """
        if network_type == "TPS":
            return paths.TPSNetwork.from_states_all_to_all([self.states[0], self.states[1]])
        else:
            raise ValueError(f"Network type '{network_type}' not supported in base class")
    
    def create_move_scheme(self, network, scheme_type: Optional[str] = None, selector=None):
        """
        Create a move scheme for path sampling.
        
        Parameters
        ----------
        network : Network
            The path sampling network.
        scheme_type : str, optional
            Type of shooting scheme ('OneWay' or 'TwoWay'). Default is config or 'OneWay'.
        selector : ShootingPointSelector, optional
            Custom selector. If None, uses the selector created by the setup.
            
        Returns
        -------
        MoveScheme
            OpenPathSampling move scheme.
        """
        scheme_type = scheme_type or self.shooting_scheme or "OneWay"
        selector = selector or self.selector

        if scheme_type == "OneWay":
            if selector is None:
                return paths.OneWayShootingMoveScheme(network, engine=self.md_engine)
            return paths.OneWayShootingMoveScheme(network, selector=selector, engine=self.md_engine)

        if scheme_type == "TwoWay":
            modifier = self._create_velocity_modifier()
            tw_strategy = paths.strategies.TwoWayShootingStrategy(
                modifier=modifier,
                selector=selector,
                engine=self.md_engine,
                group="TwoWayShooting"
            )

            move_scheme = paths.MoveScheme(network=network)
            move_scheme.append(tw_strategy)
            move_scheme.append(paths.strategies.OrganizeByMoveGroupStrategy())
            move_scheme.build_move_decision_tree()
            return move_scheme

        raise ValueError(f"Scheme type '{scheme_type}' not recognized")

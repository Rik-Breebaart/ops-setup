"""
Toy system setup for TPS/TIS simulations.

This module provides TPS and TIS setup classes for toy model simulations,
which are useful for testing and development without requiring complex
molecular systems.
"""

from pathlib import Path
from typing import Tuple, Any, Callable
import openpathsampling as paths
import openpathsampling.engines.toy as toy_engines
import numpy as np

from ops_setup.core.tps_setup import TPSSetupBase
from ops_setup.core.tis_setup import TISSetupBase
from .toy_potentials import (potential_0, potential_1, potential_2, potential_3, 
                              potential_4_linear, potential_5_Z_pot, potential_linear_q,
                              potential_WQ, potential_Face, potential_MullerBrown)


class ToyTPSSetup(TPSSetupBase):
    """
    TPS setup for toy model systems.
    
    This class provides a concrete implementation for toy potential-based
    systems, useful for testing and demonstrating TPS methodology.
    
    Parameters
    ----------
    potential_name : str
        Name of the toy potential ('potential_0', 'potential_1', etc.)
    potential_kwargs : dict, optional
        Keyword arguments for the potential initialization.
    integrator_params : dict, optional
        Integration parameters (dt, temperature, gamma).
    resource_directory : str or Path, optional
        Not needed for toy systems but kept for API compatibility.
    print_config_flag : bool, optional
        Whether to print configuration. Default is True.
        
    Attributes
    ----------
    pes : PES
        Potential energy surface object.
    toy_engine : Engine
        Toy MD engine.
    template : Snapshot
        Template snapshot.
    states : tuple
        (stateA, stateB) volume definitions.
    """
    
    def __init__(self, potential_name: str = None, potential_kwargs: dict = None,
                    integrator_params: dict = None, config_path: Path = None, 
                    resource_directory=None, print_config_flag: bool = True):
        """Initialize toy TPS setup."""
        self.using_config = config_path is not None

        if self.using_config:
            # Use config mode: call base __init__ and rely on config values
            #TODO: this now wouldnt work as the extract config needs to be changed accordingly (integrator_params doesnt exist yet etc.)
            super().__init__(config_path, resource_directory, print_config_flag)
            # potential_name will be pulled later from config if needed
        else:
            # Manual mode: store parameters before base __init__
            self.potential_name = potential_name
            self.potential_kwargs = potential_kwargs or {}
            self.integrator_params = integrator_params or {}
            self.system_name = potential_name
            self.platform_name = "CPU"

            # Fallback defaults
            self.integrator_params.setdefault('dt', 0.05)
            self.integrator_params.setdefault('temperature', 1.0)
            self.integrator_params.setdefault('gamma', 2.5)

            # Simulate config values so base class can use them
            self.config = {}  # Empty dummy config
            self.tps_selector = "uniform"
            self.tps_selector_params = {}
            self.shooting_scheme = "TwoWay"
            self.n_frames_max = 5000
            self.n_steps_per_frame = 1
            self.resource_directory = Path(resource_directory) if resource_directory else Path("")
      
            # Initialize parent will call _setup_integrator, _setup_system, etc.
            # But we skip the config-based initialization
            self._initialize_toy_system()
        
    def _initialize_toy_system(self):
        """Initialize toy system directly without config file."""
        # Setup toy engine components
        self.integrator = self._setup_integrator()
        self.pes = self._create_potential()
        self.topology = self.pes.topology
        self.integrator = self._setup_integrator()
        self.md_engine = self._setup_engine(self.integrator)
        self.template = self._create_template()
        self.states = self._define_states()
        self.selector = self._create_selector()

    
    def _create_potential(self):
        """Create the toy potential object."""
        if self.potential_name == 'potential_0':
            return potential_0(**self.potential_kwargs)
        elif self.potential_name == 'potential_1':
            return potential_1(**self.potential_kwargs)
        elif self.potential_name == 'potential_2':
            return potential_2(**self.potential_kwargs)
        elif self.potential_name == 'potential_3':
            return potential_3(**self.potential_kwargs)
        elif self.potential_name == 'potential_4_linear':
            return potential_4_linear(**self.potential_kwargs)
        elif self.potential_name == 'potential_5_Z_pot':
            return potential_5_Z_pot(**self.potential_kwargs)
        elif self.potential_name == 'potential_linear_q':
            return potential_linear_q(**self.potential_kwargs)
        elif self.potential_name in ['potential_WQ', 'wolfe-quapp', 'WolfeQuapp']:
            return potential_WQ(**self.potential_kwargs)
        elif self.potential_name in ['potential_Face', 'face', 'Face']:
            return potential_Face(**self.potential_kwargs)
        elif self.potential_name in ['potential_MB', 'mueller-brown', 'MuellerBrown']:
            return potential_MullerBrown(**self.potential_kwargs)
        else:
            raise ValueError(f"Unknown potential: {self.potential_name}")
    
    def _setup_integrator(self):
        """
        Set up Langevin integrator for toy system.
        
        Returns
        -------
        LangevinBAOABIntegrator
            Configured integrator.
        """
        print("Setting up Langevin BAOAB integrator for toy system...")
        integrator = toy_engines.LangevinBAOABIntegrator(
            dt=self.integrator_params['dt'],
            temperature=self.integrator_params['temperature'],
            gamma=self.integrator_params['gamma']
        )
        return integrator
    
    def _setup_engine(self, integrator):
        """
        Set up toy MD engine.
        
        Parameters
        ----------
        integrator : Integrator
            The integrator to use.
            
        Returns
        -------
        Engine
            OpenPathSampling toy engine.
        """
        print(f"Setting up toy engine for {self.potential_name}...")
        
        engine_options = {
            'integ' : integrator,
            'n_frames_max': 5000,
            'n_steps_per_frame': 1
        }
        
        engine = toy_engines.Engine(
            options=engine_options,
            topology=self.topology,
        )
        engine.initialized = True
        
        return engine
    
    def _setup_system(self) -> Tuple[Any, Any, Any]:
        """
        Not needed for toy systems.
        
        Raises
        ------
        NotImplementedError
            Toy systems don't need this method.
        """
        raise NotImplementedError("Not needed for toy systems")
    
    def _create_template(self):
        """
        Create template snapshot for toy system.
        
        Returns
        -------
        Snapshot
            Template snapshot.
        """
        print("Creating snapshot template for toy system...")
        return self.pes.template(self.md_engine)
    
    def _define_states(self) -> Tuple[Any, Any]:
        """
        Define stable states for toy system.
        
        Returns
        -------
        tuple
            (stateA, stateB) volume definitions.
        """
        print(f"Defining states for {self.potential_name}...")
        
        # Create CV for stable state identification
        cv = paths.CoordinateFunctionCV(
            name=f"cv_{self.potential_name}",
            f=self.pes.stable_interface_function,
            center=self.pes.state_A
        ).with_diskcache() if hasattr(self.pes, 'stable_interface_function') else None
        
        if cv is None:
            raise ValueError(f"Potential {self.potential_name} must have stable_interface_function")
        
        # Create state volumes
        stateA = paths.CVDefinedVolume(
            cv,
            lambda_min=0.0,
            lambda_max=self.pes.state_boundary
        ).named('stateA')
        
        cv_B = paths.CoordinateFunctionCV(
            name=f"cv_{self.potential_name}_B",
            f=self.pes.stable_interface_function,
            center=self.pes.state_B
        ).with_diskcache()
        
        stateB = paths.CVDefinedVolume(
            cv_B,
            lambda_min=0.0,
            lambda_max=self.pes.state_boundary
        ).named('stateB')
        
        return (stateA, stateB)

    def _extract_config(self):
        """Not used for toy systems."""
        pass


class ToyTISSetup(ToyTPSSetup, TISSetupBase):
    """
    TIS setup for toy model systems.
    
    Inherits from ToyTPSSetup and extends it with TIS-specific functionality.
    Reuses the same integrator, engine, states, and potential setup from TPS.
    
    Parameters
    ----------
    potential_name : str
        Name of the toy potential.
    potential_kwargs : dict, optional
        Keyword arguments for potential.
    integrator_params : dict, optional
        Integration parameters.
    interface_values : list of float, optional
        Interface values for TIS runs.
    """
    
    def __init__(self, potential_name: str, potential_kwargs: dict = None,
                 integrator_params: dict = None, interface_values_forward: list = None, 
                 interface_values_backward: list = None):
        """Initialize toy TIS setup."""
        # Set TIS-specific attributes before calling parent __init__
  
        self.interface_values_forward = interface_values_forward or []
        self.interface_values_backward = interface_values_backward or []
        
        # Initialize parent ToyTPSSetup (which sets up everything)
        super().__init__(
            potential_name=potential_name,
            potential_kwargs=potential_kwargs,
            integrator_params=integrator_params,
            print_config_flag=True
        )
    
    def _extract_tis_config(self):
        """TIS config already set during init."""
        pass
    
    def get_cv_for_interfaces(self) -> paths.CoordinateFunctionCV:
        """
        Get the CV to use for defining TIS interfaces.
        
        Returns
        -------
        CoordinateFunctionCV
            Collective variable for interfaces.
        """
        # Use x-coordinate for 2D systems, distance for others
        if self.pes.n_dims_pot == 2:
            cv = paths.CoordinateFunctionCV(
                name="interface_cv",
                f=lambda snapshot: snapshot.xyz[0][0]
            ).with_diskcache()
        else:
            cv = paths.CoordinateFunctionCV(
                name="interface_cv",
                f=lambda snapshot: snapshot.xyz[0][0]
            ).with_diskcache()
        
        return cv

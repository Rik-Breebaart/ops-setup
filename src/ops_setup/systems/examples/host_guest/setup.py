"""
Host-Guest system setup for TPS/TIS simulations.

This module provides a specific implementation of the OpenMM TPS/TIS setup
for host-guest binding systems (e.g., CB7-B2).
"""

from pathlib import Path
from typing import Tuple, Any
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

"""
TIS (Transition Interface Sampling) setup class.

This module extends the base TPS setup to support TIS simulations.
"""

from pathlib import Path
from typing import Optional, List
import openpathsampling as paths
from .tps_setup import TPSSetupBase
from .config_reader import read_config, print_config

IN_STATE_LOW = -1e10   # forward: frames in A sit below every interface
IN_STATE_HIGH = 1e10   # backward: frames in B sit above every interface


def _cv_with_state(snapshot, cv, state, in_state_value):
    """Order parameter that equals ``in_state_value`` inside ``state``
    and ``cv(snapshot)`` everywhere else."""
    if state(snapshot):
        return in_state_value
    return cv(snapshot)

class TISSetupBase(TPSSetupBase):
    """
    Base class for TIS simulation setup, extending TPSSetupBase.
    
    This class adds TIS-specific configuration and methods on top of the
    base TPS setup.
    
    Parameters
    ----------
    tps_config_path : str or Path
        Path to the TPS JSON configuration file.
    tis_config_path : str or Path
        Path to the TIS JSON configuration file.
    resource_directory : str or Path, optional
        Directory containing system resource files.
    print_config_flag : bool, optional
        Whether to print configuration upon initialization. Default is True.
        
    Attributes
    ----------
    tis_config : dict
        TIS-specific configuration dictionary.
    shooting_move : str
        Type of shooting move for TIS.
    tis_selector : str
        Type of shooting point selector for TIS.
    gaussian_width : float
        Width parameter for Gaussian selector.
    gaussian_origin_shift : float
        Origin shift for Gaussian selector.
    modification_method : str
        Method for path modification in TIS.
    interface_values_forward : list
        Interface values for forward TIS runs.
    interface_values_backward : list
        Interface values for backward TIS runs.
    """
    
    def __init__(self, tps_config_path: Path, tis_config_path: Path,
                 resource_directory: Path = None, print_config_flag: bool = True):
        """Initialize TIS setup from TPS and TIS configuration files."""
        # Initialize the parent TPS setup
        super().__init__(tps_config_path, resource_directory, print_config_flag)
        
        # Load TIS-specific configuration
        self.tis_config = read_config(tis_config_path)
        if print_config_flag:
            print("\nTIS Configuration:")
            print_config(self.tis_config)
        
        # Extract TIS-specific parameters
        self._extract_tis_config()
    
    def _extract_tis_config(self) -> None:
        """Extract TIS-specific configuration parameters."""
        tis_scheme = self.tis_config.get("TIS", {}).get("Scheme", {})
        tis_params = tis_scheme.get("parameters", {})
        tis_interfaces = self.tis_config.get("TIS", {}).get("interface_parameters", {})
        
        # Shooting scheme parameters
        self.shooting_move = tis_scheme.get("Shooting_Move", "OneWay")
        self.tps_selector = tis_scheme.get("selector", "uniform")
        
        # Selector parameters
        self.gaussian_width = tis_params.get("gaussian width", 0.1)
        self.gaussian_origin_shift = tis_params.get("origin_shift", 0.0)
        
        # Path modification
        self.modification_method = self.tis_config.get("TIS", {}).get(
            "modification_method", "extend"
        )
        
        # Interface values
        self.interface_values_forward = tis_interfaces.get("interfaces_forward", [])
        self.interface_values_backward = tis_interfaces.get("interfaces_backward", [])
    
    def create_tis_network(self, interface_volumes: paths.VolumeInterfaceSet, direction: str = "forward"):
        """
        Create a TIS network with specified interfaces.
        
        Parameters
        ----------
        interface_volumes : paths.VolumeInterfaceSet
            Interface set for TIS.
        direction : str, optional
            Direction of the TIS simulation ('forward' or 'backward').
            Default is 'forward'.
            
        Returns
        -------
        Network
            OpenPathSampling TIS network.
        """
        stateA, stateB = self.states
        
        if direction == "forward":
            network = paths.MISTISNetwork(
                [(stateA, interface_volumes, stateB)]
            ).named(f'mistis_{direction}')
        elif direction == "backward":
            network = paths.MISTISNetwork(
                [(stateB, interface_volumes, stateA)]
            ).named(f'mistis_{direction}')
        else:
            raise ValueError(f"Direction must be 'forward' or 'backward', got '{direction}'")
        
        return network

    def create_interface_set(self, cv, interface_value: float,
                                direction: str = "forward"):
        """
        Create an interface set for TIS.

        The interface volume is the union of the initial state and the
        region on the state side of ``interface_value``:

            forward:  stateA ∪ {cv ≤ interface_value}
            backward: stateB ∪ {cv ≥ interface_value}

        This is built from a modified order parameter that takes a
        sentinel value inside the state, so a path counts as crossing
        the interface only once it has left the state *and* passed
        ``interface_value``.

        Parameters
        ----------
        cv : CollectiveVariable
            Collective variable defining the interface.
        interface_value : float
            Value of the CV at the interface.
        direction : str, optional
            Direction of crossing ('forward' or 'backward'). Default is 'forward'.

        Returns
        -------
        VolumeInterfaceSet
            Interface set for TIS simulation.
        """
        stateA, stateB = self.states

        if direction == "forward":
            lambda_cv = paths.FunctionCV(
                f"{cv.name}_with_stateA",
                _cv_with_state,
                cv=cv,
                state=stateA,
                in_state_value=IN_STATE_LOW,
            )
            return paths.VolumeInterfaceSet(
                lambda_cv,
                minvals=-float("inf"),
                maxvals=interface_value,
            )

        elif direction == "backward":
            lambda_cv = paths.FunctionCV(
                f"{cv.name}_with_stateB",
                _cv_with_state,
                cv=cv,
                state=stateB,
                in_state_value=IN_STATE_HIGH,
            )
            return paths.VolumeInterfaceSet(
                lambda_cv,
                minvals=interface_value,
                maxvals=float("inf"),
            )

        else:
            raise ValueError(f"direction must be 'forward' or 'backward', got {direction!r}")

    def get_interface_values(self, direction: str = "forward") -> List[float]:
        """
        Get interface values for specified direction.
        
        Parameters
        ----------
        direction : str
            Direction ('forward' or 'backward').
            
        Returns
        -------
        list of float
            Interface values for the specified direction.
        """
        if direction == "forward":
            return self.interface_values_forward
        elif direction == "backward":
            return self.interface_values_backward
        else:
            raise ValueError(f"Direction must be 'forward' or 'backward', got '{direction}'")




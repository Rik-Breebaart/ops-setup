"""
Utilities for managing descriptor storage during sampling simulations.

This module provides helper functions for incrementally storing descriptors
during TPS/TIS/RETIS sampling, with automatic handling of descriptor shapes,
names, and storage indices.
"""

from pathlib import Path
from typing import Dict, Callable, Optional, Union, List
import numpy as np
import logging

from .descriptor_storage import DescriptorStorage

logger = logging.getLogger(__name__)


def infer_descriptor_names_and_shapes(
    cv_function: Callable,
    sample_trajectory,
    provided_names: Optional[Union[List[str], Dict[str, int]]] = None
) -> Dict[str, int]:
    """
    Infer descriptor names and their indices from a CV function output.
    
    Parameters
    ----------
    cv_function : Callable
        The collective variable or descriptor transform function
    sample_trajectory : trajectory
        A sample trajectory to test the function on
    provided_names : List[str] or Dict[str, int], optional
        If List: names for each dimension in order
        If Dict: mapping of name -> dimension index for multi-output functions
        If None: auto-generate names like 'dim_0', 'dim_1', etc.
    
    Returns
    -------
    Dict[str, int]
        Mapping of descriptor name to its dimension index
    """
    # Evaluate on first frame to get shape
    test_output = cv_function(sample_trajectory[0])
    
    # Handle different output shapes
    if isinstance(test_output, (int, float)):
        # Scalar output
        n_dims = 1
        test_output = np.array([test_output])
    elif isinstance(test_output, np.ndarray):
        if test_output.ndim == 0:
            # Scalar numpy array
            n_dims = 1
        elif test_output.ndim == 1:
            # 1D array (multiple descriptors)
            n_dims = len(test_output)
        else:
            raise ValueError(
                f"CV function returned {test_output.ndim}D array. "
                f"Expected scalar or 1D array."
            )
    else:
        raise TypeError(
            f"CV function returned {type(test_output)}. "
            f"Expected numeric value or numpy array."
        )
    
    # Build name mapping
    if provided_names is None:
        # Auto-generate names
        if n_dims == 1:
            return {'value': 0}
        else:
            return {f'dim_{i}': i for i in range(n_dims)}
    
    elif isinstance(provided_names, list):
        # List of names provided
        if len(provided_names) != n_dims:
            raise ValueError(
                f"Provided {len(provided_names)} names but CV returns {n_dims} dimensions"
            )
        return {name: i for i, name in enumerate(provided_names)}
    
    elif isinstance(provided_names, dict):
        # Dictionary mapping provided
        if max(provided_names.values()) >= n_dims:
            raise ValueError(
                f"Index {max(provided_names.values())} out of range for {n_dims} dimensions"
            )
        return provided_names
    
    else:
        raise TypeError(
            f"provided_names must be List, Dict, or None. Got {type(provided_names)}"
        )


def extract_descriptors_from_cv(
    cv_function: Callable,
    trajectory,
    descriptor_mapping: Dict[str, int]
) -> Dict[str, np.ndarray]:
    """
    Extract named descriptors from a CV function applied to a trajectory.
    
    Parameters
    ----------
    cv_function : Callable
        The CV or descriptor transform function
    trajectory : trajectory
        The trajectory to compute descriptors for
    descriptor_mapping : Dict[str, int]
        Mapping of descriptor names to their dimension indices
    
    Returns
    -------
    Dict[str, np.ndarray]
        Dictionary of descriptor_name -> array of shape (n_points, 1)
    """
    # Compute CV for entire trajectory
    cv_output = cv_function(trajectory)
    
    # Ensure 2D shape (n_points, n_dims)
    if cv_output.ndim == 1:
        if len(descriptor_mapping) == 1:
            # Single descriptor over trajectory
            cv_output = cv_output.reshape(-1, 1)
        else:
            # Single snapshot with multiple descriptors - shouldn't happen for trajectories
            # but handle gracefully
            cv_output = cv_output.reshape(1, -1)
    
    # Extract each named descriptor
    descriptors = {}
    for name, idx in descriptor_mapping.items():
        descriptors[name] = cv_output[:, idx:idx+1]
    
    return descriptors


def get_last_storage_index(storage_path: Path, set_name: str, interface_value: float) -> int:
    """
    Get the last storage index from an existing DescriptorStorage.
    
    Parameters
    ----------
    storage_path : Path
        Path to the descriptor storage
    set_name : str
        The set name to check
    interface_value : float
        The interface value to check
    
    Returns
    -------
    int
        The last storage_index + 1 (next index to use), or 0 if storage is empty
    """
    if not storage_path.with_suffix('.meta.json').exists():
        return 0
    
    with DescriptorStorage.load(storage_path, mode='r') as storage:
        interface_key = f"{interface_value:.2f}"
        
        if set_name not in storage.sets:
            return 0
        
        if interface_key not in storage.sets[set_name].interfaces:
            return 0
        
        trajectories = storage.sets[set_name].interfaces[interface_key].trajectories
        if not trajectories:
            return 0
        
        # Return the max storage_index + 1
        return max(t.storage_index for t in trajectories) + 1


def sampling_descriptor_manager(
    descriptor_storage_path: Path,
    sampler,
    ops_storage,
    cv_functions: Union[Callable, Dict[str, Callable]],
    n_steps: int = 100,
    increment_steps: int = 1,
    start_index: Optional[int] = None,
    set_name: str = 'TPS',
    interface_value: float = 0.0,
    descriptor_names: Optional[Union[List[str], Dict[str, int]]] = None,
    method_type: str = 'TPS'
):
    """
    Manage descriptor storage during sampling simulations.
    
    Automatically handles:
    - Index tracking (auto-detects last index if not provided)
    - Descriptor shape handling for both scalar and multi-dimensional CVs
    - Incremental storage during sampling
    - Creating new storage or appending to existing
    
    Parameters
    ----------
    descriptor_storage_path : Path
        Path to the descriptor storage file
    sampler : paths.PathSampler
        The path sampler used for sampling
    ops_storage : paths.Storage
        The OPS storage containing the sampling data
    cv_functions : Callable or Dict[str, Callable]
        If Callable: single CV function (e.g., descriptor_transform)
        If Dict: mapping of descriptor_name -> cv_function
    n_steps : int, optional
        Number of steps for sampling, by default 100
    increment_steps : int, optional
        Number of steps to increment for each sampling iteration, by default 1
    start_index : int, optional
        Starting index for storing new descriptors. If None, auto-detected from storage
    set_name : str, optional
        Set name for organizing trajectories, by default 'TPS'
    interface_value : float, optional
        Interface value for TIS/RETIS, by default 0.0
    descriptor_names : List[str] or Dict[str, int], optional
        For single cv_function: names for each dimension
        Ignored if cv_functions is a dict (names come from keys)
    method_type : str, optional
        Type of sampling method ('TPS', 'TIS', 'RETIS'), by default 'TPS'
    
    Examples
    --------
    >>> # Single CV function with automatic naming
    >>> sampling_descriptor_manager(
    ...     descriptor_storage_path=Path("my_descriptors"),
    ...     sampler=sampler,
    ...     ops_storage=storage,
    ...     cv_functions=transform_functions.cv_hg_distance,
    ...     n_steps=100
    ... )
    
    >>> # Multiple named CVs
    >>> sampling_descriptor_manager(
    ...     descriptor_storage_path=Path("my_descriptors"),
    ...     sampler=sampler,
    ...     ops_storage=storage,
    ...     cv_functions={
    ...         'distance': transform_functions.cv_hg_distance,
    ...         'angle': transform_functions.cv_hg_angle
    ...     },
    ...     n_steps=100
    ... )
    
    >>> # Multi-dimensional descriptor_transform with custom names
    >>> sampling_descriptor_manager(
    ...     descriptor_storage_path=Path("my_descriptors"),
    ...     sampler=sampler,
    ...     ops_storage=storage,
    ...     cv_functions=descriptor_transform_HG_new_symmetric,
    ...     descriptor_names=['distance', 'angle', 'h_bonds', 'waters', ...],
    ...     n_steps=100
    ... )
    """
    # Check if storage exists and determine start index
    storage_exists = descriptor_storage_path.with_suffix('.meta.json').exists()
    
    if start_index is None:
        if storage_exists:
            start_index = get_last_storage_index(
                descriptor_storage_path, set_name, interface_value
            )
            logger.info(
                f"Auto-detected start_index={start_index} from existing storage"
            )
        else:
            start_index = 0
            logger.info("Creating new descriptor storage, starting at index 0")
    else:
        if storage_exists:
            logger.warning(
                f"Manual start_index={start_index} provided for existing storage. "
                f"Ensure this doesn't overwrite existing data!"
            )
    
    # Determine if we have single CV or multiple CVs
    if callable(cv_functions):
        # Single CV function - need to infer descriptor structure
        # Get a sample trajectory to test
        try :
            sample_traj = ops_storage.trajectories[-1]
        except:
            raise ValueError("No trajectories in ops_storage to infer descriptor structure")
        
        # Infer descriptor mapping
        descriptor_mapping = infer_descriptor_names_and_shapes(
            cv_functions, sample_traj, descriptor_names
        )
        logger.info(f"Inferred descriptor mapping: {descriptor_mapping}")
        
        cv_dict = {'_single_cv': cv_functions}
        use_single_cv = True
    else:
        # Dictionary of CV functions provided
        cv_dict = cv_functions
        descriptor_mapping = None
        use_single_cv = False
    
    # Calculate sampling cycles
    n_cycles = n_steps // increment_steps
    logger.info(
        f"\nRunning {method_type} for {n_steps} MC steps in increments of "
        f"{increment_steps} steps ({n_cycles} cycles)..."
    )
    
    # Determine mode for first write
    mode = 'w' if not storage_exists else 'a'
    
    for cycle in range(n_cycles):
        logger.info(f"\nCycle {cycle+1}/{n_cycles}: Sampling {increment_steps} steps...")
        
        sim_steps = min(increment_steps, n_steps - cycle * increment_steps)
        sampler.run(n_steps=sim_steps)
        
        # Open storage for this cycle
        storage_mode = mode if cycle == 0 else 'a'
        
        with DescriptorStorage(descriptor_storage_path, mode=storage_mode, method_type=method_type) as desc_storage:
            for mcstep in range(sim_steps):
                # Get the sampled path for the current step
                sample_traj = ops_storage.steps[-(sim_steps - mcstep)].active[0].trajectory
                
                # Compute descriptors
                if use_single_cv:
                    # Single CV function - extract named descriptors
                    descriptors = extract_descriptors_from_cv(
                        cv_dict['_single_cv'], sample_traj, descriptor_mapping
                    )
                else:
                    # Multiple CV functions
                    descriptors = {}
                    for name, cv_func in cv_dict.items():
                        value = cv_func(sample_traj)
                        # Ensure 2D shape (n_points, 1)
                        if isinstance(value, (list, np.ndarray)):
                            value = np.asarray(value)
                            if value.ndim == 1:
                                value = value.reshape(-1, 1)
                        else:
                            value = np.array([[value]] * len(sample_traj))
                        descriptors[name] = value
                
                # Store descriptors
                current_index = start_index + cycle * increment_steps + mcstep
                desc_storage.add_trajectory(
                    set_name=set_name,
                    interface_value=interface_value,
                    descriptors=descriptors,
                    n_points=len(sample_traj),
                    storage_index=current_index
                )
        
        logger.info(f"Stored descriptors for {sim_steps} trajectories")
    
    logger.info(f"\nSampling complete. Stored {n_steps} trajectories total.")

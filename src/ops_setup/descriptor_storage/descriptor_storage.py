"""
Descriptor storage module for efficient trajectory descriptor management.

This module provides storage and retrieval of molecular descriptors computed
from trajectories during TPS/TIS/RETIS simulations.

Features:
- Hierarchical trajectory organization (method → origin_set → interface → trajectory)
- Efficient numpy array storage for descriptors
- JSON metadata for structure and trajectory info
- Context manager support for safe I/O during simulations
- Support for multiple sampling methods (TPS, TIS, RETIS, etc.)
- Optional trajectory weighting
- Fast access without loading full OPS storage
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Any, Optional, Callable, Union
from pathlib import Path
import json
import numpy as np
import logging
import time

logger = logging.getLogger(__name__)


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class TrajectoryInfo:
    """Information about a single trajectory in storage."""
    storage_index: int          # Original index in OPS storage
    relative_index: int         # Index within the method/set/interface
    n_points: int              # Number of snapshots in trajectory
    descriptor_start: int      # Starting index in concatenated descriptor array
    descriptor_end: int        # Ending index in concatenated descriptor array
    
    def to_dict(self) -> Dict[str, int]:
        return {
            'storage_index': self.storage_index,
            'relative_index': self.relative_index,
            'n_points': self.n_points,
            'descriptor_start': self.descriptor_start,
            'descriptor_end': self.descriptor_end,
        }
    
    @staticmethod
    def from_dict(data: Dict[str, int]) -> 'TrajectoryInfo':
        return TrajectoryInfo(**data)


@dataclass
class InterfaceData:
    """Data for all trajectories at a specific interface."""
    interface_value: float
    trajectories: List[TrajectoryInfo] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'interface_value': self.interface_value,
            'trajectories': [t.to_dict() for t in self.trajectories]
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'InterfaceData':
        return InterfaceData(
            interface_value=data['interface_value'],
            trajectories=[TrajectoryInfo.from_dict(t) for t in data['trajectories']]
        )


@dataclass
class SetData:
    """Data for all interfaces in a specific origin set."""
    set_name: str
    interfaces: Dict[str, InterfaceData] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'set_name': self.set_name,
            'interfaces': {
                iface_key: iface_data.to_dict()
                for iface_key, iface_data in self.interfaces.items()
            }
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'SetData':
        return SetData(
            set_name=data['set_name'],
            interfaces={
                iface_key: InterfaceData.from_dict(iface_data)
                for iface_key, iface_data in data['interfaces'].items()
            }
        )


# ============================================================================
# Main Descriptor Storage Class
# ============================================================================

class DescriptorStorage:
    """
    Efficient storage system for trajectory descriptors from sampling simulations.
    
    Supports multiple sampling methods (TPS, TIS, RETIS, etc.) with hierarchical
    organization. Can be used during simulations to incrementally compute and store
    descriptors without loading full OPS storage.
    
    Parameters
    ----------
    path : str or Path
        Base path for storage files (descriptors, structure, metadata)
    mode : {'r', 'w', 'a'}
        File mode: 'r' (read), 'w' (write/create), 'a' (append)
    method_type : str, optional
        Type of sampling method ('TPS', 'TIS', 'RETIS', etc.)
        Allows storing method-specific metadata
    compress : bool, optional
        Whether to use compressed numpy (.npz) format (default: True)
    
    Attributes
    ----------
    sets : Dict[str, SetData]
        Hierarchical data: method → origin_set → interface → trajectories
    descriptors : Dict[str, np.ndarray]
        Descriptor arrays: descriptor_name → array of shape (N_total_points, n_dim)
    shot_results : np.ndarray, optional
        TIS shot results: shape (N_total_points, n_features)
    trajectory_weights : Dict[str, Dict[str, np.ndarray]]
        Optional weights for each trajectory
    
    Examples
    --------
    >>> # Create new descriptor storage
    >>> storage = DescriptorStorage("my_descriptors", mode='w', method_type='TPS')
    >>> 
    >>> # Add descriptors during simulation (within context manager)
    >>> with storage:
    ...     # Compute and add trajectory descriptors
    ...     storage.add_trajectory(
    ...         set_name='set_A',
    ...         interface_value=0.5,
    ...         descriptors={'cv_dist': np.array([...])},
    ...         n_points=100,
    ...         storage_index=10
    ...     )
    >>> 
    >>> # Load and access later
    >>> storage = DescriptorStorage.load("my_descriptors", mode='r')
    >>> desc = storage.get_trajectory_descriptors('set_A', '0.50', 0, 'cv_dist')
    >>> 
    >>> # Add weights for RETIS calculations
    >>> storage.set_trajectory_weights('set_A', '0.50', weights_array)
    """
    
    def __init__(self,
                 path: Union[str, Path],
                 mode: str = 'r',
                 method_type: Optional[str] = None,
                 compress: bool = True):
        """Initialize descriptor storage."""
        self.path = Path(path)
        self.mode = mode
        self.method_type = method_type or 'unknown'
        self.compress = compress
        self._is_open = False
        
        # Data structures
        self.sets: Dict[str, SetData] = {}
        self.descriptors: Dict[str, np.ndarray] = {}
        self.shot_results: Optional[np.ndarray] = None
        self.trajectory_weights: Dict[str, Dict[str, np.ndarray]] = {}
        self.metadata: Dict[str, Any] = {
            'method_type': method_type,
            'created': time.time(),
            'descriptor_dims': {}
        }
        
        # Internal state for efficient writing
        self._descriptor_accumulators: Dict[str, List[np.ndarray]] = {}
        self._shot_results_accumulator: List[np.ndarray] = []
        self._global_point_index = 0
        
        if mode == 'r' and self.path.parent.exists():
            self.load_structure()
        elif mode == 'a' and self.path.parent.exists():
            # Load existing data for append mode
            self._load_all_data()
            # Set global point index to end of existing data
            self._global_point_index = self._compute_total_points()
        elif mode == 'w':
            self.path.parent.mkdir(parents=True, exist_ok=True)
        
        self._is_open = True
    
    # ========================================================================
    # Context Manager Support
    # ========================================================================
    
    def __enter__(self):
        """Enter context manager."""
        self._is_open = True
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager and flush data."""
        self.close()
        return False
    
    def close(self):
        """Close storage and flush all data to disk."""
        if not self._is_open:
            return
        
        if self.mode in ['w', 'a']:
            self.flush()
        
        self._is_open = False
        logger.info(f"DescriptorStorage closed: {self.path}")
    
    def flush(self):
        """Flush accumulated data to disk."""
        if not self._descriptor_accumulators and not self._shot_results_accumulator:
            return
        
        # Finalize descriptor arrays
        for name, arr_list in self._descriptor_accumulators.items():
            if name not in self.descriptors or self.descriptors[name] is None:
                self.descriptors[name] = np.concatenate(arr_list, axis=0)
            else:
                new_part = np.concatenate(arr_list, axis=0)
                self.descriptors[name] = np.vstack([self.descriptors[name], new_part])
        
        # Finalize shot results
        if self._shot_results_accumulator:
            new_results = np.concatenate(self._shot_results_accumulator, axis=0)
            if self.shot_results is None:
                self.shot_results = new_results
            else:
                self.shot_results = np.vstack([self.shot_results, new_results])
        
        # Save to disk
        self.save()
        
        # Clear accumulators
        self._descriptor_accumulators.clear()
        self._shot_results_accumulator.clear()
        self._global_point_index = 0
    
    # ========================================================================
    # Data Addition
    # ========================================================================
    
    def add_trajectory(self,
                      set_name: str,
                      interface_value: Union[float, str],
                      descriptors: Dict[str, np.ndarray],
                      n_points: int,
                      storage_index: int,
                      relative_index: Optional[int] = None,
                      shot_results: Optional[np.ndarray] = None) -> None:
        """
        Add descriptors for a single trajectory.
        
        Parameters
        ----------
        set_name : str
            Origin set name (e.g., 'initial', 'basin_A', 'basin_B')
        interface_value : float or str
            Interface value (e.g., 0.5 or '0.50')
        descriptors : Dict[str, np.ndarray]
            Descriptor arrays: descriptor_name → array of shape (n_points, n_dim)
        n_points : int
            Number of snapshots in trajectory
        storage_index : int
            Index in original OPS storage
        relative_index : int, optional
            Index within the set/interface (auto-computed if None)
        shot_results : np.ndarray, optional
            TIS shot results: shape (n_points, n_features)
        """
        if not self._is_open:
            raise RuntimeError("Storage is closed. Use 'with' statement or call open().")
        
        interface_key = _interface_key(interface_value)
        
        # Initialize sets/interfaces as needed
        if set_name not in self.sets:
            self.sets[set_name] = SetData(set_name=set_name)
        if interface_key not in self.sets[set_name].interfaces:
            self.sets[set_name].interfaces[interface_key] = InterfaceData(
                interface_value=float(interface_value)
            )
        
        interface_data = self.sets[set_name].interfaces[interface_key]
        relative_idx = relative_index or len(interface_data.trajectories)
        
        # Add to accumulators
        for name, arr in descriptors.items():
            if name not in self._descriptor_accumulators:
                self._descriptor_accumulators[name] = []
                if name not in self.metadata['descriptor_dims']:
                    self.metadata['descriptor_dims'][name] = arr.shape[1] if len(arr.shape) > 1 else 1
            
            if arr.shape[0] != n_points:
                raise ValueError(
                    f"Descriptor {name} has {arr.shape[0]} points, "
                    f"but trajectory has {n_points} points"
                )
            
            self._descriptor_accumulators[name].append(arr)
        
        if shot_results is not None:
            if shot_results.shape[0] != n_points:
                raise ValueError(
                    f"shot_results has {shot_results.shape[0]} points, "
                    f"but trajectory has {n_points} points"
                )
            self._shot_results_accumulator.append(shot_results)
        
        # Record trajectory metadata
        traj_info = TrajectoryInfo(
            storage_index=storage_index,
            relative_index=relative_idx,
            n_points=n_points,
            descriptor_start=self._global_point_index,
            descriptor_end=self._global_point_index + n_points,
        )
        interface_data.trajectories.append(traj_info)
        self._global_point_index += n_points
    
    # ========================================================================
    # Data Retrieval
    # ========================================================================
    
    def get_trajectory_descriptors(self,
                                  set_name: str,
                                  interface_value: Union[float, str],
                                  trajectory_index: int,
                                  descriptor_names: List[str]) -> np.ndarray:
        """Get descriptors for a specific trajectory."""
        if set_name not in self.sets:
            raise KeyError(f"Set '{set_name}' not found")
        interface_key = _interface_key(interface_value)
        if interface_key not in self.sets[set_name].interfaces:
            raise KeyError(f"Interface '{interface_key}' not found in set '{set_name}'")
        not_in_descriptors = [name for name in descriptor_names if name not in self.descriptors]
        if not_in_descriptors:
            raise KeyError(f"Descriptors not found: {not_in_descriptors}")
        
        traj_info = self.sets[set_name].interfaces[interface_key].trajectories[trajectory_index]
        return np.concatenate([
            self.descriptors[name][
                traj_info.descriptor_start:traj_info.descriptor_end
            ] for name in descriptor_names
        ], axis=1)  
    
    def get_trajectory_shot_results(self,
                                   set_name: str,
                                   interface_value: Union[float, str],
                                   trajectory_index: int) -> Optional[np.ndarray]:
        """Get shot results for a specific trajectory."""
        if self.shot_results is None:
            return None
        
        interface_key = _interface_key(interface_value)
        traj_info = self.sets[set_name].interfaces[interface_key].trajectories[trajectory_index]
        return self.shot_results[
            traj_info.descriptor_start:traj_info.descriptor_end
        ]
    
    def get_interface_descriptors(self,
                                 set_name: str,
                                 interface_value: Union[float, str],
                                 descriptor_names: List[str],
                                 starting_traj: int = 0) -> np.ndarray:
        """Get all descriptors at a specific interface (concatenated)."""
        not_in_descriptors = [name for name in descriptor_names if name not in self.descriptors]
        if not_in_descriptors:
            raise KeyError(f"Descriptors not found: {not_in_descriptors}")
        
        interface_key = _interface_key(interface_value)
        interface_data = self.sets[set_name].interfaces[interface_key]
        if not interface_data.trajectories:
            return np.array([])
        
        start = interface_data.trajectories[starting_traj].descriptor_start
        end = interface_data.trajectories[-1].descriptor_end

        

        return np.concatenate([
            self.descriptors[name][start:end] for name in descriptor_names
        ], axis=1)
    
    # ========================================================================
    # Weights Management
    # ========================================================================
    
    def set_trajectory_weights(self,
                              set_name: str,
                              interface_value: Union[float, str],
                              weights: np.ndarray) -> None:
        """Set weights for trajectories at an interface."""
        if set_name not in self.sets:
            raise KeyError(f"Set '{set_name}' not found")
        
        interface_key = _interface_key(interface_value) 
        if interface_key not in self.sets[set_name].interfaces:
            raise KeyError(f"Interface '{interface_key}' not found")
        
        n_trajs = len(self.sets[set_name].interfaces[interface_key].trajectories)
        if len(weights) != n_trajs:
            raise ValueError(
                f"Expected {n_trajs} weights, got {len(weights)}"
            )
        
        if set_name not in self.trajectory_weights:
            self.trajectory_weights[set_name] = {}
        
        self.trajectory_weights[set_name][interface_key] = weights.copy()
    
    def get_trajectory_weight(self,
                             set_name: str,
                             interface_value: Union[float, str],
                             trajectory_index: int) -> float:
        """Get weight for a specific trajectory (default 1.0)."""
        interface_key = _interface_key(interface_value)
        if (set_name in self.trajectory_weights and
            interface_key in self.trajectory_weights[set_name]):
            return float(self.trajectory_weights[set_name][interface_key][trajectory_index])
        return 1.0
    
    def get_interface_weights(self,
                             set_name: str,
                             interface_value: Union[float, str]) -> np.ndarray:
        """Get per-point weights for an interface."""
        interface_key = _interface_key(interface_value)
        interface_data = self.sets[set_name].interfaces[interface_key]
        
        if (set_name not in self.trajectory_weights or
            interface_key not in self.trajectory_weights[set_name]):
            # Uniform weights
            total_points = sum(t.n_points for t in interface_data.trajectories)
            return np.ones(total_points)
        
        traj_weights = self.trajectory_weights[set_name][interface_key]
        point_weights = []
        
        for traj_idx, traj_info in enumerate(interface_data.trajectories):
            weight = traj_weights[traj_idx]
            point_weights.append(np.full(traj_info.n_points, weight))
        
        return np.concatenate(point_weights)
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    def _load_all_data(self) -> None:
        """Load all data (structure, descriptors, weights, metadata) from disk."""
        # Load structure
        structure_file = self.path.parent / f"{self.path.name}.structure.json"
        if structure_file.exists():
            with open(structure_file, 'r') as f:
                structure = json.load(f)
            self.sets = {
                set_name: SetData.from_dict(set_data)
                for set_name, set_data in structure.items()
            }
        
        # Load descriptors and shot_results
        descriptors_file = self.path.parent / f"{self.path.name}.descriptors.npz"
        if descriptors_file.exists():
            arrays = np.load(descriptors_file)
            for key in arrays.files:
                if key == 'shot_results':
                    self.shot_results = arrays[key]
                else:
                    self.descriptors[key] = arrays[key]
        
        # Load weights
        weights_file = self.path.parent / f"{self.path.name}.weights.npz"
        if weights_file.exists():
            weights_data = np.load(weights_file)
            for key in weights_data.files:
                set_name, interface_key = key.split('__')
                if set_name not in self.trajectory_weights:
                    self.trajectory_weights[set_name] = {}
                self.trajectory_weights[set_name][interface_key] = weights_data[key]
        
        # Load metadata
        meta_file = self.path.parent / f"{self.path.name}.meta.json"
        if meta_file.exists():
            with open(meta_file, 'r') as f:
                self.metadata = json.load(f)
        
        logger.info(f"Loaded existing data for append mode from {self.path}")
    
    def _compute_total_points(self) -> int:
        """Compute total number of points currently stored."""
        total = 0
        for set_data in self.sets.values():
            for interface_data in set_data.interfaces.values():
                for traj_info in interface_data.trajectories:
                    total += traj_info.n_points
        return total
    
    # ========================================================================
    # I/O
    # ========================================================================
    
    def load_structure(self) -> None:
        """Load structure (JSON metadata) from disk."""
        structure_file = self.path.parent / f"{self.path.name}.structure.json"
        if not structure_file.exists():
            logger.warning(f"Structure file not found: {structure_file}")
            return
        
        with open(structure_file, 'r') as f:
            structure = json.load(f)
        
        self.sets = {
            set_name: SetData.from_dict(set_data)
            for set_name, set_data in structure.items()
        }
        
        logger.info(f"Loaded structure from {structure_file}")
    
    @staticmethod
    def load(path: Union[str, Path], mode: str = 'r') -> 'DescriptorStorage':
        """
        Load descriptor storage from disk.
        
        Parameters
        ----------
        path : str or Path
            Base path (without extensions)
        mode : str
            File mode ('r' for read, 'a' for append)
        
        Returns
        -------
        DescriptorStorage
            Loaded storage instance
        """
        path = Path(path)
        storage = DescriptorStorage(path, mode=mode)
        
        # Load structure
        structure_file = path.parent / f"{path.name}.structure.json"
        if structure_file.exists():
            with open(structure_file, 'r') as f:
                structure = json.load(f)
            storage.sets = {
                set_name: SetData.from_dict(set_data)
                for set_name, set_data in structure.items()
            }
        
        # Load descriptors and shot_results
        descriptors_file = path.parent / f"{path.name}.descriptors.npz"
        if descriptors_file.exists():
            arrays = np.load(descriptors_file)
            for key in arrays.files:
                if key == 'shot_results':
                    storage.shot_results = arrays[key]
                else:
                    storage.descriptors[key] = arrays[key]
        
        # Load weights
        weights_file = path.parent / f"{path.name}.weights.npz"
        if weights_file.exists():
            weights_data = np.load(weights_file)
            for key in weights_data.files:
                set_name, interface_key = key.split('__')
                if set_name not in storage.trajectory_weights:
                    storage.trajectory_weights[set_name] = {}
                storage.trajectory_weights[set_name][interface_key] = weights_data[key]
        
        # Load metadata
        meta_file = path.parent / f"{path.name}.meta.json"
        if meta_file.exists():
            with open(meta_file, 'r') as f:
                storage.metadata = json.load(f)
        
        logger.info(f"✓ Loaded descriptor storage from {path}")
        return storage
    
    def save(self) -> None:
        """Save all data to disk."""
        logger.info(f"Saving descriptor storage to {self.path}...")
        
        # Save structure
        structure = {
            set_name: set_data.to_dict()
            for set_name, set_data in self.sets.items()
        }
        structure_file = self.path.parent / f"{self.path.name}.structure.json"
        with open(structure_file, 'w') as f:
            json.dump(structure, f, indent=2)
        
        # Save descriptors and shot_results
        descriptors_file = self.path.parent / f"{self.path.name}.descriptors.npz"
        arrays_to_save = self.descriptors.copy()
        if self.shot_results is not None:
            arrays_to_save['shot_results'] = self.shot_results
        
        save_fn = np.savez_compressed if self.compress else np.savez
        save_fn(descriptors_file, **arrays_to_save)
        
        # Save weights if present
        if self.trajectory_weights:
            weights_file = self.path.parent / f"{self.path.name}.weights.npz"
            weights_dict = {}
            for set_name, interfaces in self.trajectory_weights.items():
                for interface_key, weights in interfaces.items():
                    key = f"{set_name}__{interface_key}"
                    weights_dict[key] = weights
            save_fn(weights_file, **weights_dict)
        
        # Save metadata
        meta_file = self.path.parent / f"{self.path.name}.meta.json"
        with open(meta_file, 'w') as f:
            json.dump(self.metadata, f, indent=2)
        
        logger.info(f"✓ Saved to {self.path}.*")
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    def summary(self) -> str:
        """Return a summary of the storage contents."""
        lines = [
            "=" * 70,
            "Descriptor Storage Summary",
            "=" * 70,
            f"Method Type: {self.method_type}",
            f"Descriptor Types: {', '.join(self.descriptors.keys())}",
            ""
        ]
        
        total_trajs = 0
        total_points = 0
        
        for set_name, set_data in self.sets.items():
            lines.append(f"Set: {set_name}")
            for interface_key, interface_data in set_data.interfaces.items():
                n_trajs = len(interface_data.trajectories)
                n_pts = sum(t.n_points for t in interface_data.trajectories)
                total_trajs += n_trajs
                total_points += n_pts
                
                has_weights = (set_name in self.trajectory_weights and
                              interface_key in self.trajectory_weights[set_name])
                weight_mark = "✓" if has_weights else " "
                
                lines.append(
                    f"  λ={interface_key}: {n_trajs:4d} trajectories, "
                    f"{n_pts:7d} points [weights: {weight_mark}]"
                )
        
        lines.extend([
            "",
            f"Total: {total_trajs} trajectories, {total_points} points",
            "=" * 70
        ])
        
        return "\n".join(lines)
    
    def __repr__(self) -> str:
        return f"DescriptorStorage({self.path}, mode={self.mode})"

def _interface_key(interface_value: Union[float, str]) -> str:
    """Convert interface value to standardized string key."""
    if isinstance(interface_value, float):
        return f"{interface_value:.2f}"
    return str(interface_value)
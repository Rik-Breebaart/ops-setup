"""
Integration Guide: Using DescriptorStorage with TPS/TIS Simulations

This module shows how to integrate DescriptorStorage into your actual
pathsampling workflow to efficiently capture and store trajectory descriptors
during simulation runs.
"""

import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, Callable
import logging

logger = logging.getLogger(__name__)


class DescriptorComputationManager:
    """
    Manager for computing and storing descriptors during TPS/TIS runs.
    
    Usage:
        # Initialize
        manager = DescriptorComputationManager(
            storage_path='/path/to/descriptors',
            descriptor_functions={'distance': compute_distance, ...},
            compute_frequency=100,  # compute every 100 MC steps
            method_type='TPS'
        )
        
        # Integrate into PathSampling
        manager.setup_callback(pathsampler)
        
        # Run simulation - callbacks called automatically
        pathsampler.run(nsteps=10000)
        
        # Save at end
        manager.finalize()
    """
    
    def __init__(
        self,
        storage_path: Path,
        descriptor_functions: Dict[str, Callable],
        compute_frequency: int = 100,
        method_type: str = 'TPS',
        batch_size: int = 10,
        compress: bool = True
    ):
        """
        Initialize descriptor manager.
        
        Parameters
        ----------
        storage_path : Path
            Where to store descriptor files
        descriptor_functions : Dict[str, Callable]
            Dict mapping descriptor names to functions:
            {
                'distance': lambda snapshot: float,
                'multidim': lambda snapshot: np.ndarray,
                ...
            }
        compute_frequency : int
            Compute descriptors every N MC steps
        method_type : str
            'TPS', 'TIS', 'RETIS', etc.
        batch_size : int
            Number of trajectories to batch before flushing
        compress : bool
            Use compressed storage (np.savez_compressed)
        """
        from ops_setup.descriptor_storage import DescriptorStorage
        
        self.storage_path = Path(storage_path)
        self.descriptor_functions = descriptor_functions
        self.compute_frequency = compute_frequency
        self.method_type = method_type
        self.batch_size = batch_size
        self.compress = compress
        
        # Initialize storage
        self.storage = DescriptorStorage(
            self.storage_path,
            mode='w',
            method_type=method_type,
            use_compression=compress
        )
        
        # Tracking
        self.step_count = 0
        self.trajectory_count = 0
        self.last_flush_step = 0
        
        logger.info(f"Initialized DescriptorComputationManager at {storage_path}")
    
    def compute_trajectory_descriptors(
        self,
        trajectory: Any,  # OPS trajectory or snapshot list
        interface_value: Optional[float] = None
    ) -> Dict[str, np.ndarray]:
        """
        Compute all descriptors for a single trajectory.
        
        Parameters
        ----------
        trajectory : OPS Trajectory
            The trajectory object (or list of snapshots)
        interface_value : float, optional
            Interface lambda value (for TIS/RETIS)
            
        Returns
        -------
        Dict[str, np.ndarray]
            descriptor_name -> array of shape (n_frames, *descriptor_shape)
        """
        n_frames = len(trajectory)
        descriptors = {}
        
        for desc_name, desc_func in self.descriptor_functions.items():
            # Compute for each frame
            values = []
            for snapshot in trajectory:
                value = desc_func(snapshot)
                if not isinstance(value, np.ndarray):
                    value = np.array(value)
                values.append(value)
            
            # Stack into array
            descriptors[desc_name] = np.array(values)
        
        return descriptors
    
    def record_trajectory(
        self,
        trajectory: Any,
        set_name: str = 'ensemble',
        interface_value: float = 0.0
    ):
        """
        Record a new trajectory and its descriptors.
        
        Parameters
        ----------
        trajectory : OPS Trajectory
            The trajectory from the MC move
        set_name : str
            Name of the ensemble (e.g., 'shooting_point_ensemble')
        interface_value : float
            Interface lambda value
        """
        # Compute descriptors
        descriptors = self.compute_trajectory_descriptors(
            trajectory, interface_value
        )
        
        # Add to storage
        self.storage.add_trajectory(
            set_name=set_name,
            interface_value=interface_value,
            descriptors=descriptors,
            n_points=len(trajectory),
            storage_index=self.trajectory_count
        )
        
        self.trajectory_count += 1
        self.step_count += 1
        
        # Periodic flushing
        if self.trajectory_count - self.last_flush_step >= self.batch_size:
            self.storage.flush()
            self.last_flush_step = self.trajectory_count
            logger.info(f"Flushed {self.trajectory_count} trajectories to disk")
    
    def setup_callback(self, pathsampler):
        """
        Attach to pathsampler to record every accepted move.
        
        Parameters
        ----------
        pathsampler : PathSampling
            The pathsampling object from OPS
        """
        original_move = pathsampler.move_engine.move
        manager = self
        
        def move_with_descriptor_recording(samples):
            """Wrapper that records descriptors for accepted moves."""
            result = original_move(samples)
            
            # Record if accepted
            if result.accepted:
                for sample in result.samples:
                    manager.record_trajectory(
                        sample.trajectory,
                        set_name='ensemble',
                        interface_value=getattr(sample, 'ensemble', None)
                    )
            
            return result
        
        # Replace move method
        pathsampler.move_engine.move = move_with_descriptor_recording
        logger.info("Set up descriptor recording callback")
    
    def finalize(self):
        """Final flush and close storage."""
        self.storage.flush()
        self.storage.close()
        logger.info(f"Finalized storage with {self.trajectory_count} trajectories")


# ============================================================================
# INTEGRATION PATTERNS
# ============================================================================

def pattern_1_simple_callback():
    """
    Pattern 1: Simple callback with minimal setup.
    
    Best for: Quick tests, single descriptor
    """
    from ops_setup.descriptor_storage import DescriptorStorage
    
    storage_path = Path("/path/to/descriptors")
    
    def distance_cv(snapshot):
        """Simple distance calculation."""
        return np.linalg.norm(snapshot.xyz[0] - snapshot.xyz[1])
    
    with DescriptorStorage(storage_path, mode='w', method_type='TPS') as storage:
        
        # During simulation loop:
        for step in range(100):
            # ... run MC move ...
            trajectory = None  # result from move
            
            # Compute and store
            distances = np.array([distance_cv(s) for s in trajectory])
            storage.add_trajectory(
                set_name='ensemble',
                interface_value=0.5,
                descriptors={'distance': distances.reshape(-1, 1)},
                n_points=len(trajectory),
                storage_index=step
            )
            
            # Flush periodically
            if step % 20 == 0:
                storage.flush()


def pattern_2_descriptor_manager():
    """
    Pattern 2: Using DescriptorComputationManager.
    
    Best for: Production runs, multiple descriptors, cleaner code
    """
    
    def distance_cv(snapshot):
        return np.linalg.norm(snapshot.xyz[0] - snapshot.xyz[1])
    
    def angle_cv(snapshot):
        v1 = snapshot.xyz[1] - snapshot.xyz[0]
        v2 = snapshot.xyz[2] - snapshot.xyz[0]
        cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
        return np.arccos(np.clip(cos_angle, -1, 1))
    
    # Initialize manager
    manager = DescriptorComputationManager(
        storage_path=Path('/path/to/descriptors'),
        descriptor_functions={
            'distance': distance_cv,
            'angle': angle_cv,
        },
        compute_frequency=100,
        method_type='TIS',
        batch_size=10
    )
    
    # During TIS simulation:
    # pathsampler = ...
    # manager.setup_callback(pathsampler)
    # pathsampler.run(nsteps=10000)
    # manager.finalize()


def pattern_3_incremental_analysis():
    """
    Pattern 3: Incremental analysis during simulation.
    
    Best for: Real-time monitoring, adaptive sampling
    """
    from ops_setup.descriptor_storage import DescriptorStorage
    
    storage_path = Path("/path/to/descriptors")
    
    with DescriptorStorage(storage_path, mode='w', method_type='TPS') as storage:
        
        for step in range(1000):
            # ... simulation step ...
            trajectory = None  # result
            descriptors = {}  # computed
            
            # Add to storage
            storage.add_trajectory(
                set_name='tps',
                interface_value=0.5,
                descriptors=descriptors,
                n_points=len(trajectory),
                storage_index=step
            )
            
            # Periodic analysis (no need to reload storage)
            if step % 100 == 0:
                storage.flush()
                
                # Quick stats
                traj_dists = storage.get_interface_descriptors(
                    'tps', '0.50', 'distance'
                )
                avg_dist = np.mean(traj_dists)
                print(f"Step {step}: avg distance = {avg_dist:.3f}")


def pattern_4_with_weights():
    """
    Pattern 4: RETIS workflow with trajectory weights.
    
    Best for: Weighted ensemble analysis, RETIS
    """
    from ops_setup.descriptor_storage import DescriptorStorage
    
    storage_path = Path("/path/to/descriptors")
    
    with DescriptorStorage(storage_path, mode='w', method_type='RETIS') as storage:
        
        trajectories_at_interface = []
        
        # Collect trajectories
        for step in range(100):
            trajectory = None  # result
            descriptors = {}
            
            storage.add_trajectory(
                set_name='retis_ensemble',
                interface_value=0.5,
                descriptors=descriptors,
                n_points=len(trajectory),
                storage_index=step
            )
            
            trajectories_at_interface.append(step)
        
        storage.flush()
    
    # After simulation, add weights for RETIS
    storage = DescriptorStorage.load(storage_path, mode='a')
    
    # Compute weights (e.g., from committor analysis)
    weights = np.random.rand(len(trajectories_at_interface))
    weights /= weights.sum()  # normalize
    
    storage.set_trajectory_weights(
        'retis_ensemble', '0.50', weights
    )
    
    # Can now compute per-point weights
    point_weights = storage.get_interface_weights('retis_ensemble', '0.50')
    print(f"Per-point weights shape: {point_weights.shape}")


# ============================================================================
# REAL OPS INTEGRATION EXAMPLE
# ============================================================================

class TPSWithDescriptorStorage:
    """
    Complete TPS workflow with descriptor storage integration.
    
    Usage:
        setup = TPSWithDescriptorStorage(
            trajectory_file='trajectory.dcd',
            topology_file='system.pdb',
            descriptor_functions={'distance': dist_cv, ...}
        )
        setup.run(nsteps=10000)
        setup.analyze()
    """
    
    def __init__(
        self,
        trajectory_file: str,
        topology_file: str,
        descriptor_functions: Dict[str, Callable],
        descriptor_path: Optional[str] = None
    ):
        """Initialize TPS setup."""
        from ops_setup.descriptor_storage import DescriptorStorage
        
        self.trajectory_file = trajectory_file
        self.topology_file = topology_file
        self.descriptor_functions = descriptor_functions
        
        self.descriptor_path = Path(descriptor_path or 'descriptors')
        self.descriptor_manager = DescriptorComputationManager(
            storage_path=self.descriptor_path,
            descriptor_functions=descriptor_functions,
            method_type='TPS',
            batch_size=20
        )
    
    def run(self, nsteps: int = 10000):
        """
        Run TPS simulation with descriptor recording.
        
        Parameters
        ----------
        nsteps : int
            Number of TPS MC steps
        """
        # Setup would happen here
        # pathsampler = ...
        # self.descriptor_manager.setup_callback(pathsampler)
        # pathsampler.run(nsteps=nsteps)
        # self.descriptor_manager.finalize()
        
        logger.info(f"Completed TPS run with {nsteps} steps")
    
    def analyze(self):
        """Analyze stored descriptors."""
        from ops_setup.descriptor_storage import DescriptorStorage
        
        storage = DescriptorStorage.load(self.descriptor_path, mode='r')
        
        print("\n" + storage.summary())
        
        # Get all distances
        distances = storage.get_interface_descriptors('ensemble', '0.50', 'distance')
        print(f"\nDescriptor statistics:")
        print(f"  Mean: {np.mean(distances):.3f}")
        print(f"  Std:  {np.std(distances):.3f}")
        print(f"  Min:  {np.min(distances):.3f}")
        print(f"  Max:  {np.max(distances):.3f}")

"""
General guide and examples for using OpenMMGromacs classes.

This module provides templates and examples for setting up different
types of systems with the OpenMMGromacs and OpenMMGromacsTPS classes.
"""

from pathlib import Path
from typing import Tuple, Dict, Any, Callable
import openpathsampling as paths
from ops_setup.engines.openmm_from_gromacs import (
    OpenMMGromacs,
    OpenMMGromacsTPS,
    GromacsCVFactory
)


# ============================================================================
# EXAMPLE 1: Minimal Setup - Just run MD from GROMACS
# ============================================================================

class Example1_MinimalMDSetup:
    """
    Minimal example: Load GROMACS files and run MD with OpenMM.
    
    This is the simplest use case - just run molecular dynamics
    without path sampling.
    """
    
    @staticmethod
    def run(topology_file: Path, structure_file: Path, 
            forcefield_dir: Path, output_dir: Path):
        """
        Run simple MD simulation.
        
        Parameters
        ----------
        topology_file : Path
            Path to .top file
        structure_file : Path
            Path to .gro file
        forcefield_dir : Path
            Path to force field directory
        output_dir : Path
            Output directory for trajectories
        """
        
        # Configuration
        config = {
            'temperature': 300.0,
            'pressure': 1.0,
            'timestep': 0.002,
            'friction': 1.0,
            'platform': 'CUDA',
            'precision': 'mixed',
        }
        
        # Create OpenMM simulation
        openmm = OpenMMGromacs(
            topology_file,
            structure_file,
            forcefield_dir,
            config=config
        )
        
        # Minimize energy
        openmm.minimize_energy()
        
        # Add reporters
        output_dir.mkdir(parents=True, exist_ok=True)
        openmm.add_reporter('StateData', output_dir / 'energy.csv', interval=2500)
        openmm.add_reporter('DCD', output_dir / 'trajectory.dcd', interval=2500)
        openmm.add_reporter('PDB', output_dir / 'final.pdb', interval=500000)
        
        # Run 500 ns
        openmm.run(250000)  # 500 ps with dt=0.002 ps
        
        return openmm


# ============================================================================
# EXAMPLE 2: Simple TPS - Two-state system with one CV
# ============================================================================

class Example2_SimpleTPS:
    """
    Simple example: Two-state TPS with a single distance CV.
    
    Use this template for simple systems where states can be defined
    by a single collective variable.
    """
    
    @staticmethod
    def setup_simple_cv(topology, atom_i: int, atom_j: int) -> paths.CollectiveVariable:
        """Create a simple distance CV."""
        cv_factory = GromacsCVFactory(topology)
        return cv_factory.distance_cv(
            f'distance_{atom_i}_{atom_j}',
            atom_indices=(atom_i, atom_j)
        )
    
    @staticmethod
    def define_states(cv: paths.CollectiveVariable,
                     state_a_bounds: Tuple[float, float],
                     state_b_bounds: Tuple[float, float]):
        """Define two states based on CV bounds."""
        state_a = paths.CVDefinedVolume(cv, *state_a_bounds).named('state_A')
        state_b = paths.CVDefinedVolume(cv, *state_b_bounds).named('state_B')
        return state_a, state_b
    
    @staticmethod
    def run(topology_file: Path, structure_file: Path,
            forcefield_dir: Path, atom_i: int, atom_j: int,
            state_a_bounds: Tuple[float, float],
            state_b_bounds: Tuple[float, float]) -> Tuple[OpenMMGromacsTPS, paths.TPSNetwork]:
        """
        Set up simple TPS.
        
        Parameters
        ----------
        topology_file : Path
            Path to .top file
        structure_file : Path
            Path to .gro file
        forcefield_dir : Path
            Path to force field directory
        atom_i, atom_j : int
            Atom indices for distance CV
        state_a_bounds : tuple
            (min, max) distance for state A
        state_b_bounds : tuple
            (min, max) distance for state B
        """
        
        config = {
            'temperature': 300.0,
            'pressure': 1.0,
            'timestep': 0.002,
            'friction': 1.0,
            'platform': 'CUDA',
        }
        
        # Create core OpenMM setup (we'll extract the topology)
        openmm_temp = OpenMMGromacs(
            topology_file, structure_file, forcefield_dir, config
        )
        
        # Create CVs
        cv = Example2_SimpleTPS.setup_simple_cv(
            openmm_temp.topology, atom_i, atom_j
        )
        
        # Define states
        state_a, state_b = Example2_SimpleTPS.define_states(
            cv, state_a_bounds, state_b_bounds
        )
        
        # Create TPS setup
        state_definitions = {
            'stateA': {
                'cvs': [cv],
                'bounds': [state_a_bounds]
            },
            'stateB': {
                'cvs': [cv],
                'bounds': [state_b_bounds]
            }
        }
        
        tps_setup = OpenMMGromacsTPS(
            topology_file,
            structure_file,
            forcefield_dir,
            state_definitions=state_definitions,
            config=config,
            n_frames_max=5000,
            n_steps_per_frame=500
        )
        
        # Create network
        network = tps_setup.create_tps_network()
        
        return tps_setup, network


# ============================================================================
# EXAMPLE 3: Advanced TPS - Multi-dimensional state space
# ============================================================================

class Example3_AdvancedTPS:
    """
    Advanced example: TPS with multiple collective variables.
    
    Use this for systems where states need to be defined as intersections
    of multiple CV constraints (e.g., protein folding, binding).
    """
    
    @staticmethod
    def setup_multi_cvs(topology,
                       cv_definitions: Dict[str, Dict[str, Any]]) -> Dict[str, paths.CollectiveVariable]:
        """
        Create multiple collective variables.
        
        Parameters
        ----------
        topology : Topology
            OpenMM topology
        cv_definitions : dict
            Dictionary mapping CV names to definitions:
            {
                'cv_name': {
                    'type': 'distance' | 'position' | 'min_distance' | 'custom',
                    'atom_indices': tuple or 'group1': tuple, 'group2': tuple,
                    'axis': 'x'|'y'|'z' (for position),
                    'function': callable (for custom)
                },
                ...
            }
        """
        
        cv_factory = GromacsCVFactory(topology)
        cvs = {}
        
        for cv_name, cv_def in cv_definitions.items():
            cv_type = cv_def['type']
            
            if cv_type == 'distance':
                cvs[cv_name] = cv_factory.distance_cv(
                    cv_name,
                    cv_def['atom_indices']
                )
            
            elif cv_type == 'position':
                cvs[cv_name] = cv_factory.position_cv(
                    cv_name,
                    cv_def['atom_index'],
                    cv_def.get('axis', 'x')
                )
            
            elif cv_type == 'min_distance':
                cvs[cv_name] = cv_factory.minimum_distance_cv(
                    cv_name,
                    cv_def['group1'],
                    cv_def['group2']
                )
            
            elif cv_type == 'custom':
                cvs[cv_name] = cv_factory.custom_cv(
                    cv_name,
                    cv_def['function'],
                    cv_def.get('arg', None)
                )
            
            else:
                raise ValueError(f"Unknown CV type: {cv_type}")
        
        return cvs
    
    @staticmethod
    def define_multi_state(cvs: Dict[str, paths.CollectiveVariable],
                          state_bounds: Dict[str, Tuple[float, float]],
                          state_name: str) -> paths.Volume:
        """
        Define a state as intersection of multiple CV constraints.
        
        Parameters
        ----------
        cvs : dict
            Dictionary of CVs
        state_bounds : dict
            CV bounds: {'cv_name': (min, max), ...}
        state_name : str
            Name for the state
        """
        
        volume = None
        for cv_name, (min_val, max_val) in state_bounds.items():
            if cv_name not in cvs:
                raise ValueError(f"CV not found: {cv_name}")
            
            cv_volume = paths.CVDefinedVolume(cvs[cv_name], min_val, max_val)
            
            if volume is None:
                volume = cv_volume
            else:
                volume = volume & cv_volume
        
        return volume.named(state_name)
    
    @staticmethod
    def run(topology_file: Path,
            structure_file: Path,
            forcefield_dir: Path,
            cv_definitions: Dict[str, Dict[str, Any]],
            state_definitions: Dict[str, Dict[str, Tuple[float, float]]]) -> Tuple[OpenMMGromacsTPS, paths.TPSNetwork]:
        """
        Set up advanced TPS with multiple CVs.
        
        Parameters
        ----------
        topology_file : Path
            Path to .top file
        structure_file : Path
            Path to .gro file
        forcefield_dir : Path
            Path to force field directory
        cv_definitions : dict
            CV definitions (see setup_multi_cvs)
        state_definitions : dict
            State definitions:
            {
                'stateA': {'cv_name': (min, max), ...},
                'stateB': {'cv_name': (min, max), ...},
                ...
            }
        """
        
        config = {
            'temperature': 300.0,
            'pressure': 1.0,
            'timestep': 0.002,
            'friction': 1.0,
            'platform': 'CUDA',
        }
        
        # Create core OpenMM setup
        openmm_temp = OpenMMGromacs(
            topology_file, structure_file, forcefield_dir, config
        )
        
        # Create all CVs
        cvs = Example3_AdvancedTPS.setup_multi_cvs(
            openmm_temp.topology, cv_definitions
        )
        
        # Create OPS state definitions from CV bounds
        ops_state_defs = {}
        for state_name in ['stateA', 'stateB']:
            if state_name not in state_definitions:
                raise ValueError(f"Missing state definition: {state_name}")
            
            state_bounds = state_definitions[state_name]
            
            # Get CV objects and bounds for TPS
            state_cvs = [cvs[cv_name] for cv_name in state_bounds.keys()]
            state_bounds_list = [state_bounds[cv_name] for cv_name in state_bounds.keys()]
            
            ops_state_defs[state_name] = {
                'cvs': state_cvs,
                'bounds': state_bounds_list
            }
        
        # Create TPS setup
        tps_setup = OpenMMGromacsTPS(
            topology_file,
            structure_file,
            forcefield_dir,
            state_definitions=ops_state_defs,
            config=config,
            n_frames_max=5000,
            n_steps_per_frame=500
        )
        
        # Create network
        network = tps_setup.create_tps_network()
        
        return tps_setup, network


# ============================================================================
# EXAMPLE 4: Custom CV Definition
# ============================================================================

class Example4_CustomCV:
    """
    Example: Define custom collective variables from scratch.
    
    Use this when you need specialized CVs not provided by the factory.
    """
    
    @staticmethod
    def radius_of_gyration_cv(topology) -> paths.CollectiveVariable:
        """Create a radius of gyration CV."""
        
        def rg_calc(frame, topology_obj):
            """Calculate radius of gyration."""
            try:
                xyz = frame.xyz
            except AttributeError:
                xyz = frame.coordinates
            
            if xyz is None or len(xyz) == 0:
                return 0.0
            
            # Center of mass
            com = xyz.mean(axis=0)
            
            # RG
            rg_sq = ((xyz - com) ** 2).sum(axis=1).mean()
            return rg_sq ** 0.5
        
        return paths.FunctionCV(
            'radius_of_gyration',
            rg_calc,
            topology,
            arg=None
        )
    
    @staticmethod
    def helix_content_cv(topology, residue_indices) -> paths.CollectiveVariable:
        """Create a helix content CV (requires MDTraj)."""
        
        def helix_calc(frame, res_indices):
            """Calculate fraction of helical residues."""
            try:
                import mdtraj as md
                traj = md.Trajectory(frame.xyz.reshape(1, -1, 3), topology=None)
                # This is a placeholder - actual helix detection is complex
                return 0.5
            except ImportError:
                return 0.0
        
        return paths.FunctionCV(
            'helix_content',
            helix_calc,
            topology,
            arg=residue_indices
        )


# ============================================================================
# Usage Guide
# ============================================================================

"""
QUICK START GUIDE
=================

1. MINIMAL MD SETUP (No path sampling):
   
   >>> openmm = Example1_MinimalMDSetup.run(
   ...     topology_file='system.top',
   ...     structure_file='system.gro',
   ...     forcefield_dir='ff/',
   ...     output_dir='output/'
   ... )

2. SIMPLE TPS (One distance CV):
   
   >>> tps, network = Example2_SimpleTPS.run(
   ...     topology_file='system.top',
   ...     structure_file='system.gro',
   ...     forcefield_dir='ff/',
   ...     atom_i=10,
   ...     atom_j=200,
   ...     state_a_bounds=(0.1, 0.2),
   ...     state_b_bounds=(0.8, 1.0)
   ... )

3. ADVANCED TPS (Multiple CVs):
   
   >>> cv_defs = {
   ...     'distance_1': {
   ...         'type': 'distance',
   ...         'atom_indices': (10, 200),
   ...     },
   ...     'distance_2': {
   ...         'type': 'min_distance',
   ...         'group1': (5, 10, 15),
   ...         'group2': (195, 200, 205),
   ...     }
   ... }
   >>> state_defs = {
   ...     'stateA': {
   ...         'distance_1': (0.1, 0.2),
   ...         'distance_2': (1.0, 1.5),
   ...     },
   ...     'stateB': {
   ...         'distance_1': (0.8, 1.0),
   ...         'distance_2': (3.0, 3.5),
   ...     }
   ... }
   >>> tps, network = Example3_AdvancedTPS.run(
   ...     topology_file='system.top',
   ...     structure_file='system.gro',
   ...     forcefield_dir='ff/',
   ...     cv_definitions=cv_defs,
   ...     state_definitions=state_defs
   ... )

4. CUSTOM CV:
   
   >>> rg_cv = Example4_CustomCV.radius_of_gyration_cv(topology)
   >>> # Use in state definitions...
"""

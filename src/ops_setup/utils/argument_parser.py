"""
Argument parser utilities for OPS-based simulations.

This module provides utilities for creating command-line argument parsers
with commonly used arguments for TPS/TIS simulations.
"""

import argparse
from pathlib import Path
from typing import List, Dict, Union, Tuple, Any


def create_parser(arguments_list: List[Union[Tuple, Dict]]) -> argparse.ArgumentParser:
    """
    Creates an ArgumentParser with arguments specified in arguments_list.

    Parameters
    ----------
    arguments_list : list
        List of tuples or dictionaries defining arguments:
        - If tuple: (flags, type, required, help_text, [default], [nargs])
        - If dictionary: {
            "flags": list of flags (e.g., ["-d", "--directory"]),
            "type": argument type (e.g., str, int, Path),
            "required": if the argument is required,
            "help": help message for the argument,
            "default": (optional) default value if argument is not provided,
            "nargs": (optional) number of arguments expected (e.g., "+", "*")
          }

    Returns
    -------
    argparse.ArgumentParser
        Configured ArgumentParser with all specified arguments.

    Examples
    --------
    >>> args_list = [
    ...     (["-d", "--directory"], Path, True, "Working directory"),
    ...     (["-n", "--n_steps"], int, True, "Number of MC steps", 1000)
    ... ]
    >>> parser = create_parser(args_list)
    """
    parser = argparse.ArgumentParser()
    
    for arg in arguments_list:
        if isinstance(arg, tuple):  # Handle tuple format
            # Unpack flags, type, required, help_text, with optional default and nargs
            flags, arg_type, required, help_text, *rest = arg
            default = rest[0] if len(rest) > 0 and not isinstance(rest[0], str) else None
            nargs = rest[1] if len(rest) > 1 and isinstance(rest[1], str) else None
            
            # Add the argument to the parser
            parser.add_argument(
                *flags,
                type=arg_type,
                required=required,
                help=help_text,
                default=default,
                nargs=nargs
            )
        elif isinstance(arg, dict):  # Handle dictionary format
            # Add the argument to the parser using dict keys
            parser.add_argument(
                *arg["flags"],
                type=arg["type"],
                required=arg.get("required", False),
                help=arg.get("help", ""),
                default=arg.get("default", None),
                nargs=arg.get("nargs", None)
            )
    
    return parser


# Global argument dictionary for common TPS/TIS arguments
COMMON_ARGUMENTS = {
    "directory": (
        ["-dir", "--directory"], 
        Path, 
        True, 
        "Directory containing initial trajectory and configuration files."
    ),
    "config_file": (
        ["-cfg", "--config_file"], 
        str, 
        True, 
        "File in JSON format with simulation settings."
    ),
    "n_steps": (
        ["-nr", "--n_steps"], 
        int, 
        True, 
        "The number of desired TPS/TIS MC cycles."
    ),
    "output_path": (
        ["-out", "--output_path"], 
        Path, 
        False, 
        "Directory for storing TPS output files."
    ),
    "ops_store": (
        ["-ops_store", "--ops_store"], 
        str, 
        False, 
        "Name for output OPS storage."
    ),
    "trajectory_path": (
        ["-traj", "--trajectory_path"], 
        Path, 
        False, 
        "Path to the input trajectory storage file."
    ),
    "save_final_traj": (
        ["-save_traj", "--save_final_traj"], 
        bool, 
        False, 
        "Flag to save the final trajectory as a separate OPS storage.", 
        True
    ),
    "final_traj_storage_path": (
        ["-final_traj_store", "--final_traj_storage_path"], 
        str, 
        False, 
        "Path to save the final trajectory storage file."
    ),
    "system_resource_directory": (
        ["-sys_source_dir", "--system_resource_directory"], 
        Path, 
        False, 
        "Directory for system resource files."
    ),
}

# TPS-specific arguments
TPS_ARGUMENTS = {
    **COMMON_ARGUMENTS,
}

# TIS-specific arguments
TIS_ARGUMENTS = {
    **COMMON_ARGUMENTS,
    "config_file_TPS": (
        ["-cfg_TPS", "--config_file_TPS"], 
        str, 
        True, 
        "File in JSON format with TPS simulation settings."
    ),
    "config_file_TIS": (
        ["-cfg_TIS", "--config_file_TIS"], 
        str, 
        True, 
        "File in JSON format with TIS settings."
    ),
    "interface_values": (
        ["-interface_values", "--interface_values"], 
        float, 
        True, 
        "The value of the interface used in the simulation.", 
        None, 
        "+"
    ),
    "direction": (
        ["-direction", "--direction"], 
        str, 
        True, 
        "The direction of the simulation, either 'forward' or 'backward'."
    ),
}


def get_tps_parser() -> argparse.ArgumentParser:
    """
    Get a pre-configured argument parser for TPS simulations.

    Returns
    -------
    argparse.ArgumentParser
        Parser with common TPS arguments.
    """
    return create_parser(list(TPS_ARGUMENTS.values()))


def get_tis_parser() -> argparse.ArgumentParser:
    """
    Get a pre-configured argument parser for TIS simulations.

    Returns
    -------
    argparse.ArgumentParser
        Parser with common TIS arguments.
    """
    return create_parser(list(TIS_ARGUMENTS.values()))

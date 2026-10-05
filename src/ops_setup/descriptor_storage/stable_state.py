"""Stable-state payload helpers built on top of DescriptorStorage.

These helpers persist stable-state descriptor data in the same canonical storage
format used for TPS/TIS descriptor streams. Stable-state runs are stored under
the set name ``stable`` with interface labels such as ``A`` and ``B``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Optional, Sequence, Union

import numpy as np

from .descriptor_storage import DescriptorStorage


def _as_2d_array(values: Any) -> np.ndarray:
    arr = np.asarray(values)
    if arr.ndim == 1:
        return arr.reshape(-1, 1)
    return arr


def build_stable_state_storage(
    storage_paths: Sequence[Any],
    descriptor_transform: Callable,
    output_path: Union[str, Path],
    state_volumes: Optional[Sequence[Callable]] = None,
    state_labels: Optional[Sequence[str]] = None,
    descriptor_name: str = "descriptors",
    set_name: str = "stable",
    method_type: str = "stable-state",
    include_shot_results: bool = True,
) -> DescriptorStorage:
    """Build canonical descriptor storage for stable-state trajectories.

    Parameters
    ----------
    storage_paths
        Sequence of OPS storages or paths, one per stable state.
    descriptor_transform
        Callable applied to each trajectory.
    output_path
        Base path for DescriptorStorage files.
    state_volumes
        Optional per-state OPS volumes used to compute in-state masks.
    state_labels
        Labels for the stable states. Defaults to ``A``, ``B``, ...
    descriptor_name
        Key under which the main descriptor array is stored.
    set_name
        Set name used in DescriptorStorage. Defaults to ``stable``.
    method_type
        Storage metadata label. Defaults to ``stable-state``.
    include_shot_results
        Store constant stable-state shot results compatible with AIMMD/RPE flows.
    """
    if state_labels is None:
        state_labels = [chr(ord("A") + i) for i in range(len(storage_paths))]
    if len(state_labels) != len(storage_paths):
        raise ValueError("state_labels length must match storage_paths length.")
    if state_volumes is not None and len(state_volumes) != len(storage_paths):
        raise ValueError("state_volumes length must match storage_paths length.")

    with DescriptorStorage(output_path, mode="w", method_type=method_type) as storage:
        storage.metadata.update(
            {
                "payload_kind": "stable_state",
                "stable_set_name": set_name,
                "stable_state_labels": list(state_labels),
                "descriptor_name": descriptor_name,
                "point_data_fields": ["in_state"],
            }
        )

        for state_idx, (label, storage_obj) in enumerate(zip(state_labels, storage_paths)):
            close_after = False
            ops_storage = storage_obj
            if isinstance(storage_obj, (str, Path)):
                import openpathsampling as paths
                if Path(storage_obj).suffix in {".nc"}:

                    ops_storage = paths.Storage(str(storage_obj), "r")
                    close_after = True
                elif Path(storage_obj).suffix in {".db"}:
                    from openpathsampling.experimental.storage import monkey_patch_all
                    from openpathsampling.experimental.storage import Storage
                    paths = monkey_patch_all(paths)
                    ops_storage = Storage(str(storage_obj), "r", format="HDF5")
                    close_after = True

            state_volume = None if state_volumes is None else state_volumes[state_idx]
            n_states = len(state_labels)

            try:
                for traj_idx, traj in enumerate(ops_storage.trajectories):
                    descriptors = _as_2d_array(descriptor_transform(traj))
                    n_points = descriptors.shape[0]
                    if state_volume is None:
                        in_state = np.ones((n_points, 1), dtype=np.uint8)
                    else:
                        in_state = np.asarray(
                            [bool(state_volume(snapshot)) for snapshot in traj],
                            dtype=np.uint8,
                        ).reshape(-1, 1)

                    shot_results = None
                    if include_shot_results:
                        shot_results = np.zeros((n_points, n_states), dtype=float)
                        shot_results[:, state_idx] = 2.0

                    storage.add_trajectory(
                        set_name=set_name,
                        interface_value=label,
                        descriptors={descriptor_name: descriptors},
                        n_points=n_points,
                        storage_index=traj_idx,
                        shot_results=shot_results,
                        point_data={"in_state": in_state},
                    )
            finally:
                if close_after:
                    ops_storage.close()

    return DescriptorStorage.load(output_path, mode="r")


def load_stable_state_payload(
    storage_path: Union[str, Path],
    descriptor_name: Optional[str] = None,
    set_name: Optional[str] = None,
    state_labels: Optional[Sequence[str]] = None,
) -> dict[str, Any]:
    """Load a stable-state payload from DescriptorStorage into RPE-ready form."""
    storage = DescriptorStorage.load(storage_path, mode="r")

    meta = storage.metadata or {}
    descriptor_name = descriptor_name or meta.get("descriptor_name", "descriptors")
    set_name = set_name or meta.get("stable_set_name", "stable")
    if state_labels is None:
        state_labels = meta.get("stable_state_labels") or sorted(storage.sets.get(set_name, {}).interfaces.keys())

    descriptors = []
    shot_results = []
    in_state_flags = []

    for label in state_labels:
        descriptors.append(storage.get_interface_descriptors(set_name, label, [descriptor_name]))
        shot = storage.get_interface_shot_results(set_name, label)
        shot_results.append(shot if shot is not None else None)
        flags = storage.get_interface_point_data(set_name, label, "in_state")
        in_state_flags.append(np.asarray(flags).reshape(-1).astype(bool))

    payload = {
        "descriptors": descriptors,
        "shot_results": shot_results,
        "in_state_flags": in_state_flags,
        "meta": {
            "descriptor_name": descriptor_name,
            "set_name": set_name,
            "state_labels": list(state_labels),
            **meta,
        },
    }
    return payload
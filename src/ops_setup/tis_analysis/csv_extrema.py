"""Read TIS extrema CSV files using rpe_mbar-compatible loaders."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

def find_cv_extrema_csvs(folder, direction=None):
    """Return sorted extrema CSV paths from a folder.

    Parameters
    ----------
    folder
        Directory containing ``cv_extrema_int*_<direction>.csv`` files.
    direction
        Optional direction filter (``forward`` or ``backward``).
    """
    folder = Path(folder)
    if direction is None:
        pattern = "cv_extrema_int*_*.csv"
    else:
        pattern = f"cv_extrema_int*_{direction}.csv"
    return sorted(folder.glob(pattern))


def load_cv_extrema_frames(csv_paths):
    """Read extrema CSV files as pandas DataFrames."""
    return [pd.read_csv(path) for path in csv_paths]

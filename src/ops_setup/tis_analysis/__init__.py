"""TIS analysis helpers.

This package contains small analysis utilities that bridge ops-setup sampling
outputs to downstream analysis tools such as rpe_mbar.
"""

from .csv_extrema import (
    find_cv_extrema_csvs,
    load_cv_extrema_frames,
)

__all__ = [
    "find_cv_extrema_csvs",
    "load_cv_extrema_frames",
]
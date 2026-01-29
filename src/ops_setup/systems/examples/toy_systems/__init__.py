"""Toy system setups."""

from .setup import ToyTPSSetup, ToyTISSetup
from .toy_potentials import (
    potential_0, potential_1, potential_2, potential_3,
    potential_4_linear, potential_5_Z_pot
)

__all__ = [
    'ToyTPSSetup',
    'ToyTISSetup',
    'potential_0',
    'potential_1',
    'potential_2',
    'potential_3',
    'potential_4_linear',
    'potential_5_Z_pot',
]

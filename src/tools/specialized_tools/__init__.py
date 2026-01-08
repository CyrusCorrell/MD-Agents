"""
Protein MD Simulation - Specialized Tools

This module provides managers for protein molecular dynamics simulations
using OpenMM, WESTPA, and ChimeraX.
"""

from .file_manager import FileManager
from .structure_creator import StructureCreator
from .forcefield_manager import ForceFieldManager
from .openmm_manager import OpenMMManager
from .slurm_manager import SLURMManager
from .westpa_manager import WESTPAManager
from .chimerax_manager import ChimeraXManager

# Legacy imports for backwards compatibility (can be removed later)
try:
    from .potential_manager import PotentialManager
except ImportError:
    PotentialManager = None

try:
    from .hpc_manager import HPCManager
except ImportError:
    HPCManager = None

__all__ = [
    # Core managers
    'FileManager',
    'StructureCreator',
    'ForceFieldManager',
    'OpenMMManager',
    'SLURMManager',
    'WESTPAManager',
    'ChimeraXManager',
    # Legacy (for backwards compatibility)
    'PotentialManager',
    'HPCManager',
]
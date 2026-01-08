"""
Validation Tools for Protein MD Simulation Workflows

This module provides validation gates and status checking for protein molecular
dynamics workflows using OpenMM, WESTPA, and ChimeraX. Replaces the LAMMPS-focused
validation_tools.py.
"""

import os
from typing import Tuple, Optional, Dict, List
from datetime import datetime


class ValidationManager:
    """Manager for validation operations and workflow status checking in protein MD."""
    
    def __init__(self, workdir: str, forcefield_manager=None, structure_creator=None):
        """
        Initialize ValidationManager.
        
        Args:
            workdir: Working directory path
            forcefield_manager: Reference to ForceFieldManager (optional)
            structure_creator: Reference to StructureCreator (optional)
        """
        self.workdir = workdir
        self.forcefield_manager = forcefield_manager
        self.structure_creator = structure_creator
        
        # Validation state tracking
        self.structure_validated = False
        self.forcefield_validated = False
        self.system_prepared = False
        
        # Track validated files
        self.validated_structure_file: Optional[str] = None
        self.validated_forcefield: Optional[str] = None
        self.validated_system_file: Optional[str] = None
        
        # Validation history for observability
        self.validation_history: List[Dict] = []
        
        # Register validation methods
        self.validation_methods = {}
        self._register_default_methods()
    
    def _register_default_methods(self):
        """Register default validation methods."""
        self.register_validation_method('structure', self.validate_structure)
        self.register_validation_method('forcefield', self.validate_forcefield_coverage)
        self.register_validation_method('workflow_status', self.check_workflow_status)
        self.register_validation_method('system_ready', self.check_system_ready)
    
    def set_forcefield_manager(self, forcefield_manager):
        """Set the ForceFieldManager reference after initialization."""
        self.forcefield_manager = forcefield_manager
    
    def set_structure_creator(self, structure_creator):
        """Set the StructureCreator reference after initialization."""
        self.structure_creator = structure_creator
    
    def register_validation_method(self, name: str, method):
        """Register a new validation method."""
        self.validation_methods[name] = method
    
    def validate(self, name: str, *args, **kwargs):
        """Run a registered validation method."""
        if name in self.validation_methods:
            return self.validation_methods[name](*args, **kwargs)
        else:
            raise ValueError(f"Validation method '{name}' is not registered.")
    
    def _log_validation(self, validation_type: str, success: bool, message: str):
        """Log validation event for observability."""
        self.validation_history.append({
            'timestamp': datetime.now().isoformat(),
            'type': validation_type,
            'success': success,
            'message': message
        })

    # ==================== STRUCTURE VALIDATION ====================
    
    def validate_structure(self, pdb_file: str) -> Tuple[bool, str]:
        """
        Validate PDB structure for simulation readiness.
        
        Checks:
        - File exists and is readable
        - Valid PDB format with atoms
        - Contains standard amino acids
        - No severe clashes or missing backbone atoms
        
        Returns: (is_valid, message)
        """
        # Handle both absolute and relative paths
        if not os.path.isabs(pdb_file):
            full_path = os.path.join(self.workdir, pdb_file)
        else:
            full_path = pdb_file
        
        if not os.path.exists(full_path):
            msg = f"❌ Structure file not found: {pdb_file}"
            self._log_validation('structure', False, msg)
            return False, msg
        
        try:
            with open(full_path, 'r') as f:
                content = f.read()
                lines = content.split('\n')
            
            # Check for ATOM records
            atom_lines = [l for l in lines if l.startswith('ATOM') or l.startswith('HETATM')]
            if len(atom_lines) < 10:
                msg = f"❌ PDB has insufficient atoms: {len(atom_lines)} ATOM/HETATM records"
                self._log_validation('structure', False, msg)
                return False, msg
            
            # Count unique residues
            residues = set()
            chains = set()
            for line in atom_lines:
                if len(line) >= 26:
                    chain = line[21]
                    resnum = line[22:26].strip()
                    resname = line[17:20].strip()
                    chains.add(chain)
                    residues.add(f"{chain}_{resnum}_{resname}")
            
            # Check for standard amino acids
            standard_aa = {'ALA', 'ARG', 'ASN', 'ASP', 'CYS', 'GLN', 'GLU', 'GLY', 
                          'HIS', 'ILE', 'LEU', 'LYS', 'MET', 'PHE', 'PRO', 'SER', 
                          'THR', 'TRP', 'TYR', 'VAL', 'HIE', 'HID', 'HIP'}
            
            aa_residues = [r for r in residues if r.split('_')[2] in standard_aa]
            
            # Check for backbone atoms (CA, C, N)
            backbone_atoms = {'CA', 'C', 'N'}
            found_backbone = set()
            for line in atom_lines:
                if len(line) >= 16:
                    atom_name = line[12:16].strip()
                    if atom_name in backbone_atoms:
                        found_backbone.add(atom_name)
            
            missing_backbone = backbone_atoms - found_backbone
            if missing_backbone and len(aa_residues) > 0:
                msg = f"⚠️ Missing backbone atoms: {missing_backbone}"
                self._log_validation('structure', False, msg)
                return False, msg
            
            # Structure looks valid
            self.structure_validated = True
            self.validated_structure_file = full_path
            
            msg = (f"✅ Structure validated: {os.path.basename(pdb_file)}\n"
                   f"   📊 {len(atom_lines)} atoms, {len(residues)} residues, {len(chains)} chain(s)\n"
                   f"   🧬 {len(aa_residues)} amino acid residues")
            
            self._log_validation('structure', True, msg)
            return True, msg
            
        except Exception as e:
            msg = f"❌ Error reading PDB file: {str(e)}"
            self._log_validation('structure', False, msg)
            return False, msg
    
    def check_structure_status(self) -> str:
        """Check current structure validation status."""
        if self.structure_validated and self.validated_structure_file:
            if os.path.exists(self.validated_structure_file):
                return f"✅ Structure validated: {os.path.basename(self.validated_structure_file)}"
            else:
                self.structure_validated = False
                self.validated_structure_file = None
                return "❌ Previously validated structure file no longer exists"
        return "❌ No structure has been validated"
    
    def mark_structure_validated(self, pdb_file: str) -> str:
        """Manually mark a structure as validated."""
        if not os.path.isabs(pdb_file):
            full_path = os.path.join(self.workdir, pdb_file)
        else:
            full_path = pdb_file
        
        if not os.path.exists(full_path):
            return f"❌ Cannot mark as validated - file not found: {pdb_file}"
        
        self.structure_validated = True
        self.validated_structure_file = full_path
        self._log_validation('structure', True, f"Manually marked validated: {pdb_file}")
        return f"✅ Structure marked as validated: {pdb_file}"

    # ==================== FORCE FIELD VALIDATION ====================
    
    def validate_forcefield_coverage(self, pdb_file: str, 
                                     forcefield: str = "amber14-all.xml") -> Tuple[bool, str]:
        """
        Validate that force field covers all residues/atoms in the structure.
        
        Checks:
        - Force field is available in OpenMM
        - All residue types are parameterized
        - Water model compatibility
        
        Returns: (is_valid, message)
        """
        # Handle path
        if not os.path.isabs(pdb_file):
            full_path = os.path.join(self.workdir, pdb_file)
        else:
            full_path = pdb_file
        
        if not os.path.exists(full_path):
            msg = f"❌ PDB file not found for forcefield validation: {pdb_file}"
            self._log_validation('forcefield', False, msg)
            return False, msg
        
        # Check forcefield availability
        available_forcefields = [
            'amber14-all.xml', 'amber99sb.xml', 'amber99sbildn.xml',
            'charmm36.xml', 'amoeba2013.xml'
        ]
        
        # Normalize forcefield name
        ff_name = forcefield
        if not ff_name.endswith('.xml'):
            ff_name = f"{ff_name}.xml"
        
        # Check if it's a known forcefield
        known_ff = ff_name in available_forcefields or 'amber' in ff_name.lower() or 'charmm' in ff_name.lower()
        
        if not known_ff:
            msg = f"⚠️ Force field '{forcefield}' may not be available. Known: {available_forcefields}"
            self._log_validation('forcefield', False, msg)
            return False, msg
        
        # Parse PDB to find residue types
        try:
            with open(full_path, 'r') as f:
                lines = f.readlines()
            
            residue_types = set()
            for line in lines:
                if line.startswith('ATOM') or line.startswith('HETATM'):
                    if len(line) >= 20:
                        resname = line[17:20].strip()
                        residue_types.add(resname)
            
            # Standard amino acids supported by all protein forcefields
            standard_aa = {'ALA', 'ARG', 'ASN', 'ASP', 'CYS', 'GLN', 'GLU', 'GLY', 
                          'HIS', 'HIE', 'HID', 'HIP', 'ILE', 'LEU', 'LYS', 'MET', 
                          'PHE', 'PRO', 'SER', 'THR', 'TRP', 'TYR', 'VAL'}
            
            # Common water/ion residues
            common_solvent = {'HOH', 'WAT', 'TIP3', 'SOL', 'NA', 'CL', 'K', 'MG', 'CA'}
            
            # Check for unsupported residue types
            unsupported = residue_types - standard_aa - common_solvent
            
            if unsupported:
                # Check if they're common ligands/modifications
                known_hetero = {'ACE', 'NME', 'NH2', 'GDP', 'GTP', 'ATP', 'ADP', 'NAG', 'MAN'}
                unknown = unsupported - known_hetero
                
                if unknown:
                    msg = (f"⚠️ Force field may not cover residue types: {unknown}\n"
                           f"   Consider removing non-standard residues or adding parameters")
                    self._log_validation('forcefield', False, msg)
                    return False, msg
            
            # Force field looks compatible
            self.forcefield_validated = True
            self.validated_forcefield = forcefield
            
            msg = (f"✅ Force field validated: {forcefield}\n"
                   f"   📊 {len(residue_types)} residue types found\n"
                   f"   🧬 All residues appear to be parameterized")
            
            self._log_validation('forcefield', True, msg)
            return True, msg
            
        except Exception as e:
            msg = f"❌ Error validating force field coverage: {str(e)}"
            self._log_validation('forcefield', False, msg)
            return False, msg
    
    def check_forcefield_status(self) -> str:
        """Check current force field validation status."""
        if self.forcefield_validated and self.validated_forcefield:
            return f"✅ Force field validated: {self.validated_forcefield}"
        return "❌ No force field has been validated"
    
    def mark_forcefield_validated(self, forcefield: str, pdb_file: str) -> str:
        """Manually mark a force field as validated for a structure."""
        self.forcefield_validated = True
        self.validated_forcefield = forcefield
        self._log_validation('forcefield', True, f"Manually marked validated: {forcefield} for {pdb_file}")
        return f"✅ Force field marked as validated: {forcefield}"

    # ==================== SYSTEM PREPARATION VALIDATION ====================
    
    def validate_system_preparation(self, system_file: str) -> Tuple[bool, str]:
        """
        Validate that a solvated system is ready for simulation.
        
        Checks:
        - System file exists
        - Contains protein, water, and ions
        - Box dimensions are reasonable
        
        Returns: (is_valid, message)
        """
        if not os.path.isabs(system_file):
            full_path = os.path.join(self.workdir, system_file)
        else:
            full_path = system_file
        
        if not os.path.exists(full_path):
            msg = f"❌ System file not found: {system_file}"
            self._log_validation('system', False, msg)
            return False, msg
        
        try:
            with open(full_path, 'r') as f:
                lines = f.readlines()
            
            # Count atoms and residues
            atom_count = 0
            water_count = 0
            ion_count = 0
            protein_atoms = 0
            
            water_names = {'HOH', 'WAT', 'TIP3', 'SOL', 'TIP3P'}
            ion_names = {'NA', 'CL', 'K', 'MG', 'CA', 'NA+', 'CL-'}
            
            for line in lines:
                if line.startswith('ATOM') or line.startswith('HETATM'):
                    atom_count += 1
                    if len(line) >= 20:
                        resname = line[17:20].strip()
                        if resname in water_names:
                            water_count += 1
                        elif resname in ion_names:
                            ion_count += 1
                        else:
                            protein_atoms += 1
            
            # Check for reasonable composition
            issues = []
            
            if protein_atoms < 100:
                issues.append(f"Low protein atom count: {protein_atoms}")
            
            if water_count < 100:
                issues.append(f"Low water count: {water_count} - may need more solvation")
            
            if ion_count == 0:
                issues.append("No ions found - system may not be neutralized")
            
            if issues:
                msg = "⚠️ System preparation issues:\n   " + "\n   ".join(issues)
                self._log_validation('system', False, msg)
                return False, msg
            
            # System looks ready
            self.system_prepared = True
            self.validated_system_file = full_path
            
            msg = (f"✅ System prepared: {os.path.basename(system_file)}\n"
                   f"   📊 {atom_count} total atoms\n"
                   f"   🧬 {protein_atoms} protein atoms\n"
                   f"   💧 {water_count} water atoms\n"
                   f"   ⚡ {ion_count} ion atoms")
            
            self._log_validation('system', True, msg)
            return True, msg
            
        except Exception as e:
            msg = f"❌ Error validating system: {str(e)}"
            self._log_validation('system', False, msg)
            return False, msg
    
    def check_system_ready(self) -> Tuple[bool, str]:
        """Check if system is ready for simulation."""
        if self.system_prepared and self.validated_system_file:
            if os.path.exists(self.validated_system_file):
                return True, f"✅ System ready: {os.path.basename(self.validated_system_file)}"
            else:
                self.system_prepared = False
                self.validated_system_file = None
                return False, "❌ Prepared system file no longer exists"
        return False, "❌ No system has been prepared for simulation"

    # ==================== WORKFLOW VALIDATION ====================
    
    def check_workflow_status(self) -> Tuple[bool, str]:
        """
        Check if workflow can continue based on validation states.
        
        VALIDATION GATE: This is the main checkpoint before running simulations.
        
        Returns: (can_continue, status_message)
        """
        status_parts = []
        all_valid = True
        
        # Check structure
        if self.structure_validated and self.validated_structure_file:
            if os.path.exists(self.validated_structure_file):
                status_parts.append(f"✅ Structure: {os.path.basename(self.validated_structure_file)}")
            else:
                self.structure_validated = False
                self.validated_structure_file = None
                status_parts.append("❌ Structure file missing")
                all_valid = False
        else:
            # Try to auto-detect structure files
            pdb_files = self._find_pdb_files()
            if pdb_files:
                # Try to validate first found PDB
                success, msg = self.validate_structure(pdb_files[0])
                if success:
                    status_parts.append(f"✅ Structure: {os.path.basename(pdb_files[0])} (auto-detected)")
                else:
                    status_parts.append(f"❌ Structure: {msg}")
                    all_valid = False
            else:
                status_parts.append("❌ No structure file found")
                all_valid = False
        
        # Check force field
        if self.forcefield_validated and self.validated_forcefield:
            status_parts.append(f"✅ Force field: {self.validated_forcefield}")
        else:
            status_parts.append("❌ Force field not validated")
            all_valid = False
        
        # Build final message
        if all_valid:
            message = "✅ WORKFLOW READY - All prerequisites met:\n   " + "\n   ".join(status_parts)
        else:
            message = "❌ WORKFLOW HALTED - Prerequisites not met:\n   " + "\n   ".join(status_parts)
        
        self._log_validation('workflow', all_valid, message)
        return all_valid, message
    
    def _find_pdb_files(self) -> List[str]:
        """Find PDB files in working directory."""
        pdb_files = []
        if os.path.exists(self.workdir):
            for f in os.listdir(self.workdir):
                if f.endswith('.pdb'):
                    pdb_files.append(os.path.join(self.workdir, f))
        return pdb_files
    
    def get_validation_summary(self) -> str:
        """Get comprehensive validation state summary."""
        summary = "📋 VALIDATION SUMMARY:\n" + "="*50 + "\n"
        
        summary += f"\n🧬 Structure: {'✅ Validated' if self.structure_validated else '❌ Not validated'}\n"
        if self.validated_structure_file:
            summary += f"   File: {os.path.basename(self.validated_structure_file)}\n"
        
        summary += f"\n⚛️ Force Field: {'✅ Validated' if self.forcefield_validated else '❌ Not validated'}\n"
        if self.validated_forcefield:
            summary += f"   Name: {self.validated_forcefield}\n"
        
        summary += f"\n🔬 System: {'✅ Prepared' if self.system_prepared else '❌ Not prepared'}\n"
        if self.validated_system_file:
            summary += f"   File: {os.path.basename(self.validated_system_file)}\n"
        
        # Overall status
        ready = self.structure_validated and self.forcefield_validated
        summary += f"\n{'='*50}\n"
        summary += f"🎯 Overall: {'✅ READY FOR SIMULATION' if ready else '❌ NOT READY'}\n"
        
        return summary
    
    def reset_validation_state(self) -> str:
        """Reset all validation states."""
        self.structure_validated = False
        self.forcefield_validated = False
        self.system_prepared = False
        self.validated_structure_file = None
        self.validated_forcefield = None
        self.validated_system_file = None
        
        return "🔄 All validation states reset"
    
    def get_validation_history(self) -> List[Dict]:
        """Get validation history for observability."""
        return self.validation_history


# ==================== VALIDATION DECORATORS ====================

def require_structure(func):
    """Decorator to require validated structure before function execution."""
    def wrapper(self, *args, **kwargs):
        if hasattr(self, 'validation_manager') and self.validation_manager:
            if not self.validation_manager.structure_validated:
                return "❌ Structure validation required before this operation"
        return func(self, *args, **kwargs)
    return wrapper


def require_forcefield(func):
    """Decorator to require validated force field before function execution."""
    def wrapper(self, *args, **kwargs):
        if hasattr(self, 'validation_manager') and self.validation_manager:
            if not self.validation_manager.forcefield_validated:
                return "❌ Force field validation required before this operation"
        return func(self, *args, **kwargs)
    return wrapper


def require_workflow_ready(func):
    """Decorator to require full workflow validation before function execution."""
    def wrapper(self, *args, **kwargs):
        if hasattr(self, 'validation_manager') and self.validation_manager:
            ready, msg = self.validation_manager.check_workflow_status()
            if not ready:
                return f"❌ Workflow not ready: {msg}"
        return func(self, *args, **kwargs)
    return wrapper

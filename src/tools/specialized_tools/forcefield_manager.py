"""
Force Field Manager

Handles OpenMM force field management, validation, and custom force field downloads.
Replaces materials-science EAM/MEAM potential management.
"""

import os
import requests
from typing import Optional, Tuple, Dict, List


class ForceFieldManager:
    """Manages OpenMM force fields for protein simulations."""
    
    # Standard OpenMM force fields
    STANDARD_FORCEFIELDS = {
        'amber14': {
            'protein': 'amber14-all.xml',
            'water': 'amber14/tip3pfb.xml',
            'description': 'AMBER ff14SB for proteins, TIP3P-FB water'
        },
        'amber99sb': {
            'protein': 'amber99sb.xml',
            'water': 'tip3p.xml',
            'description': 'AMBER ff99SB-ILDN for proteins'
        },
        'charmm36': {
            'protein': 'charmm36.xml',
            'water': 'charmm36/water.xml',
            'description': 'CHARMM36m for proteins'
        },
        'amoeba': {
            'protein': 'amoeba2018.xml',
            'water': 'amoeba2018.xml',
            'description': 'AMOEBA polarizable force field'
        }
    }
    
    # Water models
    WATER_MODELS = {
        'tip3p': 'tip3p.xml',
        'tip3pfb': 'amber14/tip3pfb.xml',
        'tip4pew': 'tip4pew.xml',
        'tip5p': 'tip5p.xml',
        'spce': 'spce.xml',
        'opc': 'opc.xml'
    }
    
    def __init__(self, workdir: str, websurfer=None):
        self.workdir = workdir
        self.websurfer = websurfer
        self.workflow_logger = None  # Set by AutoGenSystem
        
        # Validation state
        self.forcefield_validated = False
        self.last_forcefield_file = None
        self.last_forcefield_name = None
    
    def _log(self, message: str):
        """Log message if workflow logger is available."""
        if self.workflow_logger:
            self.workflow_logger.log_tool_invocation("ForceFieldManager", {}, message)
    
    def set_websurfer(self, websurfer):
        """Set the websurfer agent for web searches."""
        self.websurfer = websurfer
    
    def list_available_forcefields(self) -> str:
        """
        List all available force fields and water models.
        
        Returns:
            Formatted string of available options
        """
        output = "📚 Available Force Fields:\n\n"
        
        for name, ff in self.STANDARD_FORCEFIELDS.items():
            output += f"  🔬 {name}:\n"
            output += f"     Protein: {ff['protein']}\n"
            output += f"     Water: {ff['water']}\n"
            output += f"     Description: {ff['description']}\n\n"
        
        output += "💧 Water Models:\n"
        for name, xml in self.WATER_MODELS.items():
            output += f"  • {name}: {xml}\n"
        
        output += "\n📝 Usage: Use forcefield name (e.g., 'amber14') or XML filename"
        
        return output
    
    def validate_forcefield(self, forcefield_name: str = 'amber14-all.xml') -> Tuple[bool, str]:
        """
        Validate that a force field is available in OpenMM.
        
        Args:
            forcefield_name: Force field name or XML filename
            
        Returns:
            Tuple of (is_valid, message)
        """
        self._log(f"Validating force field: {forcefield_name}")
        
        try:
            from openmm.app import ForceField
        except ImportError:
            return False, "❌ OpenMM not installed. Run: pip install openmm"
        
        # Handle shorthand names
        if forcefield_name in self.STANDARD_FORCEFIELDS:
            ff_info = self.STANDARD_FORCEFIELDS[forcefield_name]
            protein_ff = ff_info['protein']
            water_ff = ff_info['water']
        else:
            protein_ff = forcefield_name
            water_ff = None
        
        try:
            # Try to load force field
            if water_ff:
                ff = ForceField(protein_ff, water_ff)
            else:
                ff = ForceField(protein_ff)
            
            self.forcefield_validated = True
            self.last_forcefield_name = forcefield_name
            self.last_forcefield_file = protein_ff
            
            return True, f"""✅ Force field validated: {forcefield_name}
  📄 Protein FF: {protein_ff}
  💧 Water model: {water_ff or 'Not specified'}"""
            
        except Exception as e:
            self.forcefield_validated = False
            return False, f"❌ Force field validation failed: {str(e)}"
    
    def validate_forcefield_coverage(self, pdb_file: str, 
                                     forcefield_name: str = 'amber14-all.xml') -> Tuple[bool, str]:
        """
        Validate that a force field covers all atoms in a PDB structure.
        
        Args:
            pdb_file: PDB file to check
            forcefield_name: Force field to validate
            
        Returns:
            Tuple of (is_valid, message)
        """
        self._log(f"Checking force field coverage for: {pdb_file}")
        
        try:
            from openmm.app import ForceField, PDBFile
        except ImportError:
            return False, "❌ OpenMM not installed"
        
        if not os.path.isabs(pdb_file):
            pdb_path = os.path.join(self.workdir, pdb_file)
        else:
            pdb_path = pdb_file
        
        if not os.path.exists(pdb_path):
            return False, f"❌ PDB file not found: {pdb_file}"
        
        # Get force field files
        if forcefield_name in self.STANDARD_FORCEFIELDS:
            ff_info = self.STANDARD_FORCEFIELDS[forcefield_name]
            ff_files = [ff_info['protein'], ff_info['water']]
        else:
            ff_files = [forcefield_name]
        
        try:
            # Load PDB
            pdb = PDBFile(pdb_path)
            topology = pdb.topology
            
            # Try to create force field and system
            ff = ForceField(*ff_files)
            
            # This will raise an exception if atoms are not covered
            try:
                system = ff.createSystem(topology)
                
                # Count atoms
                n_atoms = topology.getNumAtoms()
                n_residues = topology.getNumResidues()
                
                self.forcefield_validated = True
                
                return True, f"""✅ Force field covers all atoms:
  📄 PDB: {pdb_file}
  🔬 Force field: {forcefield_name}
  ⚛️  Atoms: {n_atoms}
  🧬 Residues: {n_residues}
  ✓ All atom types parameterized"""
                
            except Exception as e:
                error_msg = str(e)
                
                # Parse missing atom types from error
                missing_atoms = []
                if 'No template found' in error_msg:
                    # Extract residue name from error
                    missing_atoms.append(error_msg)
                
                return False, f"""⚠️ Force field coverage incomplete:
  📄 PDB: {pdb_file}
  🔬 Force field: {forcefield_name}
  ❌ Missing parameters: {error_msg}
  
  Suggestions:
  • Check for non-standard residues
  • Add custom residue templates
  • Try different force field"""
                
        except Exception as e:
            return False, f"❌ Coverage check failed: {str(e)}"
    
    def download_custom_forcefield(self, url: str, filename: str = None) -> str:
        """
        Download a custom force field XML file.
        
        Args:
            url: URL to force field file
            filename: Local filename (optional)
            
        Returns:
            Status message
        """
        self._log(f"Downloading custom force field: {url}")
        
        if filename is None:
            filename = url.split('/')[-1]
        
        output_path = os.path.join(self.workdir, filename)
        
        try:
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                with open(output_path, 'w') as f:
                    f.write(response.text)
                
                # Validate the downloaded file
                is_valid, msg = self.validate_forcefield(output_path)
                
                if is_valid:
                    return f"""✅ Custom force field downloaded:
  📄 File: {filename}
  🔗 Source: {url}
  ✓ Validation: Passed"""
                else:
                    return f"""⚠️ Force field downloaded but validation failed:
  📄 File: {filename}
  ❌ Validation: {msg}"""
            else:
                return f"❌ Download failed: HTTP {response.status_code}"
                
        except Exception as e:
            return f"❌ Download error: {str(e)}"
    
    def create_custom_residue_template(self, residue_name: str, 
                                       smiles: str = None,
                                       output_file: str = None) -> str:
        """
        Create a custom residue template for non-standard residues.
        
        Args:
            residue_name: 3-letter residue code
            smiles: SMILES string for the molecule (optional)
            output_file: Output XML filename
            
        Returns:
            Status message
        """
        self._log(f"Creating custom template for: {residue_name}")
        
        if output_file is None:
            output_file = f"{residue_name.lower()}_template.xml"
        
        # Template for custom residue
        template = f"""<?xml version="1.0" encoding="UTF-8"?>
<ForceField>
  <Info>
    <DateGenerated>auto-generated</DateGenerated>
    <Reference>Custom residue template for {residue_name}</Reference>
  </Info>
  
  <Residues>
    <Residue name="{residue_name}">
      <!-- Add atoms here -->
      <!-- <Atom name="CA" type="CT" charge="0.0"/> -->
      <!-- Add bonds here -->
      <!-- <Bond from="0" to="1"/> -->
    </Residue>
  </Residues>
  
  <!-- Add any custom atom types and parameters below -->
  
</ForceField>
"""
        
        output_path = os.path.join(self.workdir, output_file)
        
        with open(output_path, 'w') as f:
            f.write(template)
        
        return f"""✅ Custom residue template created:
  📄 File: {output_file}
  🧬 Residue: {residue_name}
  
  ⚠️ Note: You must manually add:
  • Atom definitions with types and charges
  • Bond connectivity
  • Any non-standard atom types/parameters
  
  Reference: OpenMM ForceField documentation"""
    
    def get_forcefield_info(self, forcefield_name: str) -> str:
        """
        Get detailed information about a force field.
        
        Args:
            forcefield_name: Force field name
            
        Returns:
            Information string
        """
        if forcefield_name in self.STANDARD_FORCEFIELDS:
            ff = self.STANDARD_FORCEFIELDS[forcefield_name]
            return f"""📋 Force Field: {forcefield_name}
  📄 Protein XML: {ff['protein']}
  💧 Water XML: {ff['water']}
  📝 Description: {ff['description']}
  
  Usage in OpenMM:
    from openmm.app import ForceField
    ff = ForceField('{ff['protein']}', '{ff['water']}')"""
        else:
            return f"❓ Force field '{forcefield_name}' not in standard list. May be custom or misspelled."
    
    def recommend_forcefield(self, system_type: str = 'protein') -> str:
        """
        Recommend appropriate force field based on system type.
        
        Args:
            system_type: Type of system ('protein', 'nucleic', 'membrane', 'small_molecule')
            
        Returns:
            Recommendation string
        """
        recommendations = {
            'protein': {
                'recommended': 'amber14',
                'alternatives': ['charmm36', 'amber99sb'],
                'notes': 'amber14-all.xml with TIP3P-FB is well-validated for proteins'
            },
            'nucleic': {
                'recommended': 'amber14',
                'alternatives': ['charmm36'],
                'notes': 'OL15 modifications for DNA, OL3 for RNA'
            },
            'membrane': {
                'recommended': 'charmm36',
                'alternatives': [],
                'notes': 'CHARMM36m optimized for membrane proteins'
            },
            'small_molecule': {
                'recommended': 'gaff2',
                'alternatives': ['openff'],
                'notes': 'Use OpenFF or GAFF2 for small molecules'
            }
        }
        
        if system_type.lower() not in recommendations:
            return f"❓ Unknown system type: {system_type}. Try: protein, nucleic, membrane, small_molecule"
        
        rec = recommendations[system_type.lower()]
        
        output = f"""🎯 Force Field Recommendation for {system_type}:

  ✨ Recommended: {rec['recommended']}
  🔄 Alternatives: {', '.join(rec['alternatives']) if rec['alternatives'] else 'None'}
  
  📝 Notes: {rec['notes']}
  
  To use:
    forcefield_name = '{rec['recommended']}'
    validate_forcefield(forcefield_name)"""
        
        return output
    
    def check_workflow_status(self) -> Tuple[bool, str]:
        """
        Check if force field is validated for workflow to proceed.
        
        Returns:
            Tuple of (can_continue, message)
        """
        if self.forcefield_validated:
            return True, f"✅ Force field ready: {self.last_forcefield_name}"
        else:
            return False, "❌ WORKFLOW HALTED: Force field not validated. Call validate_forcefield() first."

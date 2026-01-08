"""
Protein Structure Creator

Handles protein structure download from RCSB PDB and AlphaFold,
structure preparation, validation, and system setup for MD simulations.

Replaces materials-science Atomsk-based structure creation.
"""

import os
import requests
from typing import Optional, Tuple, Dict, List


class StructureCreator:
    """Handles protein structure creation and preparation for MD simulations."""

    def __init__(self, workdir: str):
        self.workdir = workdir
        self.workflow_logger = None  # Set by AutoGenSystem
        
        # Structure state tracking
        self.structure_validated = False
        self.last_structure_file = None
        self.system_prepared = False
        
        # PDB/AlphaFold base URLs
        self.rcsb_url = "https://files.rcsb.org/download"
        self.alphafold_url = "https://alphafold.ebi.ac.uk/files"
    
    def _log(self, message: str):
        """Log message if workflow logger is available."""
        if self.workflow_logger:
            self.workflow_logger.log_tool_invocation(
                "StructureCreator", {}, message
            )
    
    def download_pdb_structure(self, pdb_id: str, format: str = "pdb") -> str:
        """
        Download PDB structure from RCSB database.
        
        Args:
            pdb_id: 4-character PDB identifier (e.g., '1LYZ')
            format: File format ('pdb' or 'cif')
            
        Returns:
            Status message with file path
        """
        self._log(f"Downloading PDB structure: {pdb_id}")
        
        pdb_id = pdb_id.upper().strip()
        
        if len(pdb_id) != 4:
            return f"❌ Invalid PDB ID: {pdb_id}. Must be 4 characters."
        
        # Determine file extension
        if format.lower() == "cif":
            extension = "cif"
            url = f"{self.rcsb_url}/{pdb_id}.cif"
        else:
            extension = "pdb"
            url = f"{self.rcsb_url}/{pdb_id}.pdb"
        
        output_file = os.path.join(self.workdir, f"{pdb_id}.{extension}")
        
        try:
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                with open(output_file, 'w') as f:
                    f.write(response.text)
                
                # Parse structure info
                info = self._parse_pdb_info(output_file)
                
                self.last_structure_file = output_file
                
                return f"""✅ PDB structure downloaded successfully:
  🆔 PDB ID: {pdb_id}
  📄 File: {pdb_id}.{extension}
  🔬 Title: {info.get('title', 'N/A')}
  ⚛️  Atoms: {info.get('atoms', 'N/A')}
  🧬 Residues: {info.get('residues', 'N/A')}
  🔗 Chains: {info.get('chains', 'N/A')}
  📊 Resolution: {info.get('resolution', 'N/A')}"""
                
            elif response.status_code == 404:
                return f"❌ PDB ID '{pdb_id}' not found in RCSB database"
            else:
                return f"❌ Download failed with status code: {response.status_code}"
                
        except requests.exceptions.Timeout:
            return "❌ Download timed out. Please try again."
        except Exception as e:
            return f"❌ Download error: {str(e)}"
    
    def download_alphafold_structure(self, uniprot_id: str, version: int = 4) -> str:
        """
        Download AlphaFold predicted structure from EBI.
        
        Args:
            uniprot_id: UniProt accession (e.g., 'P00520')
            version: AlphaFold model version (default: 4)
            
        Returns:
            Status message with file path
        """
        self._log(f"Downloading AlphaFold structure: {uniprot_id}")
        
        uniprot_id = uniprot_id.upper().strip()
        
        # AlphaFold URL format
        url = f"{self.alphafold_url}/AF-{uniprot_id}-F1-model_v{version}.pdb"
        
        output_file = os.path.join(self.workdir, f"AF_{uniprot_id}.pdb")
        
        try:
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                with open(output_file, 'w') as f:
                    f.write(response.text)
                
                info = self._parse_pdb_info(output_file)
                
                self.last_structure_file = output_file
                
                return f"""✅ AlphaFold structure downloaded:
  🆔 UniProt: {uniprot_id}
  📄 File: AF_{uniprot_id}.pdb
  🔬 Model version: {version}
  ⚛️  Atoms: {info.get('atoms', 'N/A')}
  🧬 Residues: {info.get('residues', 'N/A')}
  ⚠️  Note: Check pLDDT scores for model confidence"""
                
            elif response.status_code == 404:
                return f"❌ UniProt ID '{uniprot_id}' not found in AlphaFold database"
            else:
                return f"❌ AlphaFold download failed: status {response.status_code}"
                
        except Exception as e:
            return f"❌ AlphaFold download error: {str(e)}"
    
    def validate_structure(self, pdb_file: str) -> Tuple[bool, str]:
        """
        Validate a PDB structure for simulation readiness.
        
        Args:
            pdb_file: Path to PDB file
            
        Returns:
            Tuple of (is_valid, message)
        """
        self._log(f"Validating structure: {pdb_file}")
        
        if not os.path.isabs(pdb_file):
            pdb_path = os.path.join(self.workdir, pdb_file)
        else:
            pdb_path = pdb_file
        
        if not os.path.exists(pdb_path):
            return False, f"❌ File not found: {pdb_file}"
        
        issues = []
        warnings = []
        
        try:
            with open(pdb_path, 'r') as f:
                content = f.read()
                lines = content.split('\n')
            
            # Count atoms and check for common issues
            atom_count = 0
            has_hydrogens = False
            missing_residues = []
            hetatm_count = 0
            water_count = 0
            
            for line in lines:
                if line.startswith('ATOM'):
                    atom_count += 1
                    if ' H' in line[12:16] or line[12:16].strip().startswith('H'):
                        has_hydrogens = True
                        
                elif line.startswith('HETATM'):
                    hetatm_count += 1
                    if 'HOH' in line or 'WAT' in line:
                        water_count += 1
                        
                elif line.startswith('REMARK 465'):
                    # Missing residues
                    if 'M RES' not in line and len(line) > 20:
                        missing_residues.append(line[15:27].strip())
            
            # Check for critical issues
            if atom_count == 0:
                issues.append("No atoms found in structure")
            
            if missing_residues:
                pct_missing = len(missing_residues)
                if pct_missing > 10:
                    issues.append(f"Too many missing residues ({pct_missing})")
                else:
                    warnings.append(f"{pct_missing} missing residues (may need modeling)")
            
            # Check for warnings
            if not has_hydrogens:
                warnings.append("No hydrogens present (add with ChimeraX)")
            
            if water_count > 0:
                warnings.append(f"{water_count} crystallographic waters (consider removing)")
            
            if hetatm_count - water_count > 0:
                warnings.append(f"{hetatm_count - water_count} HETATM entries (ligands/ions)")
            
            # Determine validity
            is_valid = len(issues) == 0
            
            if is_valid:
                self.structure_validated = True
                self.last_structure_file = pdb_path
            
            # Build message
            status = "✅ VALID" if is_valid else "❌ INVALID"
            msg = f"{status}: {pdb_file}\n"
            msg += f"  ⚛️  Atoms: {atom_count}\n"
            
            if issues:
                msg += "  🚫 Issues:\n"
                for issue in issues:
                    msg += f"    • {issue}\n"
            
            if warnings:
                msg += "  ⚠️  Warnings:\n"
                for warning in warnings:
                    msg += f"    • {warning}\n"
            
            return is_valid, msg
            
        except Exception as e:
            return False, f"❌ Validation error: {str(e)}"
    
    def create_protein_system(self, pdb_file: str, add_waters: bool = True,
                             padding: float = 1.0, ionic_strength: float = 0.15,
                             forcefield: str = "amber14-all.xml") -> str:
        """
        Create a solvated protein system ready for simulation.
        
        Args:
            pdb_file: Input PDB file
            add_waters: Whether to add water box
            padding: Box padding in nm
            ionic_strength: Ion concentration in M
            forcefield: Force field to use
            
        Returns:
            Status message
        """
        self._log(f"Creating protein system from: {pdb_file}")
        
        try:
            from openmm import app, unit
        except ImportError:
            return "❌ OpenMM not installed. Run: pip install openmm"
        
        if not os.path.isabs(pdb_file):
            pdb_path = os.path.join(self.workdir, pdb_file)
        else:
            pdb_path = pdb_file
        
        if not os.path.exists(pdb_path):
            return f"❌ PDB file not found: {pdb_file}"
        
        try:
            # Load structure
            pdb = app.PDBFile(pdb_path)
            
            # Create modeller
            modeller = app.Modeller(pdb.topology, pdb.positions)
            
            # Add hydrogens if missing
            print("  🔬 Adding missing hydrogens...")
            forcefield_obj = app.ForceField(forcefield, 'amber14/tip3pfb.xml')
            modeller.addHydrogens(forcefield_obj)
            
            if add_waters:
                # Add water box
                print("  💧 Adding water box...")
                modeller.addSolvent(
                    forcefield_obj,
                    padding=padding * unit.nanometer,
                    ionicStrength=ionic_strength * unit.molar
                )
            
            # Count molecules
            n_atoms = modeller.topology.getNumAtoms()
            n_residues = modeller.topology.getNumResidues()
            n_waters = sum(1 for r in modeller.topology.residues() if r.name == 'HOH')
            n_ions = sum(1 for r in modeller.topology.residues() if r.name in ['NA', 'CL', 'K'])
            
            # Save prepared system
            base_name = os.path.splitext(os.path.basename(pdb_file))[0]
            output_file = f"{base_name}_prepared.pdb"
            output_path = os.path.join(self.workdir, output_file)
            
            app.PDBFile.writeFile(
                modeller.topology, 
                modeller.positions, 
                open(output_path, 'w')
            )
            
            self.system_prepared = True
            self.last_structure_file = output_path
            
            return f"""✅ Protein system created successfully:
  📄 Input: {pdb_file}
  📄 Output: {output_file}
  ⚛️  Total atoms: {n_atoms}
  🧬 Residues: {n_residues}
  💧 Water molecules: {n_waters}
  🧂 Ions: {n_ions}
  📦 Box padding: {padding} nm
  ⚗️  Ionic strength: {ionic_strength} M
  🔬 Force field: {forcefield}"""
            
        except Exception as e:
            return f"❌ System creation failed: {str(e)}"
    
    def get_pdb_info(self, pdb_id: str) -> str:
        """
        Get information about a PDB entry without downloading.
        
        Args:
            pdb_id: 4-character PDB ID
            
        Returns:
            Information about the structure
        """
        pdb_id = pdb_id.upper().strip()
        
        # Use RCSB REST API
        url = f"https://data.rcsb.org/rest/v1/core/entry/{pdb_id}"
        
        try:
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                title = data.get('struct', {}).get('title', 'N/A')
                method = data.get('exptl', [{}])[0].get('method', 'N/A')
                resolution = data.get('rcsb_entry_info', {}).get('resolution_combined', ['N/A'])[0]
                deposit_date = data.get('rcsb_accession_info', {}).get('deposit_date', 'N/A')
                
                # Get polymer info
                polymers = data.get('rcsb_entry_info', {}).get('polymer_entity_count', 0)
                
                return f"""📋 PDB Entry: {pdb_id}
  🔬 Title: {title}
  📊 Method: {method}
  📐 Resolution: {resolution} Å
  📅 Deposited: {deposit_date}
  🔗 Polymer entities: {polymers}
  🌐 URL: https://www.rcsb.org/structure/{pdb_id}"""
                
            elif response.status_code == 404:
                return f"❌ PDB ID '{pdb_id}' not found"
            else:
                return f"❌ API error: status {response.status_code}"
                
        except Exception as e:
            return f"❌ Failed to get PDB info: {str(e)}"
    
    def search_pdb(self, query: str, max_results: int = 10) -> str:
        """
        Search RCSB PDB database.
        
        Args:
            query: Search query (protein name, organism, etc.)
            max_results: Maximum results to return
            
        Returns:
            Search results
        """
        # RCSB Search API
        search_url = "https://search.rcsb.org/rcsbsearch/v2/query"
        
        search_query = {
            "query": {
                "type": "terminal",
                "service": "full_text",
                "parameters": {
                    "value": query
                }
            },
            "return_type": "entry",
            "request_options": {
                "paginate": {
                    "start": 0,
                    "rows": max_results
                }
            }
        }
        
        try:
            response = requests.post(search_url, json=search_query, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('result_set', [])
                total = data.get('total_count', 0)
                
                if not results:
                    return f"No results found for: {query}"
                
                output = f"🔍 Search results for '{query}' ({total} total):\n\n"
                
                for entry in results[:max_results]:
                    pdb_id = entry.get('identifier', 'N/A')
                    score = entry.get('score', 0)
                    output += f"  • {pdb_id} (score: {score:.2f})\n"
                
                output += f"\nUse download_pdb_structure(pdb_id) to download."
                return output
                
            else:
                return f"❌ Search failed: status {response.status_code}"
                
        except Exception as e:
            return f"❌ Search error: {str(e)}"
    
    def _parse_pdb_info(self, pdb_file: str) -> Dict:
        """Parse basic information from PDB file."""
        info = {
            'atoms': 0,
            'residues': set(),
            'chains': set(),
            'title': '',
            'resolution': 'N/A'
        }
        
        try:
            with open(pdb_file, 'r') as f:
                for line in f:
                    if line.startswith('ATOM') or line.startswith('HETATM'):
                        info['atoms'] += 1
                        if len(line) > 21:
                            info['chains'].add(line[21])
                        if len(line) > 26:
                            res_id = line[17:26]
                            info['residues'].add(res_id)
                    elif line.startswith('TITLE'):
                        info['title'] += line[10:].strip() + ' '
                    elif line.startswith('REMARK   2 RESOLUTION'):
                        parts = line.split()
                        for i, p in enumerate(parts):
                            if p == 'ANGSTROMS' and i > 0:
                                try:
                                    info['resolution'] = f"{float(parts[i-1]):.2f} Å"
                                except:
                                    pass
            
            info['residues'] = len(info['residues'])
            info['chains'] = ','.join(sorted(info['chains'])) if info['chains'] else 'N/A'
            info['title'] = info['title'].strip()[:100]  # Truncate
            
        except Exception:
            pass
        
        return info
    
    def list_structures(self) -> str:
        """List all PDB/structure files in the working directory."""
        extensions = ['.pdb', '.cif', '.pdbx', '.mmcif']
        structures = []
        
        for file in os.listdir(self.workdir):
            if any(file.lower().endswith(ext) for ext in extensions):
                filepath = os.path.join(self.workdir, file)
                size = os.path.getsize(filepath)
                structures.append(f"  • {file} ({size/1024:.1f} KB)")
        
        if structures:
            return f"📁 Structure files in workdir:\n" + "\n".join(structures)
        else:
            return "📁 No structure files found in workdir"

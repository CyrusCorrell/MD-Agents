"""
ChimeraX Manager

Handles protein structure visualization and preparation using ChimeraX.
Supports both ChimeraX Python API and headless subprocess operations.
"""

import os
import subprocess
from typing import Optional, Tuple, List


class ChimeraXManager:
    """Manages ChimeraX visualization and structure preparation."""
    
    def __init__(self, workdir: str):
        self.workdir = workdir
        self.workflow_logger = None  # Set by AutoGenSystem
        
        # Check if ChimeraX is available
        self.chimerax_path = self._find_chimerax()
        self.use_api = self._check_chimerax_api_available()
    
    def _log(self, message: str):
        """Log message if workflow logger is available."""
        if self.workflow_logger:
            self.workflow_logger.log_tool_invocation("ChimeraXManager", {}, message)
    
    def _find_chimerax(self) -> Optional[str]:
        """Find ChimeraX executable."""
        # Common ChimeraX paths
        paths_to_check = [
            # Windows
            r"C:\Program Files\ChimeraX\bin\ChimeraX.exe",
            r"C:\Program Files\ChimeraX 1.7\bin\ChimeraX.exe",
            r"C:\Program Files\ChimeraX 1.8\bin\ChimeraX.exe",
            # macOS
            "/Applications/ChimeraX.app/Contents/MacOS/ChimeraX",
            # Linux
            "/usr/bin/chimerax",
            "/usr/local/bin/chimerax",
            os.path.expanduser("~/ChimeraX/bin/ChimeraX"),
        ]
        
        for path in paths_to_check:
            if os.path.exists(path):
                return path
        
        # Try finding in PATH
        try:
            result = subprocess.run(
                ["which", "chimerax"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        
        return None
    
    def _check_chimerax_api_available(self) -> bool:
        """Check if ChimeraX Python API is available."""
        try:
            import chimerax
            return True
        except ImportError:
            return False
    
    def clean_pdb_structure(self, pdb_file: str, remove_waters: bool = True,
                           add_hydrogens: bool = True, fix_gaps: bool = False,
                           output_file: str = None) -> str:
        """
        Clean a PDB structure for simulation.
        
        Args:
            pdb_file: Input PDB file
            remove_waters: Remove crystallographic waters
            add_hydrogens: Add missing hydrogens
            fix_gaps: Attempt to fix missing residues (experimental)
            output_file: Output filename
            
        Returns:
            Status message
        """
        self._log(f"Cleaning structure: {pdb_file}")
        
        if not os.path.isabs(pdb_file):
            pdb_path = os.path.join(self.workdir, pdb_file)
        else:
            pdb_path = pdb_file
        
        if not os.path.exists(pdb_path):
            return f"❌ PDB file not found: {pdb_file}"
        
        if output_file is None:
            base = os.path.splitext(os.path.basename(pdb_file))[0]
            output_file = f"{base}_cleaned.pdb"
        
        output_path = os.path.join(self.workdir, output_file)
        
        # Try API first, fall back to subprocess
        if self.use_api:
            return self._clean_with_api(pdb_path, output_path, 
                                       remove_waters, add_hydrogens, fix_gaps)
        elif self.chimerax_path:
            return self._clean_with_subprocess(pdb_path, output_path,
                                              remove_waters, add_hydrogens)
        else:
            # Fall back to basic Python cleaning
            return self._clean_basic(pdb_path, output_path, remove_waters)
    
    def _clean_basic(self, pdb_path: str, output_path: str, 
                    remove_waters: bool) -> str:
        """Basic PDB cleaning without ChimeraX."""
        try:
            with open(pdb_path, 'r') as f:
                lines = f.readlines()
            
            cleaned_lines = []
            removed_waters = 0
            removed_hetatm = 0
            
            for line in lines:
                # Remove waters if requested
                if remove_waters and line.startswith('HETATM'):
                    if 'HOH' in line or 'WAT' in line:
                        removed_waters += 1
                        continue
                
                # Keep ATOM lines and important header info
                if (line.startswith('ATOM') or 
                    line.startswith('TER') or
                    line.startswith('END') or
                    line.startswith('HEADER') or
                    line.startswith('TITLE') or
                    line.startswith('CRYST')):
                    cleaned_lines.append(line)
                elif line.startswith('HETATM'):
                    # Keep non-water HETATM (ligands, ions)
                    cleaned_lines.append(line)
            
            with open(output_path, 'w') as f:
                f.writelines(cleaned_lines)
            
            return f"""✅ Basic structure cleaning completed:
  📄 Input: {os.path.basename(pdb_path)}
  📄 Output: {os.path.basename(output_path)}
  💧 Waters removed: {removed_waters}
  ⚠️  Note: Hydrogens not added (ChimeraX not available)
  ⚠️  Recommend: Use OpenMM or external tool to add hydrogens"""
            
        except Exception as e:
            return f"❌ Basic cleaning failed: {str(e)}"
    
    def _clean_with_subprocess(self, pdb_path: str, output_path: str,
                               remove_waters: bool, add_hydrogens: bool) -> str:
        """Clean structure using ChimeraX command line."""
        try:
            # Build ChimeraX command script
            commands = [f'open "{pdb_path}"']
            
            if remove_waters:
                commands.append('delete solvent')
            
            if add_hydrogens:
                commands.append('addh')
            
            commands.append(f'save "{output_path}"')
            commands.append('exit')
            
            # Create temporary script file
            script_file = os.path.join(self.workdir, '_chimerax_clean.cxc')
            with open(script_file, 'w') as f:
                f.write('\n'.join(commands))
            
            # Run ChimeraX in headless mode
            result = subprocess.run(
                [self.chimerax_path, '--nogui', '--cmd', f'open {script_file}'],
                capture_output=True, text=True, timeout=120
            )
            
            # Clean up script
            os.remove(script_file)
            
            if os.path.exists(output_path):
                return f"""✅ Structure cleaned with ChimeraX:
  📄 Input: {os.path.basename(pdb_path)}
  📄 Output: {os.path.basename(output_path)}
  💧 Waters: {'removed' if remove_waters else 'kept'}
  🔬 Hydrogens: {'added' if add_hydrogens else 'not modified'}"""
            else:
                return f"❌ ChimeraX cleaning failed: output not created"
                
        except subprocess.TimeoutExpired:
            return "❌ ChimeraX operation timed out"
        except Exception as e:
            return f"❌ ChimeraX subprocess error: {str(e)}"
    
    def _clean_with_api(self, pdb_path: str, output_path: str,
                       remove_waters: bool, add_hydrogens: bool, 
                       fix_gaps: bool) -> str:
        """Clean structure using ChimeraX Python API."""
        try:
            from chimerax.core.commands import run
            from chimerax.core import session
            
            # This requires running inside ChimeraX environment
            # For standalone use, fall back to subprocess
            return self._clean_with_subprocess(pdb_path, output_path,
                                              remove_waters, add_hydrogens)
        except ImportError:
            return self._clean_with_subprocess(pdb_path, output_path,
                                              remove_waters, add_hydrogens)
    
    def visualize_trajectory(self, trajectory_file: str, topology_file: str,
                            output_movie: str = "trajectory.mp4",
                            frames: str = "all") -> str:
        """
        Create a movie from MD trajectory.
        
        Args:
            trajectory_file: DCD/XTC trajectory file
            topology_file: PDB topology file
            output_movie: Output movie filename
            frames: Frame selection ('all' or 'start:end:step')
            
        Returns:
            Status message
        """
        self._log(f"Creating trajectory movie: {trajectory_file}")
        
        if not self.chimerax_path:
            return "❌ ChimeraX not found. Cannot create visualization."
        
        traj_path = os.path.join(self.workdir, trajectory_file) if not os.path.isabs(trajectory_file) else trajectory_file
        top_path = os.path.join(self.workdir, topology_file) if not os.path.isabs(topology_file) else topology_file
        output_path = os.path.join(self.workdir, output_movie)
        
        if not os.path.exists(traj_path):
            return f"❌ Trajectory not found: {trajectory_file}"
        if not os.path.exists(top_path):
            return f"❌ Topology not found: {topology_file}"
        
        try:
            # ChimeraX commands for movie creation
            commands = [
                f'open "{top_path}"',
                f'open "{traj_path}"',
                'graphics silhouettes true',
                'lighting soft',
                'color bychain',
                f'movie record; coordset #1; movie stop',
                f'movie encode "{output_path}"',
                'exit'
            ]
            
            script_file = os.path.join(self.workdir, '_chimerax_movie.cxc')
            with open(script_file, 'w') as f:
                f.write('\n'.join(commands))
            
            result = subprocess.run(
                [self.chimerax_path, '--nogui', '--script', script_file],
                capture_output=True, text=True, timeout=600
            )
            
            os.remove(script_file)
            
            if os.path.exists(output_path):
                size_mb = os.path.getsize(output_path) / (1024 * 1024)
                return f"""✅ Trajectory movie created:
  🎬 Output: {output_movie}
  📊 Size: {size_mb:.1f} MB
  🎞️  Trajectory: {trajectory_file}"""
            else:
                return f"❌ Movie creation failed"
                
        except subprocess.TimeoutExpired:
            return "❌ Movie creation timed out"
        except Exception as e:
            return f"❌ Movie creation error: {str(e)}"
    
    def calculate_rmsd(self, trajectory_file: str, reference_pdb: str,
                      output_file: str = "rmsd.dat") -> str:
        """
        Calculate RMSD over trajectory using MDTraj (fallback if ChimeraX unavailable).
        
        Args:
            trajectory_file: DCD/XTC trajectory
            reference_pdb: Reference PDB structure
            output_file: Output data file
            
        Returns:
            Status message with RMSD summary
        """
        self._log(f"Calculating RMSD: {trajectory_file}")
        
        try:
            import mdtraj as md
            import numpy as np
        except ImportError:
            return "❌ MDTraj not installed. Run: pip install mdtraj"
        
        traj_path = os.path.join(self.workdir, trajectory_file) if not os.path.isabs(trajectory_file) else trajectory_file
        ref_path = os.path.join(self.workdir, reference_pdb) if not os.path.isabs(reference_pdb) else reference_pdb
        output_path = os.path.join(self.workdir, output_file)
        
        if not os.path.exists(traj_path):
            return f"❌ Trajectory not found: {trajectory_file}"
        if not os.path.exists(ref_path):
            return f"❌ Reference not found: {reference_pdb}"
        
        try:
            # Load trajectory
            traj = md.load(traj_path, top=ref_path)
            
            # Calculate RMSD to first frame
            rmsd = md.rmsd(traj, traj, frame=0)
            
            # Save RMSD data
            np.savetxt(output_path, 
                      np.column_stack([np.arange(len(rmsd)), rmsd]),
                      header="Frame RMSD(nm)", fmt='%d %.6f')
            
            return f"""✅ RMSD calculation completed:
  📊 Frames: {len(rmsd)}
  📈 Mean RMSD: {rmsd.mean():.3f} nm
  📉 Min RMSD: {rmsd.min():.3f} nm
  📈 Max RMSD: {rmsd.max():.3f} nm
  📄 Output: {output_file}"""
            
        except Exception as e:
            return f"❌ RMSD calculation failed: {str(e)}"
    
    def create_figure(self, pdb_file: str, output_image: str = "structure.png",
                     style: str = "ribbon", color: str = "bychain",
                     width: int = 1920, height: int = 1080) -> str:
        """
        Create a publication-quality figure of a structure.
        
        Args:
            pdb_file: Input PDB file
            output_image: Output image filename
            style: Visualization style ('ribbon', 'surface', 'stick')
            color: Coloring scheme ('bychain', 'byfactor', 'rainbow')
            width: Image width
            height: Image height
            
        Returns:
            Status message
        """
        self._log(f"Creating figure: {pdb_file}")
        
        if not self.chimerax_path:
            return "❌ ChimeraX not found. Cannot create figure."
        
        pdb_path = os.path.join(self.workdir, pdb_file) if not os.path.isabs(pdb_file) else pdb_file
        output_path = os.path.join(self.workdir, output_image)
        
        if not os.path.exists(pdb_path):
            return f"❌ PDB file not found: {pdb_file}"
        
        try:
            # Map style to ChimeraX commands
            style_cmds = {
                'ribbon': 'cartoon; hide atoms',
                'surface': 'surface; hide cartoon',
                'stick': 'show atoms; style stick',
                'ball': 'show atoms; style ball',
            }
            style_cmd = style_cmds.get(style, 'cartoon')
            
            color_cmds = {
                'bychain': 'color bychain',
                'byfactor': 'color bfactor',
                'rainbow': 'color rainbow',
                'secondary': 'color byattr ss_type',
            }
            color_cmd = color_cmds.get(color, 'color bychain')
            
            commands = [
                f'open "{pdb_path}"',
                style_cmd,
                color_cmd,
                'graphics silhouettes true',
                'lighting soft',
                'set bgcolor white',
                f'windowsize {width} {height}',
                f'save "{output_path}" supersample 3',
                'exit'
            ]
            
            script_file = os.path.join(self.workdir, '_chimerax_figure.cxc')
            with open(script_file, 'w') as f:
                f.write('\n'.join(commands))
            
            result = subprocess.run(
                [self.chimerax_path, '--nogui', '--script', script_file],
                capture_output=True, text=True, timeout=120
            )
            
            os.remove(script_file)
            
            if os.path.exists(output_path):
                return f"""✅ Figure created:
  🖼️  Output: {output_image}
  🎨 Style: {style}
  🌈 Color: {color}
  📐 Size: {width}x{height}"""
            else:
                return f"❌ Figure creation failed"
                
        except subprocess.TimeoutExpired:
            return "❌ Figure creation timed out"
        except Exception as e:
            return f"❌ Figure creation error: {str(e)}"
    
    def get_status(self) -> str:
        """Get ChimeraX availability status."""
        if self.use_api:
            return "✅ ChimeraX Python API available"
        elif self.chimerax_path:
            return f"✅ ChimeraX available: {self.chimerax_path}"
        else:
            return "⚠️ ChimeraX not found. Basic cleaning available, advanced features disabled."

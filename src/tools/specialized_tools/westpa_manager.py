"""
WESTPA Manager

Handles WESTPA weighted ensemble simulations for rare event sampling.
Provides basic weighted ensemble functionality for protein folding and binding studies.
"""

import os
import subprocess
import shutil
from typing import Optional, Tuple, List, Dict


class WESTPAManager:
    """Manages WESTPA weighted ensemble simulations."""
    
    def __init__(self, workdir: str):
        self.workdir = workdir
        self.westpa_dir = os.path.join(workdir, 'westpa')
        self.workflow_logger = None  # Set by AutoGenSystem
        
        # State tracking
        self.project_initialized = False
        self.simulation_running = False
        self.current_iteration = 0
    
    def _log(self, message: str):
        """Log message if workflow logger is available."""
        if self.workflow_logger:
            self.workflow_logger.log_tool_invocation("WESTPAManager", {}, message)
    
    def initialize_westpa_project(self, pdb_file: str, 
                                  basis_state: str = "folded",
                                  target_state: str = "unfolded",
                                  n_walkers: int = 48,
                                  tau: float = 10.0) -> str:
        """
        Initialize a WESTPA project directory structure.
        
        Args:
            pdb_file: Input PDB structure (basis state)
            basis_state: Name of the basis state
            target_state: Name of the target state  
            n_walkers: Number of walkers per bin
            tau: Resampling interval in ps
            
        Returns:
            Status message
        """
        self._log(f"Initializing WESTPA project: {pdb_file}")
        
        if not os.path.isabs(pdb_file):
            pdb_path = os.path.join(self.workdir, pdb_file)
        else:
            pdb_path = pdb_file
        
        if not os.path.exists(pdb_path):
            return f"❌ PDB file not found: {pdb_file}"
        
        try:
            # Create WESTPA directory structure
            dirs_to_create = [
                self.westpa_dir,
                os.path.join(self.westpa_dir, 'bstates'),
                os.path.join(self.westpa_dir, 'tstates'),
                os.path.join(self.westpa_dir, 'common_files'),
                os.path.join(self.westpa_dir, 'westpa_scripts'),
            ]
            
            for d in dirs_to_create:
                os.makedirs(d, exist_ok=True)
            
            # Copy basis state structure
            basis_pdb = os.path.join(self.westpa_dir, 'bstates', f'{basis_state}.pdb')
            shutil.copy(pdb_path, basis_pdb)
            
            # Create west.cfg
            self._create_west_cfg(n_walkers, tau)
            
            # Create system.py for progress coordinate
            self._create_system_py()
            
            # Create runseg.sh script
            self._create_runseg_script()
            
            # Create init.sh
            self._create_init_script()
            
            self.project_initialized = True
            
            return f"""✅ WESTPA project initialized:
  📁 Directory: {self.westpa_dir}
  📄 Basis state: {basis_state} ({pdb_file})
  🎯 Target state: {target_state}
  🚶 Walkers: {n_walkers}
  ⏱️  τ (tau): {tau} ps
  
  📂 Structure:
    westpa/
    ├── west.cfg
    ├── system.py
    ├── bstates/
    ├── tstates/
    ├── common_files/
    └── westpa_scripts/
  
  Next: Run init.sh, then w_run"""
            
        except Exception as e:
            return f"❌ WESTPA initialization failed: {str(e)}"
    
    def _create_west_cfg(self, n_walkers: int, tau: float):
        """Create WESTPA configuration file."""
        config = f"""# WESTPA Configuration
---
west:
  system:
    driver: westpa.core.systems.WESTSystem
    module_path: $WEST_SIM_ROOT
    system_options:
      pcoord_ndim: 1
      pcoord_len: 11
      pcoord_dtype: float64

  propagation:
    max_total_iterations: 1000
    max_run_wallclock: null
    propagator: executable
    gen_istates: false

  data:
    west_data_file: west.h5
    aux_compression_threshold: 0
    datasets:
      - name: pcoord
        dtype: float64

  plugins:
    - plugin: westpa.westext.wess.WESSDriver
      enabled: false

  executable:
    environ:
      PROPAGATION_DEBUG: 0
    propagator:
      executable: $WEST_SIM_ROOT/westpa_scripts/runseg.sh
      stdout: seg.log
      stderr: seg.err
      stdin: null
      cwd: null
      environ:
        SEG_DEBUG: 0

  we:
    n_iter: 100
    tau: {tau}
    n_walkers: {n_walkers}
"""
        
        config_path = os.path.join(self.westpa_dir, 'west.cfg')
        with open(config_path, 'w') as f:
            f.write(config)
    
    def _create_system_py(self):
        """Create WESTPA system.py for progress coordinate calculation."""
        system_py = '''"""
WESTPA System Configuration

Defines progress coordinate calculation and binning for weighted ensemble.
"""

import numpy as np
import westpa

class System(westpa.core.systems.WESTSystem):
    """WESTPA system configuration."""
    
    def initialize(self):
        """Initialize binning and target/basis states."""
        
        # Progress coordinate: RMSD from target state
        # Bins: evenly spaced from 0 to max_rmsd
        self.pcoord_ndim = 1
        self.pcoord_len = 11
        self.pcoord_dtype = np.float64
        
        # Define bins for RMSD-based progress coordinate
        # Adjust max_rmsd based on your system
        max_rmsd = 2.0  # nm
        n_bins = 20
        
        bin_boundaries = np.linspace(0, max_rmsd, n_bins + 1)
        
        from westpa.core.binning import RectilinearBinMapper
        self.bin_mapper = RectilinearBinMapper([bin_boundaries])
        
        # Target state: RMSD < 0.2 nm from target
        self.bin_target_counts = np.zeros(n_bins, dtype=np.int64)
        
    def get_pcoord(self, pcoord):
        """Get progress coordinate from trajectory."""
        return pcoord
'''
        
        system_path = os.path.join(self.westpa_dir, 'system.py')
        with open(system_path, 'w') as f:
            f.write(system_py)
    
    def _create_runseg_script(self):
        """Create WESTPA segment propagation script."""
        runseg = '''#!/bin/bash
# WESTPA segment propagation script

# Source WESTPA environment
if [ -n "$WEST_ROOT" ]; then
    source $WEST_ROOT/westpa.sh
fi

cd $WEST_CURRENT_SEG_DATA_REF

# Get parent coordinates
if [ "$WEST_CURRENT_SEG_INITPOINT_TYPE" = "SEG_INITPOINT_CONTINUES" ]; then
    ln -sf $WEST_PARENT_DATA_REF/seg.xml ./parent.xml
    PARENT_PCOORD=$(cat $WEST_PARENT_DATA_REF/pcoord.txt | tail -1)
elif [ "$WEST_CURRENT_SEG_INITPOINT_TYPE" = "SEG_INITPOINT_NEWTRAJ" ]; then
    ln -sf $WEST_BSTATE_DATA_REF/bstate.pdb ./parent.pdb
    PARENT_PCOORD=0.0
fi

# Run short MD segment using OpenMM
python << 'OPENMM_SCRIPT'
import os
from openmm import app, unit
from openmm import LangevinMiddleIntegrator, MonteCarloBarostat

# Load structure
if os.path.exists('parent.xml'):
    # Continue from checkpoint
    with open('parent.xml', 'r') as f:
        simulation.loadState(f)
else:
    # New trajectory from basis state
    pdb = app.PDBFile('parent.pdb')
    # Set up simulation...

# Run segment (tau ps)
# simulation.step(n_steps)

# Calculate progress coordinate (RMSD)
# ... mdtraj or internal calculation

# Save pcoord
with open('pcoord.txt', 'w') as f:
    f.write(f'{rmsd}\\n')

OPENMM_SCRIPT

# Output progress coordinate for WESTPA
cat pcoord.txt
'''
        
        script_path = os.path.join(self.westpa_dir, 'westpa_scripts', 'runseg.sh')
        with open(script_path, 'w') as f:
            f.write(runseg)
        os.chmod(script_path, 0o755)
    
    def _create_init_script(self):
        """Create WESTPA initialization script."""
        init_sh = '''#!/bin/bash
# WESTPA initialization script

set -e

# Source WESTPA
source $WEST_ROOT/westpa.sh
source env.sh

# Initialize WESTPA
rm -rf traj_segs seg_logs istates west.h5
mkdir -p traj_segs seg_logs istates

# Create initial states from basis states
BSTATE_ARGS="--bstate-file bstates/bstates.txt"

# Initialize simulation
w_init $BSTATE_ARGS --segs-per-state 1

echo "WESTPA initialization complete"
'''
        
        script_path = os.path.join(self.westpa_dir, 'init.sh')
        with open(script_path, 'w') as f:
            f.write(init_sh)
        os.chmod(script_path, 0o755)
    
    def run_westpa_simulation(self, iterations: int = 100) -> str:
        """
        Run WESTPA weighted ensemble simulation.
        
        Args:
            iterations: Number of WE iterations
            
        Returns:
            Status message
        """
        self._log(f"Running WESTPA simulation: {iterations} iterations")
        
        if not self.project_initialized:
            return "❌ WESTPA project not initialized. Run initialize_westpa_project() first."
        
        try:
            # Check if WESTPA is available
            result = subprocess.run(
                ['which', 'w_run'],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode != 0:
                return "❌ WESTPA not found in PATH. Install with: pip install westpa"
            
            # Run WESTPA
            self.simulation_running = True
            
            result = subprocess.run(
                ['w_run', '--max-iterations', str(iterations)],
                cwd=self.westpa_dir,
                capture_output=True, text=True,
                timeout=7200  # 2 hours max for local testing
            )
            
            self.simulation_running = False
            
            if result.returncode == 0:
                return f"""✅ WESTPA simulation completed:
  🔄 Iterations: {iterations}
  📁 Data file: west.h5
  📊 Analyze with: w_pdist, w_trace"""
            else:
                return f"❌ WESTPA failed: {result.stderr}"
                
        except subprocess.TimeoutExpired:
            self.simulation_running = False
            return "⚠️ WESTPA simulation still running (timeout reached). Check status with w_trace."
        except FileNotFoundError:
            return "❌ WESTPA not installed. Run: pip install westpa"
        except Exception as e:
            self.simulation_running = False
            return f"❌ WESTPA error: {str(e)}"
    
    def analyze_pathways(self, output_file: str = "pathways.dat") -> str:
        """
        Basic pathway analysis - flux and probability calculation.
        
        Args:
            output_file: Output file for pathway data
            
        Returns:
            Status message with analysis results
        """
        self._log("Analyzing WESTPA pathways")
        
        west_h5 = os.path.join(self.westpa_dir, 'west.h5')
        
        if not os.path.exists(west_h5):
            return "❌ WESTPA data file (west.h5) not found. Run simulation first."
        
        try:
            import h5py
            import numpy as np
        except ImportError:
            return "❌ h5py not installed. Run: pip install h5py"
        
        try:
            with h5py.File(west_h5, 'r') as f:
                # Get iterations
                iterations = list(f['iterations'].keys())
                n_iter = len(iterations)
                
                # Get final weights
                if n_iter > 0:
                    last_iter = iterations[-1]
                    weights = f[f'iterations/{last_iter}/seg_index']['weight'][:]
                    pcoords = f[f'iterations/{last_iter}/pcoord'][:]
                    
                    total_weight = np.sum(weights)
                    n_walkers = len(weights)
                    
                    # Basic statistics
                    mean_pcoord = np.average(pcoords[:, -1], weights=weights)
                    min_pcoord = np.min(pcoords[:, -1])
                    max_pcoord = np.max(pcoords[:, -1])
                else:
                    return "❌ No iterations found in west.h5"
            
            # Save pathway data
            output_path = os.path.join(self.westpa_dir, output_file)
            with open(output_path, 'w') as f:
                f.write(f"# WESTPA Pathway Analysis\n")
                f.write(f"# Iterations: {n_iter}\n")
                f.write(f"# Walkers: {n_walkers}\n")
                f.write(f"# Total weight: {total_weight:.6e}\n")
                f.write(f"# Mean pcoord: {mean_pcoord:.4f}\n")
            
            return f"""✅ Pathway analysis completed:
  🔄 Iterations analyzed: {n_iter}
  🚶 Active walkers: {n_walkers}
  📊 Progress coordinate:
    • Mean: {mean_pcoord:.4f}
    • Min: {min_pcoord:.4f}
    • Max: {max_pcoord:.4f}
  📄 Output: {output_file}
  
  For detailed analysis use:
    • w_pdist: probability distribution
    • w_trace: trace successful pathways
    • w_kinetics: rate constant estimation"""
            
        except Exception as e:
            return f"❌ Pathway analysis failed: {str(e)}"
    
    def get_status(self) -> str:
        """Get current WESTPA simulation status."""
        west_h5 = os.path.join(self.westpa_dir, 'west.h5')
        
        if not os.path.exists(self.westpa_dir):
            return "📊 WESTPA Status: Not initialized"
        
        if not os.path.exists(west_h5):
            return "📊 WESTPA Status: Project initialized, no simulation data"
        
        try:
            import h5py
            with h5py.File(west_h5, 'r') as f:
                n_iter = len(list(f['iterations'].keys()))
            
            return f"""📊 WESTPA Status:
  📁 Project: {self.westpa_dir}
  🔄 Completed iterations: {n_iter}
  🏃 Running: {self.simulation_running}"""
        except:
            return "📊 WESTPA Status: Data file exists but could not be read"
    
    def setup_folding_study(self, folded_pdb: str, unfolded_pdb: str = None,
                           n_walkers: int = 48) -> str:
        """
        Set up a protein folding weighted ensemble study.
        
        Args:
            folded_pdb: PDB of folded (native) state
            unfolded_pdb: PDB of unfolded state (optional, will generate if not provided)
            n_walkers: Number of walkers
            
        Returns:
            Status message
        """
        self._log(f"Setting up folding study: {folded_pdb}")
        
        # Initialize project with folded state as basis
        result = self.initialize_westpa_project(
            pdb_file=folded_pdb,
            basis_state="folded",
            target_state="unfolded",
            n_walkers=n_walkers
        )
        
        if "❌" in result:
            return result
        
        # Copy target state if provided
        if unfolded_pdb and os.path.exists(unfolded_pdb):
            target_path = os.path.join(self.westpa_dir, 'tstates', 'unfolded.pdb')
            shutil.copy(unfolded_pdb, target_path)
        
        return f"""{result}

🧬 Folding Study Setup:
  • Basis state: Folded structure ({folded_pdb})
  • Target state: Unfolded conformation
  • Progress coordinate: RMSD from native
  
  Recommended workflow:
  1. Generate unfolded ensemble (high-T simulation)
  2. Define progress coordinate bins
  3. Run w_init to initialize walkers
  4. Run w_run for weighted ensemble sampling"""

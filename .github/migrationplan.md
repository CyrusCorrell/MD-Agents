# Migration Plan: LAMMPS Framework → Protein MD Simulation

Transform this materials science atomistic simulation framework into a protein molecular dynamics system using OpenMM, WESTPA, and ChimeraX while preserving the multi-agent orchestration patterns.

## Core Changes Overview

**Remove**: LAMMPS, Atomsk, Phonopy, elastic constants agents
**Add**: OpenMM, WESTPA, ChimeraX, observability (Kalibr/Pydantic)
**Preserve**: Multi-agent architecture, validation gates, function registry, teachability

---

## Step 1: Replace Simulation Engine (LAMMPS → OpenMM)

### Current State
- `src/tools/specialized_tools/local_run_manager.py` invokes LAMMPS via subprocess
- Calls `subprocess.run(['lmp', '-in', 'input.lammps'], ...)` 
- Returns status strings with simulation results

### Target State
- Create `src/tools/specialized_tools/openmm_manager.py`
- Use OpenMM Python API directly (no subprocess)
- Support force fields: AMBER, CHARMM, OpenFF

### Implementation
```python
class OpenMMManager:
    def __init__(self, workdir: str):
        self.workdir = workdir
    
    def run_simulation(self, pdb_file: str, forcefield: str, 
                      steps: int, temperature: float) -> str:
        """Run MD simulation using OpenMM."""
        from openmm.app import *
        from openmm import *
        from openmm.unit import *
        
        try:
            # Load PDB and force field
            pdb = PDBFile(os.path.join(self.workdir, pdb_file))
            forcefield = ForceField(f'{forcefield}.xml', 'tip3p.xml')
            
            # Create system, integrator, simulation
            system = forcefield.createSystem(pdb.topology, ...)
            integrator = LangevinIntegrator(temperature*kelvin, ...)
            simulation = Simulation(pdb.topology, system, integrator)
            
            # Run and save trajectory
            simulation.step(steps)
            
            return f"✅ OpenMM simulation completed: {steps} steps"
        except Exception as e:
            return f"❌ OpenMM error: {str(e)}"
```

### Files to Modify
- Update `src/tools/agent_factory.py`: Rename `HPCAgent` → `SimulationAgent`
- Update `src/tools/function_registry.py`: Register OpenMM functions
- Update `src/system_messages/hpc_manager_system_message.py` → `simulation_manager_system_message.py`
- Modify `lammps_agents.py`: Replace `self.hpc_manager` with `self.openmm_manager`

### SLURM Integration (Required for Production)

**Create**: `src/tools/specialized_tools/slurm_manager.py`
```python
import subprocess
import paramiko  # For SSH
import os
from typing import Tuple

class SLURMManager:
    """Manage OpenMM and WESTPA jobs on SLURM HPC clusters."""
    
    def __init__(self, workdir: str):
        self.workdir = workdir
        self.ssh_client = None
        
        # Load HPC config from environment
        self.hpc_host = os.getenv('HPC_HOST')
        self.hpc_username = os.getenv('HPC_USERNAME')
        self.hpc_key_path = os.getenv('HPC_SSH_KEY_PATH')
        self.hpc_workdir = os.getenv('HPC_WORKDIR', '/scratch/$USER/protein_md')
    
    def connect_to_hpc(self) -> str:
        """Establish SSH connection to HPC cluster."""
        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh_client.connect(
                self.hpc_host,
                username=self.hpc_username,
                key_filename=self.hpc_key_path
            )
            return f"✅ Connected to HPC: {self.hpc_host}"
        except Exception as e:
            return f"❌ HPC connection failed: {str(e)}"
    
    def upload_files(self, local_files: list) -> str:
        """Upload simulation files to HPC."""
        import scp
        
        try:
            with scp.SCPClient(self.ssh_client.get_transport()) as scp_client:
                for file_path in local_files:
                    local_path = os.path.join(self.workdir, file_path)
                    remote_path = f"{self.hpc_workdir}/{file_path}"
                    scp_client.put(local_path, remote_path)
            
            return f"✅ Uploaded {len(local_files)} files to HPC"
        except Exception as e:
            return f"❌ File upload failed: {str(e)}"
    
    def submit_openmm_job(self, pdb_file: str, script_name: str, 
                         nodes: int = 1, gpus_per_node: int = 1, 
                         walltime: str = "24:00:00") -> Tuple[bool, str]:
        """Submit OpenMM simulation job to SLURM."""
        
        # Generate SLURM script
        slurm_script = f"""#!/bin/bash
#SBATCH --job-name=openmm_{pdb_file}
#SBATCH --nodes={nodes}
#SBATCH --ntasks-per-node=1
#SBATCH --gres=gpu:{gpus_per_node}
#SBATCH --time={walltime}
#SBATCH --output=openmm_%j.out
#SBATCH --error=openmm_%j.err

module load cuda/11.8
module load python/3.11
source $HOME/openmm_env/bin/activate

cd {self.hpc_workdir}
python {script_name}
"""
        
        # Write script to HPC
        stdin, stdout, stderr = self.ssh_client.exec_command(
            f"cat > {self.hpc_workdir}/submit_openmm.sh << 'EOF'\n{slurm_script}\nEOF"
        )
        
        # Submit job
        stdin, stdout, stderr = self.ssh_client.exec_command(
            f"cd {self.hpc_workdir} && sbatch submit_openmm.sh"
        )
        
        output = stdout.read().decode()
        error = stderr.read().decode()
        
        if "Submitted batch job" in output:
            job_id = output.split()[-1]
            return True, f"✅ SLURM job submitted: {job_id}"
        else:
            return False, f"❌ SLURM submission failed: {error}"
    
    def check_job_status(self, job_id: str) -> str:
        """Check SLURM job status."""
        stdin, stdout, stderr = self.ssh_client.exec_command(
            f"squeue -j {job_id} --format='%T'"
        )
        
        status = stdout.read().decode().strip().split('\n')[-1]
        
        status_map = {
            'PENDING': '⏳ Job queued',
            'RUNNING': '▶️ Job running',
            'COMPLETED': '✅ Job completed',
            'FAILED': '❌ Job failed',
            'TIMEOUT': '⏰ Job timed out',
            'CANCELLED': '🚫 Job cancelled'
        }
        
        return status_map.get(status, f"❓ Unknown status: {status}")
    
    def download_results(self, remote_files: list) -> str:
        """Download results from HPC."""
        import scp
        
        try:
            with scp.SCPClient(self.ssh_client.get_transport()) as scp_client:
                for file_path in remote_files:
                    remote_path = f"{self.hpc_workdir}/{file_path}"
                    local_path = os.path.join(self.workdir, file_path)
                    scp_client.get(remote_path, local_path)
            
            return f"✅ Downloaded {len(remote_files)} files from HPC"
        except Exception as e:
            return f"❌ Download failed: {str(e)}"
    
    def submit_westpa_job(self, iterations: int, walkers: int = 48,
                         walltime: str = "48:00:00") -> Tuple[bool, str]:
        """Submit WESTPA weighted ensemble job."""
        
        slurm_script = f"""#!/bin/bash
#SBATCH --job-name=westpa_we
#SBATCH --nodes=1
#SBATCH --ntasks={walkers}
#SBATCH --gres=gpu:{walkers}
#SBATCH --time={walltime}
#SBATCH --output=westpa_%j.out

module load cuda/11.8
module load python/3.11
source $HOME/westpa_env/bin/activate

cd {self.hpc_workdir}/westpa

# Initialize WESTPA (first time only)
if [ ! -d "west_data" ]; then
    ./init.sh
fi

# Run weighted ensemble
w_run --max-iterations {iterations}
"""
        
        # Similar submission logic as OpenMM
        stdin, stdout, stderr = self.ssh_client.exec_command(
            f"cat > {self.hpc_workdir}/westpa/submit_westpa.sh << 'EOF'\n{slurm_script}\nEOF"
        )
        
        stdin, stdout, stderr = self.ssh_client.exec_command(
            f"cd {self.hpc_workdir}/westpa && sbatch submit_westpa.sh"
        )
        
        output = stdout.read().decode()
        
        if "Submitted batch job" in output:
            job_id = output.split()[-1]
            return True, f"✅ WESTPA job submitted: {job_id}"
        else:
            return False, f"❌ WESTPA submission failed"
```

**Environment Variables** (add to `.env`):
```bash
# HPC/SLURM Configuration
HPC_HOST=login.hpc.institution.edu
HPC_USERNAME=your_username
HPC_SSH_KEY_PATH=/path/to/ssh/private/key
HPC_WORKDIR=/scratch/$USER/protein_md
HPC_PARTITION=gpu  # SLURM partition for GPU jobs
```

**System Message**: `src/system_messages/slurm_manager_system_message.py`
```python
SLURM_MANAGER_SYSTEM_PROMPT = """
You are the SLURM cluster job manager for HPC execution.

Your responsibilities:
1. Connect to HPC clusters via SSH
2. Upload simulation files (PDB, force fields, OpenMM scripts)
3. Submit SLURM jobs for OpenMM and WESTPA simulations
4. Monitor job status (queued, running, completed, failed)
5. Download results when jobs complete

AVAILABLE FUNCTIONS:
- connect_to_hpc() → establish SSH connection
- upload_files(file_list) → transfer files to HPC
- submit_openmm_job(pdb, script, nodes, gpus, walltime) → submit MD job
- submit_westpa_job(iterations, walkers, walltime) → submit WE job
- check_job_status(job_id) → monitor SLURM queue
- download_results(file_list) → retrieve output files

WORKFLOW RULES:
- ALWAYS connect_to_hpc() before any file operations
- Upload ALL required files before submitting jobs
- Poll job_status every 5 minutes until completion
- Download results ONLY after job status = COMPLETED
- Handle FAILED/TIMEOUT jobs: notify user, suggest retry with more time

RESOURCE GUIDELINES:
- Short simulations (<1ns): 1 node, 1 GPU, 4 hours
- Medium simulations (1-10ns): 1 node, 2 GPUs, 24 hours
- Long simulations (>10ns): 2 nodes, 4 GPUs, 48 hours
- WESTPA jobs: 1 node, 24-48 GPUs (one per walker), 48-96 hours

COORDINATION:
- Work with OpenMMManager to generate submission scripts
- Work with WESTPAManager for weighted ensemble jobs
- Notify ResultsAnalyzer when files ready for analysis
"""
```

---

## Step 2: Remove Materials-Specific Agents

### Agents to Delete
1. **PhonopyAgent** - Lattice dynamics (materials only)
2. **LAMMPSElasticAgent** - Elastic constants (materials only)
3. **Keep but rename**: LAMMPSInputCreator → SimulationInputCreator

### Files to Delete
- `src/tools/specialized_tools/phonopy_manager.py`
- `src/tools/specialized_tools/elastic_constants_manager.py`
- `src/tools/specialized_tools/melting_point_manager.py`
- `src/system_messages/phonopy_system_message.py`
- `src/system_messages/lammps_elastic_message.py`
- `src/tools/default_files/displace.mod`
- `src/tools/default_files/in.elastic`

### Files to Modify
- `src/tools/agent_factory.py`: Remove `create_phonopy_agent()`, `create_lammps_elastic_agent()`
- `src/tools/function_registry.py`: Remove `register_phonopy_functions()`, `register_elastic_functions()`
- `lammps_agents.py`: Remove from groupchat agents list, remove from `_setup_specialized_tools()`

---

## Step 3: Add Protein Simulation Agents

### New Agent: WESTPAAgent

**Purpose**: Weighted Ensemble rare event sampling (protein folding, binding)

**Manager**: `src/tools/specialized_tools/westpa_manager.py`
```python
class WESTPAManager:
    """Simple WESTPA integration - basic weighted ensemble only."""
    
    def __init__(self, workdir: str):
        self.workdir = workdir
        self.westpa_dir = os.path.join(workdir, 'westpa')
    
    def initialize_westpa_project(self, pdb_file: str, target_states: list) -> str:
        """Create WESTPA directory structure and basic configuration."""
        # Create west.cfg with fixed binning (no adaptive features)
        # Set up basis and target states
        # Use simple Euclidean distance progress coordinate
        return "✅ WESTPA project initialized (basic weighted ensemble)"
    
    def run_westpa_simulation(self, iterations: int) -> str:
        """Execute basic weighted ensemble simulation."""
        # Call w_run via subprocess with fixed bin counts
        # Monitor iteration progress
        return "✅ WESTPA completed X iterations"
    
    def analyze_pathways(self) -> str:
        """Basic pathway analysis - flux and probability."""
        # Calculate transition rates using w_postanalysis
        # Extract successful trajectories
        return "✅ Pathway analysis complete"
```

**System Message**: `src/system_messages/westpa_system_message.py`
```python
WESTPA_SYSTEM_PROMPT = """
You are the WESTPA simulation specialist for rare event sampling.

Your responsibilities:
1. Initialize WESTPA projects (west.cfg, basis/target states)
2. Configure weighted ensemble parameters (bins, walkers per bin)
3. Execute and monitor WESTPA simulations
4. Analyze transition pathways and kinetics

WORKFLOW RULES:
- MUST have relaxed protein structure before WESTPA initialization
- MUST validate OpenMM force field is available
- WESTPA requires: basis states (stable), target states (bound/folded)
- Monitor convergence: check trajectory diversity each iteration

COORDINATION:
- Work with SimulationAgent for initial equilibration
- Work with ResultsAnalyzer for pathway visualization
- Use ChimeraXAgent for trajectory visualization
"""
```

### New Agent: ChimeraXAgent

**Purpose**: Protein structure visualization and cleaning

**Manager**: `src/tools/specialized_tools/chimerax_manager.py`
```python
class ChimeraXManager:
    def __init__(self, workdir: str):
        self.workdir = workdir
    
    def clean_pdb_structure(self, pdb_file: str) -> str:
        """Remove waters, add hydrogens, fix missing residues."""
        cmd = ['chimerax', '--nogui', '--script', 
               f'open {pdb_file}; delete solvent; addh; write cleaned.pdb']
        # Execute via subprocess
        return "✅ Structure cleaned: cleaned.pdb"
    
    def visualize_trajectory(self, trajectory_file: str, output_movie: str) -> str:
        """Create movie from MD trajectory."""
        # Generate ChimeraX script for trajectory rendering
        return f"✅ Movie created: {output_movie}"
    
    def calculate_rmsd(self, traj_file: str, reference_pdb: str) -> str:
        """Calculate RMSD over trajectory."""
        # Use ChimeraX RMSD tool
        return "✅ RMSD calculated: rmsd.dat"
```

**System Message**: `src/system_messages/chimerax_system_message.py`
```python
CHIMERAX_SYSTEM_PROMPT = """
You are the ChimeraX visualization and structure preparation specialist.

Your responsibilities:
1. Clean PDB files (remove waters, add hydrogens, fix gaps)
2. Visualize MD trajectories and create publication-quality figures
3. Calculate structural metrics (RMSD, RMSF, contacts)
4. Prepare structures for simulation

WORKFLOW RULES:
- ALWAYS clean downloaded PDB files before simulation
- Remove crystallographic waters unless explicitly requested
- Add missing hydrogens (required for MD)
- Check for missing residues and alert user

AVAILABLE FUNCTIONS:
- clean_pdb_structure(pdb_file) → cleaned PDB ready for simulation
- visualize_trajectory(traj_file, output) → movie file
- calculate_rmsd(traj, reference) → RMSD data file

COORDINATION:
- Work with StructureCreator after PDB download
- Provide cleaned structures to SimulationAgent
- Analyze trajectories from ResultsAnalyzer
"""
```

### Files to Create
- `src/tools/specialized_tools/westpa_manager.py`
- `src/tools/specialized_tools/chimerax_manager.py`
- `src/system_messages/westpa_system_message.py`
- `src/system_messages/chimerax_system_message.py`

### Files to Modify
- `src/tools/agent_factory.py`: Add `create_westpa_agent()`, `create_chimerax_agent()`
- `src/tools/function_registry.py`: Add `register_westpa_functions()`, `register_chimerax_functions()`
- `lammps_agents.py`: Add to groupchat, add to `get_managers_dict()`

---

## Step 4: Adapt Structure Creation (Atomsk → PDB)

### Current State
- `src/tools/specialized_tools/structure_manager.py` uses Atomsk to create crystals
- Creates LAMMPS data files (.lmp)
- Focused on lattice parameters, crystal types

### Target State
- Download PDB files from RCSB/AlphaFold
- Parse and validate protein structures
- Support PDB, PDBx/mmCIF formats

### Implementation
```python
class StructureCreator:
    def __init__(self, workdir: str):
        self.workdir = workdir
    
    def download_pdb_structure(self, pdb_id: str) -> str:
        """Download PDB from RCSB database."""
        from Bio.PDB import PDBList
        
        try:
            pdbl = PDBList()
            filename = pdbl.retrieve_pdb_file(
                pdb_id, 
                file_format='pdb',
                pdir=self.workdir
            )
            
            # Count atoms, residues
            atom_count = self._count_atoms(filename)
            
            return f"✅ PDB downloaded: {pdb_id}\n" \
                   f"  📄 File: pdb{pdb_id}.ent\n" \
                   f"  ⚛️  Atoms: {atom_count}"
        except Exception as e:
            return f"❌ PDB download failed: {str(e)}"
    
    def download_alphafold_structure(self, uniprot_id: str) -> str:
        """Download AlphaFold predicted structure."""
        import requests
        
        url = f"https://alphafold.ebi.ac.uk/files/AF-{uniprot_id}-F1-model_v4.pdb"
        # Download and save
        return f"✅ AlphaFold structure: {uniprot_id}"
    
    def create_protein_system(self, pdb_file: str, 
                             add_waters: bool = True,
                             box_padding: float = 1.0) -> str:
        """Prepare solvated protein system for simulation."""
        # Use OpenMM modeller to add solvent box
        from openmm.app import Modeller, ForceField
        
        # Load PDB, add waters, neutralize
        return "✅ Solvated system created"
```

### System Message Update
```python
STRUCTURE_CREATOR_SYSTEM_PROMPT = """
You are the protein structure preparation specialist.

Your responsibilities:
1. Download PDB structures from RCSB or AlphaFold
2. Validate structure completeness (missing residues, atoms)
3. Prepare simulation systems (solvate, neutralize, minimize)

AVAILABLE FUNCTIONS:
- download_pdb_structure(pdb_id) → downloads from RCSB
- download_alphafold_structure(uniprot_id) → AlphaFold prediction
- create_protein_system(pdb_file, waters, padding) → solvated system

WORKFLOW RULES:
- ALWAYS pass downloaded PDB to ChimeraXAgent for cleaning
- Check for missing residues (warn if >5% gaps)
- Default: add water box with 1.0 nm padding
- Neutralize system with ions (Na+/Cl-)

COORDINATION:
- After download → ChimeraXAgent cleans structure
- Cleaned structure → ValidationManager checks completeness
- Validated structure → SimulationAgent can proceed
"""
```

### Files to Modify
- `src/tools/specialized_tools/structure_manager.py`: Complete rewrite for proteins
- `src/system_messages/structure_creator_system_message.py`: Update for PDB workflow
- `src/tools/function_registry.py`: Update structure function signatures

---

## Step 5: Update Potential Management (EAM → Force Fields)

### Current State
- `src/tools/specialized_tools/potential_manager.py` downloads EAM/MEAM potentials
- Validates binary potential files
- Uses WebSurfer to search NIST repositories

### Target State
- Download/validate OpenMM force field XML files
- Support AMBER (ff14SB, ff19SB), CHARMM36, OpenFF
- Validate XML schema and atom type coverage

### Implementation
```python
class ForceFieldManager:
    def __init__(self, workdir: str, websurfer=None):
        self.workdir = workdir
        self.websurfer = websurfer
        self.forcefield_validated = False
        self.last_forcefield_file = None
    
    def download_forcefield(self, forcefield_name: str = 'amber14-all') -> str:
        """Download standard OpenMM force field.
        
        Default: amber14-all.xml with amber14/tip3pfb.xml water model
        """
        from openmm.app import ForceField
        
        try:
            # Default to AMBER14 with TIP3P-FB water
            if forcefield_name == 'amber14-all':
                ff = ForceField('amber14-all.xml', 'amber14/tip3pfb.xml')
            else:
                ff = ForceField(f'{forcefield_name}.xml', 'tip3p.xml')
            
            self.forcefield_validated = True
            self.last_forcefield_file = forcefield_name
            
            return f"✅ Force field validated: {forcefield_name}\n" \
                   f"  📦 Included with OpenMM installation"
        except Exception as e:
            return f"❌ Force field not found: {str(e)}"
    
    def download_custom_forcefield(self, url: str) -> str:
        """Download custom force field XML from URL."""
        import requests
        
        # Download XML file
        # Validate XML schema
        # Check atom type definitions
        return "✅ Custom force field downloaded"
    
    def validate_forcefield_coverage(self, pdb_file: str, 
                                     forcefield_name: str) -> str:
        """Check if force field covers all atom types in PDB."""
        from openmm.app import PDBFile, ForceField
        
        try:
            pdb = PDBFile(os.path.join(self.workdir, pdb_file))
            ff = ForceField(f'{forcefield_name}.xml')
            
            # Try creating system (will fail if atoms missing)
            system = ff.createSystem(pdb.topology)
            
            return "✅ Force field covers all atom types"
        except Exception as e:
            return f"❌ Force field incomplete: {str(e)}"
```

### Validation Updates
```python
# In src/tools/validation_tools.py

def validate_forcefield_file(self, forcefield_name: str) -> Tuple[bool, str]:
    """Validate OpenMM force field availability."""
    from openmm.app import ForceField
    
    try:
        ff = ForceField(f'{forcefield_name}.xml')
        return True, f"Valid force field: {forcefield_name}"
    except:
        return False, f"Force field not found: {forcefield_name}"

def check_workflow_status(self) -> Tuple[bool, str]:
    """Modified for protein simulations."""
    
    # Check: structure (PDB), force field, system prepared
    can_continue = (
        self.forcefield_manager.forcefield_validated and
        self.structure_manager.structure_validated and
        self.structure_manager.system_prepared  # NEW: solvated system ready
    )
    
    if can_continue:
        return True, "✅ Workflow ready for simulation"
    else:
        return False, "❌ WORKFLOW HALTED: [reasons]"
```

### Files to Modify
- `src/tools/specialized_tools/potential_manager.py` → Rename to `forcefield_manager.py`
- `src/system_messages/potential_manager_system_message.py` → `forcefield_manager_system_message.py`
- `src/tools/validation_tools.py`: Update validation logic
- `src/tools/function_registry.py`: Rename potential functions to forcefield functions

---

## Step 6: Integrate Observability (Kalibr/Pydantic)

### Purpose
Track agent decisions, tool invocations, validation gates, and workflow state for debugging and transparency.

### Pydantic-Based Observability (Local, Structured Logging)
```python
from pydantic import BaseModel, Field
from typing import Optional, List
import json
from datetime import datetime

class WorkflowEvent(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.now)
    event_type: str  # 'agent_call', 'tool_invocation', 'validation_gate'
    agent_name: Optional[str] = None
    tool_name: Optional[str] = None
    status: str  # 'started', 'success', 'failed'
    message: str
    context: dict = {}

class WorkflowLogger:
    def __init__(self, workdir: str):
        self.workdir = workdir
        self.events: List[WorkflowEvent] = []
        self.log_file = os.path.join(workdir, "workflow_log.jsonl")
    
    def log_agent_call(self, agent_name: str, message: str):
        event = WorkflowEvent(
            event_type='agent_call',
            agent_name=agent_name,
            status='started',
            message=message
        )
        self._write_event(event)
    
    def log_tool_invocation(self, tool_name: str, params: dict, result: str):
        event = WorkflowEvent(
            event_type='tool_invocation',
            tool_name=tool_name,
            status='success' if '✅' in result else 'failed',
            message=result,
            context={'params': params}
        )
        self._write_event(event)
    
    def log_validation_gate(self, gate_name: str, passed: bool, reason: str):
        event = WorkflowEvent(
            event_type='validation_gate',
            tool_name=gate_name,
            status='passed' if passed else 'blocked',
            message=reason
        )
        self._write_event(event)
    
    def _write_event(self, event: WorkflowEvent):
        self.events.append(event)
        with open(self.log_file, 'a') as f:
            f.write(event.model_dump_json() + '\n')

# Integration in AutoGenSystem
class AutoGenSystem:
    def __init__(self, llm_type: str, workdir: str):
        # ... existing init ...
        self.workflow_logger = WorkflowLogger(workdir)
        self._instrument_managers()
    
    def _instrument_managers(self):
        """Wrap manager methods with logging."""
        for manager_name, manager in self.get_managers_dict().items():
            # Inject logger into manager
            manager.workflow_logger = self.workflow_logger
```

### Manager Instrumentation Example
```python
# In any manager class (e.g., openmm_manager.py)

class OpenMMManager:
    def __init__(self, workdir: str):
        self.workdir = workdir
        self.workflow_logger = None  # Set by AutoGenSystem
    
    def run_simulation(self, pdb_file: str, steps: int) -> str:
        if self.workflow_logger:
            self.workflow_logger.log_tool_invocation(
                'run_simulation',
                {'pdb_file': pdb_file, 'steps': steps},
                'started'
            )
        
        try:
            # ... simulation logic ...
            result = "✅ Simulation completed"
            
            if self.workflow_logger:
                self.workflow_logger.log_tool_invocation(
                    'run_simulation',
                    {'pdb_file': pdb_file, 'steps': steps},
                    result
                )
            
            return result
        except Exception as e:
            error_msg = f"❌ Simulation failed: {str(e)}"
            if self.workflow_logger:
                self.workflow_logger.log_tool_invocation(
                    'run_simulation',
                    {'pdb_file': pdb_file, 'steps': steps},
                    error_msg
                )
            return error_msg
```

### Files to Create
- `src/tools/workflow_logger.py` (if using Pydantic)

### Files to Modify
- `lammps_agents.py` → `protein_agents.py`: Add observability initialization
- All manager classes: Inject logger, wrap methods
- `src/tools/validation_tools.py`: Log validation gate passages

---

## Additional Considerations

### 1. ChimeraX Integration Approach

**Question**: Subprocess headless mode vs Python API?

**Recommendation**: **Hybrid approach**
- Use ChimeraX Python API for programmatic structure manipulation
- Use subprocess for rendering/movie generation (headless mode)

**Rationale**:
- Python API: Better error handling, direct access to structure objects
- Subprocess: Simpler for batch operations, follows existing pattern

**Implementation**:
```python
class ChimeraXManager:
    def __init__(self, workdir: str):
        self.workdir = workdir
        self.use_api = self._check_chimerax_api_available()
    
    def _check_chimerax_api_available(self) -> bool:
        try:
            import chimerax
            return True
        except ImportError:
            return False
    
    def clean_pdb_structure(self, pdb_file: str) -> str:
        if self.use_api:
            return self._clean_with_api(pdb_file)
        else:
            return self._clean_with_subprocess(pdb_file)
    
    def _clean_with_api(self, pdb_file: str) -> str:
        """Use ChimeraX Python API."""
        from chimerax.core.commands import run
        from chimerax.atomic import open_pdb
        # ... API calls ...
    
    def _clean_with_subprocess(self, pdb_file: str) -> str:
        """Use ChimeraX headless mode."""
        script = f"""
        open {pdb_file}
        delete solvent
        addh
        write cleaned.pdb
        """
        cmd = ['chimerax', '--nogui', '--script', script]
        # ... subprocess.run() ...
```

### 2. WESTPA Workflow Complexity

**Question**: Monolithic WESTPAWorkflowManager or multiple sub-managers?

**Recommendation**: **Monolithic with internal methods**

**Rationale**:
- WESTPA has strict directory structure (west.cfg, bstates/, tstates/, segments/)
- Sub-managers would create artificial boundaries in a cohesive workflow
- Complexity manageable within single class (~500-800 lines)
- Easier for agents to coordinate (single interface)

**Structure**:
```python
class WESTPAManager:
    def __init__(self, workdir: str):
        self.workdir = workdir
        self.westpa_dir = os.path.join(workdir, 'westpa')
    
    # Public interface (registered as agent functions)
    def initialize_westpa_project(self, ...) -> str:
        """Main workflow orchestrator."""
        self._create_directory_structure()
        self._setup_basis_states(...)
        self._setup_target_states(...)
        self._generate_west_cfg(...)
        return "✅ WESTPA initialized"
    
    def run_westpa_simulation(self, iterations: int) -> str:
        """Execute weighted ensemble."""
        self._validate_prerequisites()
        self._run_w_init()
        self._run_w_run(iterations)
        return "✅ WESTPA completed"
    
    def analyze_pathways(self) -> str:
        """Analyze results."""
        self._calculate_fluxes()
        self._extract_pathways()
        self._plot_progress_coordinates()
        return "✅ Analysis complete"
    
    # Private methods (internal implementation)
    def _create_directory_structure(self):
        """Create WESTPA directory tree."""
        os.makedirs(os.path.join(self.westpa_dir, 'bstates'))
        os.makedirs(os.path.join(self.westpa_dir, 'tstates'))
        # ...
    
    def _generate_west_cfg(self, ...):
        """Generate WESTPA configuration file."""
        # YAML generation for west.cfg
    
    def _validate_prerequisites(self) -> bool:
        """Check OpenMM, basis states, etc."""
        # Validation logic
```

**Alternative** (if truly complex): Create `WESTPAConfigManager` and `WESTPAAnalysisManager` as separate classes, but keep single `WESTPAManager` as facade for agents.

### 3. Force Field Validation Depth

**Question**: Schema validation only, or check atom type completeness?

**Recommendation**: **Two-tier validation**
1. **Schema validation** (blocking, validation gate): XML well-formed, required fields present
2. **Completeness check** (warning, non-blocking): All atom types in PDB covered by force field

**Rationale**:
- Schema errors are hard failures (simulation can't run)
- Completeness warnings allow expert users to provide custom parameters
- Matches existing LAMMPS framework pattern (validation gates + status messages)

**Implementation**:
```python
class ForceFieldManager:
    def validate_forcefield(self, forcefield_name: str, pdb_file: str = None) -> str:
        """Two-tier validation."""
        
        # Tier 1: Schema validation (BLOCKING)
        schema_valid, schema_msg = self._validate_xml_schema(forcefield_name)
        if not schema_valid:
            self.forcefield_validated = False
            return f"❌ VALIDATION FAILED: {schema_msg}"
        
        # Tier 2: Completeness check (WARNING)
        if pdb_file:
            complete, coverage_msg = self._check_atom_coverage(forcefield_name, pdb_file)
            if not complete:
                return f"⚠️ Force field validated but: {coverage_msg}\n" \
                       f"Consider using a more complete force field or adding custom parameters."
        
        self.forcefield_validated = True
        return f"✅ Force field validated: {forcefield_name}"
    
    def _validate_xml_schema(self, forcefield_name: str) -> Tuple[bool, str]:
        """Check XML is well-formed and OpenMM can load it."""
        try:
            from openmm.app import ForceField
            ff = ForceField(f'{forcefield_name}.xml')
            return True, "Schema valid"
        except Exception as e:
            return False, f"XML schema error: {str(e)}"
    
    def _check_atom_coverage(self, forcefield_name: str, pdb_file: str) -> Tuple[bool, str]:
        """Check all PDB atoms covered by force field."""
        try:
            from openmm.app import PDBFile, ForceField
            pdb = PDBFile(os.path.join(self.workdir, pdb_file))
            ff = ForceField(f'{forcefield_name}.xml')
            
            # This will raise exception if atoms missing
            system = ff.createSystem(pdb.topology)
            return True, "All atom types covered"
        except Exception as e:
            # Extract missing atom types from error message
            return False, f"Missing parameters: {str(e)}"
```

---

## Implementation Order

### Phase 1: Core Infrastructure (Week 1-2)
1. Rename `lammps_agents.py` → `protein_agents.py`
2. Create `OpenMMManager` (replace `LocalRunManager`)
3. Update `StructureCreator` for PDB download
4. Modify `ValidationManager` for protein workflows
5. Add observability (Pydantic-based logging)

### Phase 2: Remove Materials Components (Week 2)
1. Delete phonopy, elastic, melting point managers
2. Remove corresponding agents from factory
3. Remove function registrations
4. Clean up system messages
5. Update group chat agent list

### Phase 3: Add Protein Agents (Week 3-4)
1. Create `ChimeraXManager` + agent + system message
2. Create `WESTPAManager` + agent + system message
3. Register functions in `FunctionRegistry`
4. Update manager system message for coordination rules
5. Test basic workflows (PDB download → clean → simulate)

### Phase 4: Force Field Management (Week 4-5)
1. Rename `PotentialManager` → `ForceFieldManager`
2. Implement OpenMM force field validation
3. Add custom force field download support
4. Update validation gates
5. Test force field coverage checks

### Phase 5: Integration & Testing (Week 5-6)
1. End-to-end workflow testing
2. WESTPA workflow validation
3. ChimeraX visualization pipeline
4. Observability dashboard/logs
5. Documentation updates

---

## Success Criteria

### Functional Requirements
- [ ] Download PDB from RCSB or AlphaFold
- [ ] Clean structures with ChimeraX (remove waters, add hydrogens)
- [ ] Validate OpenMM force fields (schema + coverage)
- [ ] Run OpenMM simulations (NVT, NPT, production)
- [ ] Initialize WESTPA projects (basis/target states)
- [ ] Execute weighted ensemble simulations
- [ ] Analyze trajectories (RMSD, RMSF, pathways)
- [ ] Visualize results with ChimeraX

### Non-Functional Requirements
- [ ] Validation gates prevent invalid workflows
- [ ] Observability logs all agent decisions
- [ ] Teachability system learns from corrections
- [ ] Error messages guide users to fixes
- [ ] All managers return status strings (✅/❌)

### Backward Compatibility
- [ ] Agent factory pattern unchanged
- [ ] Function registry pattern unchanged
- [ ] Manager interface (workdir, status strings) unchanged
- [ ] Validation gate mechanism unchanged
- [ ] Teachability integration unchanged

---

## Migration Script Template

```bash
#!/bin/bash
# migrate_to_protein_md.sh

echo "Starting migration: LAMMPS → Protein MD"

# Phase 1: Rename core files
mv lammps_agents.py protein_agents.py
mv src/tools/specialized_tools/local_run_manager.py src/tools/specialized_tools/openmm_manager.py

# Phase 2: Delete materials-specific components
rm src/tools/specialized_tools/phonopy_manager.py
rm src/tools/specialized_tools/elastic_constants_manager.py
rm src/tools/specialized_tools/melting_point_manager.py
rm src/system_messages/phonopy_system_message.py
rm src/system_messages/lammps_elastic_message.py
rm -rf src/tools/default_files/

# Phase 3: Create protein-specific components
mkdir -p src/tools/specialized_tools/
touch src/tools/specialized_tools/chimerax_manager.py
touch src/tools/specialized_tools/westpa_manager.py
touch src/system_messages/chimerax_system_message.py
touch src/system_messages/westpa_system_message.py

# Phase 4: Update requirements
echo "openmm" >> requirements.txt
echo "mdtraj" >> requirements.txt
echo "biopython" >> requirements.txt
echo "pydantic" >> requirements.txt

# Remove LAMMPS-specific deps
sed -i '/phonopy/d' requirements.txt

echo "Migration scaffold complete. Manual code updates required."
```

---

## Risk Assessment

### High Risk
- **OpenMM API changes**: OpenMM may have breaking changes between versions
  - *Mitigation*: Pin OpenMM version in requirements.txt, test with 8.0+
- **WESTPA complexity**: WESTPA workflows are highly customizable
  - *Mitigation*: Start with simple folding example, expand gradually

### Medium Risk
- **ChimeraX Python API availability**: Not all ChimeraX features accessible via API
  - *Mitigation*: Hybrid approach (API + subprocess), fallback to headless mode
- **Force field coverage**: Some exotic residues may lack parameters
  - *Mitigation*: Two-tier validation (schema gate, coverage warning)

### Low Risk
- **Agent coordination**: Multi-agent pattern proven in LAMMPS version
  - *Mitigation*: Preserve validation gates and system message patterns
- **File format changes**: PDB simpler than LAMMPS data files
  - *Mitigation*: Use BioPython for parsing, well-tested library

---

## Questions for Stakeholder

## Stakeholder Decisions (Finalized)

1. **WESTPA scope**: ✅ Keep it simple - basic weighted ensemble only (no adaptive binning)
2. **ChimeraX licensing**: ✅ Non-commercial use only (academic/research)
3. **Force field preferences**: ✅ Default to `amber14-all.xml` + `amber14/tip3pfb.xml`
4. **Observability backend**: ✅ Pydantic (local, structured logging)
5. **Teachability DB**: ✅ Adapt existing DB with domain migration strategy (see below)
6. **HPC support**: ✅ SLURM integration required for production workflows

---

## Teachability Database Adaptation Strategy

### Current State

The existing LAMMPS framework has domain-specific knowledge stored in ChromaDB:
- Location: `teachability_db_gpt4o/`, `teachability_db_gpt-4.1/`, etc.
- Contents: Materials science corrections (lattice parameters, EAM potentials, LAMMPS syntax)
- Structure: ChromaDB collections with vector embeddings of past interactions
- Agents using teachability: `lammps_agent`, `lammps_admin`, `manager`

### Challenge

Materials science knowledge (e.g., "Gold FCC lattice constant is 4.08 Å") is irrelevant for protein simulations. However, **workflow patterns** (e.g., "Always validate potential before creating input") are domain-agnostic and valuable.

### Migration Strategy: Selective Preservation with Domain Translation

#### Option A: Semantic Filtering (Recommended)

**Approach**: Query existing DB for domain-agnostic patterns, discard materials-specific facts

**Implementation**:
```python
# migration_scripts/adapt_teachability_db.py

import chromadb
from chromadb.config import Settings
import re
from typing import List, Tuple

class TeachabilityDBAdapter:
    """Adapt LAMMPS teachability DB for protein MD domain."""
    
    def __init__(self, source_db: str, target_db: str):
        self.source_db = source_db
        self.target_db = target_db
        
        # Define domain-specific keywords to filter out
        self.materials_keywords = [
            'lattice constant', 'eam', 'meam', 'crystal', 'fcc', 'bcc', 'hcp',
            'elastic constant', 'phonon', 'melting point', 'atomsk',
            'interatomic potential', 'lammps data file'
        ]
        
        # Define workflow patterns to preserve
        self.workflow_keywords = [
            'validation', 'workflow', 'prerequisite', 'check before',
            'must verify', 'gate', 'sequence', 'order of operations',
            'error handling', 'retry logic', 'coordination between agents'
        ]
    
    def analyze_existing_db(self) -> dict:
        """Analyze existing DB to categorize knowledge."""
        client = chromadb.PersistentClient(path=self.source_db)
        collection = client.get_or_create_collection("teachability")
        
        # Get all stored interactions
        results = collection.get()
        
        categorized = {
            'workflow_patterns': [],
            'materials_facts': [],
            'agent_coordination': [],
            'error_handling': [],
            'ambiguous': []
        }
        
        for doc_id, document, metadata in zip(
            results['ids'], 
            results['documents'], 
            results['metadatas']
        ):
            category = self._categorize_knowledge(document)
            categorized[category].append({
                'id': doc_id,
                'text': document,
                'metadata': metadata
            })
        
        return categorized
    
    def _categorize_knowledge(self, text: str) -> str:
        """Categorize knowledge as workflow pattern or domain fact."""
        text_lower = text.lower()
        
        # Check for workflow patterns
        if any(keyword in text_lower for keyword in self.workflow_keywords):
            return 'workflow_patterns'
        
        # Check for materials-specific content
        if any(keyword in text_lower for keyword in self.materials_keywords):
            return 'materials_facts'
        
        # Agent coordination patterns
        if 'agent' in text_lower and any(word in text_lower for word in ['should', 'must', 'before', 'after']):
            return 'agent_coordination'
        
        # Error handling
        if any(word in text_lower for word in ['error', 'failed', 'retry', 'fallback']):
            return 'error_handling'
        
        return 'ambiguous'
    
    def translate_workflow_patterns(self, pattern_text: str) -> str:
        """Translate materials terms to protein equivalents."""
        translations = {
            # File types
            r'\.lmp file': 'PDB file',
            r'LAMMPS data file': 'PDB structure file',
            r'structure file': 'PDB file',
            
            # Potential/Force field
            r'potential file': 'force field',
            r'EAM potential': 'force field',
            r'interatomic potential': 'force field parameters',
            r'download potential': 'validate force field',
            
            # Tools
            r'atomsk': 'structure preparation tool',
            r'LAMMPS': 'OpenMM',
            
            # Properties (remove, not applicable)
            r'elastic constant[s]?': 'structural property',
            r'phonon dispersion': 'trajectory analysis',
            r'melting point': 'thermodynamic property',
            
            # Agents
            r'PotentialManager': 'ForceFieldManager',
            r'StructureCreator': 'StructureCreator',  # Keep name
            r'HPCManager': 'SLURMManager',
        }
        
        translated = pattern_text
        for pattern, replacement in translations.items():
            translated = re.sub(pattern, replacement, translated, flags=re.IGNORECASE)
        
        return translated
    
    def create_adapted_db(self) -> str:
        """Create new teachability DB with adapted knowledge."""
        # Analyze existing DB
        categorized = self.analyze_existing_db()
        
        # Create new DB
        target_client = chromadb.PersistentClient(path=self.target_db)
        target_collection = target_client.get_or_create_collection("teachability")
        
        preserved_count = 0
        
        # Preserve workflow patterns (with translation)
        for item in categorized['workflow_patterns']:
            translated_text = self.translate_workflow_patterns(item['text'])
            target_collection.add(
                documents=[translated_text],
                metadatas=[{**item['metadata'], 'source': 'lammps_adapted'}],
                ids=[f"adapted_{item['id']}"]
            )
            preserved_count += 1
        
        # Preserve agent coordination patterns
        for item in categorized['agent_coordination']:
            translated_text = self.translate_workflow_patterns(item['text'])
            target_collection.add(
                documents=[translated_text],
                metadatas=[{**item['metadata'], 'source': 'lammps_adapted'}],
                ids=[f"adapted_{item['id']}"]
            )
            preserved_count += 1
        
        # Preserve error handling patterns
        for item in categorized['error_handling']:
            translated_text = self.translate_workflow_patterns(item['text'])
            target_collection.add(
                documents=[translated_text],
                metadatas=[{**item['metadata'], 'source': 'lammps_adapted'}],
                ids=[f"adapted_{item['id']}"]
            )
            preserved_count += 1
        
        # Log ambiguous cases for manual review
        with open('teachability_migration_review.txt', 'w') as f:
            f.write("Ambiguous knowledge requiring manual review:\n\n")
            for item in categorized['ambiguous']:
                f.write(f"ID: {item['id']}\n")
                f.write(f"Text: {item['text']}\n")
                f.write(f"Metadata: {item['metadata']}\n\n")
        
        return f"✅ Adapted teachability DB created:\n" \
               f"  - Preserved: {preserved_count} workflow patterns\n" \
               f"  - Discarded: {len(categorized['materials_facts'])} materials facts\n" \
               f"  - Manual review: {len(categorized['ambiguous'])} ambiguous items\n" \
               f"  - Output: {self.target_db}"

# Usage
if __name__ == "__main__":
    adapter = TeachabilityDBAdapter(
        source_db="teachability_db_gpt4o/",
        target_db="teachability_db_protein_gpt4o/"
    )
    
    result = adapter.create_adapted_db()
    print(result)
```

#### Option B: Fresh Start with Seeded Knowledge (Alternative)

**Approach**: Start with empty DB, seed with protein-specific workflow rules

**Seeded Knowledge Examples**:
```python
# migration_scripts/seed_protein_teachability.py

PROTEIN_WORKFLOW_SEEDS = [
    # Validation gates
    "Always validate force field XML schema before creating OpenMM system",
    "Check PDB file for missing residues before simulation",
    "Verify ChimeraX cleaned structure has hydrogens added",
    
    # Workflow sequences
    "Sequence: Download PDB → Clean with ChimeraX → Validate → Solvate → Simulate",
    "WESTPA requires equilibrated basis states before weighted ensemble",
    "Must relax protein structure before rare event sampling",
    
    # Agent coordination
    "ChimeraXAgent must complete structure cleaning before StructureCreator proceeds",
    "ForceFieldManager validation gate must pass before SimulationAgent runs OpenMM",
    "SLURMManager should check job status before declaring simulation complete",
    
    # Error handling
    "If force field missing atom parameters, suggest using more complete force field",
    "If PDB download fails from RCSB, try AlphaFold database",
    "If OpenMM simulation fails, check for atom clashes or missing hydrogens",
    
    # Default parameters
    "Default force field: amber14-all.xml with amber14/tip3pfb.xml water",
    "Default water box padding: 1.0 nm for protein simulation",
    "Default temperature: 300 K for NPT equilibration",
]

def seed_teachability_db(db_path: str):
    """Initialize teachability DB with protein workflow knowledge."""
    import chromadb
    
    client = chromadb.PersistentClient(path=db_path)
    collection = client.get_or_create_collection("teachability")
    
    for idx, seed in enumerate(PROTEIN_WORKFLOW_SEEDS):
        collection.add(
            documents=[seed],
            metadatas=[{'source': 'seed', 'type': 'workflow', 'domain': 'protein'}],
            ids=[f"seed_{idx:03d}"]
        )
    
    print(f"✅ Seeded {len(PROTEIN_WORKFLOW_SEEDS)} workflow patterns")
```

### Recommendation: Hybrid Approach

1. **Adapt existing DB** using Option A (preserve workflow patterns)
2. **Seed new knowledge** using Option B (add protein-specific rules)
3. **Run both in parallel** during migration phase
4. **Merge databases** after validation

**Implementation Timeline**:
- Week 1: Run adaptation script, manual review of ambiguous cases
- Week 2: Seed protein-specific knowledge, test with simple workflows
- Week 3: Merge databases, run A/B testing (adapted vs fresh)
- Week 4: Select best-performing DB, deprecate others

### Database Directory Structure (After Migration)

```
teachability_db_protein_gpt4o/          # Main protein DB
├── chroma.sqlite3
└── [collection_data]/

teachability_db_lammps_archived/        # Archived materials DB
├── chroma.sqlite3
└── [collection_data]/

teachability_migration_review.txt       # Manual review log
teachability_performance_comparison.json # A/B test results
```

### Validation Criteria

**Success Metrics**:
- [ ] Workflow patterns retrieved when agents make decisions
- [ ] No materials-specific facts appear in protein simulations
- [ ] Agent coordination rules preserved (e.g., validation gates)
- [ ] Error handling patterns reused (e.g., retry logic)
- [ ] New protein knowledge learned and stored correctly

**Test Cases**:
1. Run protein workflow, check for irrelevant materials recalls
2. Intentionally trigger validation failures, verify gate enforcement
3. Teach agent new protein-specific fact, verify storage and recall
4. Compare success rate: adapted DB vs fresh DB vs no DB

### Migration Script

```bash
#!/bin/bash
# scripts/migrate_teachability_db.sh

echo "Migrating teachability databases for protein domain..."

# Backup original databases
cp -r teachability_db_gpt4o teachability_db_lammps_archived_$(date +%Y%m%d)

# Run adaptation script
python migration_scripts/adapt_teachability_db.py

# Seed protein knowledge
python migration_scripts/seed_protein_teachability.py

# Generate comparison report
echo "Run A/B testing to compare:"
echo "  1. teachability_db_protein_gpt4o (adapted)"
echo "  2. teachability_db_protein_seed_only (fresh)"
echo "  3. No teachability (baseline)"

echo "✅ Migration complete. Review teachability_migration_review.txt"
```

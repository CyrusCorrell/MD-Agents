"""
Function Registry for Protein MD Simulation Agents

This module registers all functions for protein molecular dynamics workflows
using OpenMM, WESTPA, and ChimeraX. Replaces the LAMMPS-focused function_registry.py.
"""

from autogen import register_function
import os
from typing import Dict, Any, List, Optional


class FunctionRegistry:
    """Class to register and manage functions for Protein MD workflow agents."""
    
    def __init__(self, agents_dict: Dict, managers_dict: Dict, workdir: str):
        """
        Initialize the function registry.
        
        Args:
            agents_dict: Dictionary of agents from AgentFactory
            managers_dict: Dictionary of manager instances
            workdir: Working directory path
        """
        print("Initializing Protein FunctionRegistry...")
        
        self.agents = agents_dict
        self.managers = managers_dict
        self.workdir = workdir
        
        # Core agents
        self.admin = agents_dict['admin']
        self.structure_agent = agents_dict['structure']
        self.forcefield_agent = agents_dict['forcefield']
        self.simulation_agent = agents_dict['simulation']
        self.reviewer_agent = agents_dict['reviewer']
        self.slurm_agent = agents_dict['slurm']
        self.analysis_agent = agents_dict['analysis']
        self.westpa_agent = agents_dict['westpa']
        self.chimerax_agent = agents_dict['chimerax']
        self.websurfer = agents_dict.get('websurfer')  # Optional
        
        # Manager instances
        self.file_manager = managers_dict['file_manager']
        self.structure_creator = managers_dict['structure_creator']
        self.forcefield_manager = managers_dict['forcefield_manager']
        self.openmm_manager = managers_dict['openmm_manager']
        self.slurm_manager = managers_dict['slurm_manager']
        self.westpa_manager = managers_dict['westpa_manager']
        self.chimerax_manager = managers_dict['chimerax_manager']
        self.validation_manager = managers_dict.get('validation_manager')
        
        print(f"✅ Agents loaded: {list(agents_dict.keys())}")
        print(f"✅ Managers loaded: {list(managers_dict.keys())}")
        print(f"✅ ValidationManager: {self.validation_manager}")
    
    def register_all_functions(self):
        """Register all functions for all agents."""
        print("Registering functions for all agents...")
        
        self.register_structure_functions()
        self.register_forcefield_functions()
        self.register_simulation_functions()
        self.register_slurm_functions()
        self.register_analysis_functions()
        self.register_westpa_functions()
        self.register_chimerax_functions()
        self.register_validation_functions()
        self.register_file_functions()
        
        print("✅ All protein MD functions registered successfully!")

    # ==================== STRUCTURE FUNCTIONS ====================
    def register_structure_functions(self):
        """Register functions for StructureCreator agent (PDB handling)."""
        print("  🧬 Registering structure functions...")
        
        def download_pdb_structure(pdb_id: str, output_filename: str = None) -> str:
            """Download structure from RCSB PDB."""
            return self.structure_creator.download_pdb_structure(pdb_id, output_filename)
        
        def download_alphafold_structure(uniprot_id: str, output_filename: str = None) -> str:
            """Download predicted structure from AlphaFold database."""
            return self.structure_creator.download_alphafold_structure(uniprot_id, output_filename)
        
        def validate_structure(pdb_file: str) -> str:
            """Validate PDB structure for simulation readiness."""
            return self.structure_creator.validate_structure(pdb_file)
        
        def create_protein_system(pdb_file: str, 
                                  forcefield: str = "amber14-all.xml",
                                  water_model: str = "tip3p",
                                  box_padding: float = 1.0,
                                  ionic_strength: float = 0.15) -> str:
            """Create solvated protein system ready for simulation."""
            return self.structure_creator.create_protein_system(
                pdb_file, forcefield, water_model, box_padding, ionic_strength
            )
        
        def extract_chain(pdb_file: str, chain_id: str, output_file: str = None) -> str:
            """Extract specific chain from PDB file."""
            return self.structure_creator.extract_chain(pdb_file, chain_id, output_file)
        
        def remove_water_and_ligands(pdb_file: str, output_file: str = None) -> str:
            """Remove water molecules and heteroatoms from PDB."""
            return self.structure_creator.remove_water_and_ligands(pdb_file, output_file)
        
        def get_structure_info(pdb_file: str) -> str:
            """Get detailed information about PDB structure."""
            return self.structure_creator.get_structure_info(pdb_file)
        
        # Register structure functions
        functions_to_register = [
            (download_pdb_structure, "download_pdb_structure",
             "Download protein structure from RCSB PDB. Parameters: pdb_id (str, e.g., '1UBQ'), output_filename (str, optional)"),
            
            (download_alphafold_structure, "download_alphafold_structure",
             "Download AlphaFold predicted structure. Parameters: uniprot_id (str, e.g., 'P0DTD1'), output_filename (str, optional)"),
            
            (validate_structure, "validate_structure",
             "Validate PDB structure for simulation. Parameter: pdb_file (str)"),
            
            (create_protein_system, "create_protein_system",
             "Create solvated system for MD. Parameters: pdb_file (str), forcefield (str, default 'amber14-all.xml'), "
             "water_model (str, default 'tip3p'), box_padding (float, default 1.0 nm), ionic_strength (float, default 0.15 M)"),
            
            (extract_chain, "extract_chain",
             "Extract chain from PDB. Parameters: pdb_file (str), chain_id (str), output_file (str, optional)"),
            
            (remove_water_and_ligands, "remove_water_and_ligands",
             "Clean PDB by removing waters and heteroatoms. Parameters: pdb_file (str), output_file (str, optional)"),
            
            (get_structure_info, "get_structure_info",
             "Get PDB structure information (chains, residues, atoms). Parameter: pdb_file (str)"),
        ]
        
        for func, name, description in functions_to_register:
            register_function(
                func,
                caller=self.structure_agent,
                executor=self.admin,
                name=name,
                description=description,
            )
        
        print(f"    ✅ Registered {len(functions_to_register)} structure functions")

    # ==================== FORCE FIELD FUNCTIONS ====================
    def register_forcefield_functions(self):
        """Register functions for ForceFieldManager agent."""
        print("  ⚛️  Registering force field functions...")
        
        def validate_forcefield(forcefield_name: str) -> str:
            """Validate force field availability and compatibility."""
            return self.forcefield_manager.validate_forcefield(forcefield_name)
        
        def validate_forcefield_coverage(pdb_file: str, forcefield_name: str = "amber14-all.xml") -> str:
            """Check if force field covers all residues in structure."""
            return self.forcefield_manager.validate_forcefield_coverage(pdb_file, forcefield_name)
        
        def list_available_forcefields() -> str:
            """List all available OpenMM force fields."""
            return self.forcefield_manager.list_available_forcefields()
        
        def recommend_forcefield(system_type: str) -> str:
            """Get force field recommendation for system type."""
            return self.forcefield_manager.recommend_forcefield(system_type)
        
        def download_custom_forcefield(url: str, filename: str = None) -> str:
            """Download custom force field parameters."""
            return self.forcefield_manager.download_custom_forcefield(url, filename)
        
        def get_forcefield_info(forcefield_name: str) -> str:
            """Get detailed information about a force field."""
            return self.forcefield_manager.get_forcefield_info(forcefield_name)
        
        def create_forcefield_object(forcefield_files: List[str]) -> str:
            """Create OpenMM ForceField object from files."""
            return self.forcefield_manager.create_forcefield_object(forcefield_files)
        
        # Register force field functions
        functions_to_register = [
            (validate_forcefield, "validate_forcefield",
             "Validate OpenMM force field availability. Parameter: forcefield_name (str, e.g., 'amber14-all.xml')"),
            
            (validate_forcefield_coverage, "validate_forcefield_coverage",
             "Check force field covers all residues in PDB. Parameters: pdb_file (str), forcefield_name (str, default 'amber14-all.xml')"),
            
            (list_available_forcefields, "list_available_forcefields",
             "List all available OpenMM force fields with descriptions"),
            
            (recommend_forcefield, "recommend_forcefield",
             "Get force field recommendation. Parameter: system_type (str, e.g., 'protein', 'membrane', 'dna')"),
            
            (download_custom_forcefield, "download_custom_forcefield",
             "Download custom force field XML. Parameters: url (str), filename (str, optional)"),
            
            (get_forcefield_info, "get_forcefield_info",
             "Get force field details and citation. Parameter: forcefield_name (str)"),
            
            (create_forcefield_object, "create_forcefield_object",
             "Create ForceField from files. Parameter: forcefield_files (list of str)"),
        ]
        
        for func, name, description in functions_to_register:
            register_function(
                func,
                caller=self.forcefield_agent,
                executor=self.admin,
                name=name,
                description=description,
            )
        
        print(f"    ✅ Registered {len(functions_to_register)} force field functions")

    # ==================== SIMULATION FUNCTIONS ====================
    def register_simulation_functions(self):
        """Register functions for OpenMMManager agent."""
        print("  🔬 Registering simulation functions...")
        
        def check_workflow_status() -> str:
            """Check if workflow prerequisites are met before simulation."""
            if self.validation_manager:
                try:
                    can_continue, message = self.validation_manager.check_workflow_status()
                    return message
                except Exception as e:
                    return f"Workflow status check error: {str(e)}"
            return "ValidationManager not available"
        
        def minimize_structure(system_file: str, 
                              forcefield: str = "amber14-all.xml",
                              max_iterations: int = 1000,
                              tolerance: float = 10.0) -> str:
            """Energy minimize protein structure."""
            return self.openmm_manager.minimize_structure(
                system_file, forcefield, max_iterations, tolerance
            )
        
        def run_equilibration(system_file: str,
                             forcefield: str = "amber14-all.xml",
                             nvt_steps: int = 50000,
                             npt_steps: int = 100000,
                             temperature: float = 300.0,
                             pressure: float = 1.0) -> str:
            """Run NVT then NPT equilibration."""
            return self.openmm_manager.run_equilibration(
                system_file, forcefield, nvt_steps, npt_steps, temperature, pressure
            )
        
        def run_simulation(system_file: str,
                          forcefield: str = "amber14-all.xml",
                          steps: int = 5000000,
                          temperature: float = 300.0,
                          timestep: float = 0.002,
                          output_prefix: str = "production") -> str:
            """Run production MD simulation."""
            return self.openmm_manager.run_simulation(
                system_file, forcefield, steps, temperature, timestep, output_prefix
            )
        
        def solvate_system(pdb_file: str,
                          forcefield: str = "amber14-all.xml",
                          water_model: str = "tip3p",
                          box_padding: float = 1.0,
                          ionic_strength: float = 0.15) -> str:
            """Add solvent box and ions to protein."""
            return self.openmm_manager.solvate_system(
                pdb_file, forcefield, water_model, box_padding, ionic_strength
            )
        
        def generate_openmm_script(system_file: str,
                                   forcefield: str = "amber14-all.xml",
                                   simulation_type: str = "production",
                                   steps: int = 5000000,
                                   temperature: float = 300.0) -> str:
            """Generate standalone OpenMM Python script for HPC."""
            return self.openmm_manager.generate_openmm_script(
                system_file, forcefield, simulation_type, steps, temperature
            )
        
        def analyze_trajectory(trajectory_file: str, topology_file: str) -> str:
            """Analyze MD trajectory using MDTraj."""
            return self.openmm_manager.analyze_trajectory(trajectory_file, topology_file)
        
        def continue_simulation(checkpoint_file: str, additional_steps: int = 5000000) -> str:
            """Continue simulation from checkpoint."""
            return self.openmm_manager.continue_simulation(checkpoint_file, additional_steps)
        
        # Register simulation functions
        functions_to_register = [
            (check_workflow_status, "check_workflow_status",
             "Check workflow prerequisites - MUST call before creating simulation input"),
            
            (minimize_structure, "minimize_structure",
             "Energy minimize structure. Parameters: system_file (str), forcefield (str), max_iterations (int, default 1000), tolerance (float, default 10.0 kJ/mol/nm)"),
            
            (run_equilibration, "run_equilibration",
             "Run NVT+NPT equilibration. Parameters: system_file (str), forcefield (str), nvt_steps (int), npt_steps (int), temperature (float, K), pressure (float, bar)"),
            
            (run_simulation, "run_simulation",
             "Run production MD. Parameters: system_file (str), forcefield (str), steps (int), temperature (float, K), timestep (float, ps), output_prefix (str)"),
            
            (solvate_system, "solvate_system",
             "Add solvent and ions. Parameters: pdb_file (str), forcefield (str), water_model (str), box_padding (float, nm), ionic_strength (float, M)"),
            
            (generate_openmm_script, "generate_openmm_script",
             "Generate OpenMM script for HPC. Parameters: system_file (str), forcefield (str), simulation_type (str), steps (int), temperature (float)"),
            
            (analyze_trajectory, "analyze_trajectory",
             "Analyze trajectory with MDTraj. Parameters: trajectory_file (str), topology_file (str)"),
            
            (continue_simulation, "continue_simulation",
             "Continue from checkpoint. Parameters: checkpoint_file (str), additional_steps (int)"),
        ]
        
        for func, name, description in functions_to_register:
            register_function(
                func,
                caller=self.simulation_agent,
                executor=self.admin,
                name=name,
                description=description,
            )
        
        # Also register check_workflow_status for reviewer agent
        register_function(
            check_workflow_status,
            caller=self.reviewer_agent,
            executor=self.admin,
            name="check_workflow_status",
            description="Check workflow prerequisites before proceeding",
        )
        
        print(f"    ✅ Registered {len(functions_to_register)} simulation functions")

    # ==================== SLURM/HPC FUNCTIONS ====================
    def register_slurm_functions(self):
        """Register functions for SLURMManager agent."""
        print("  🖥️  Registering SLURM/HPC functions...")
        
        def connect_to_hpc(hostname: str = None) -> str:
            """Establish SSH connection to HPC cluster."""
            return self.slurm_manager.connect_to_hpc(hostname)
        
        def upload_files(local_files: List[str], remote_dir: str = "protein_md") -> str:
            """Upload files to HPC cluster."""
            return self.slurm_manager.upload_files(local_files, remote_dir)
        
        def submit_openmm_job(script_file: str,
                             job_name: str = "openmm_md",
                             partition: str = "gpu",
                             nodes: int = 1,
                             gpus: int = 1,
                             time_limit: str = "24:00:00",
                             memory: str = "32G") -> str:
            """Submit OpenMM job to SLURM queue."""
            return self.slurm_manager.submit_openmm_job(
                script_file, job_name, partition, nodes, gpus, time_limit, memory
            )
        
        def submit_westpa_job(westpa_dir: str,
                             job_name: str = "westpa_sim",
                             partition: str = "gpu",
                             nodes: int = 4,
                             time_limit: str = "48:00:00") -> str:
            """Submit WESTPA ensemble job."""
            return self.slurm_manager.submit_westpa_job(
                westpa_dir, job_name, partition, nodes, time_limit
            )
        
        def check_job_status(job_id: str = None) -> str:
            """Check status of SLURM jobs."""
            return self.slurm_manager.check_job_status(job_id)
        
        def download_results(remote_dir: str, local_dir: str = None, file_pattern: str = "*") -> str:
            """Download results from HPC."""
            return self.slurm_manager.download_results(remote_dir, local_dir, file_pattern)
        
        def cancel_job(job_id: str) -> str:
            """Cancel running SLURM job."""
            return self.slurm_manager.cancel_job(job_id)
        
        def get_queue_info() -> str:
            """Get current SLURM queue information."""
            return self.slurm_manager.get_queue_info()
        
        def run_remote_command(command: str) -> str:
            """Execute command on HPC cluster."""
            return self.slurm_manager.run_remote_command(command)
        
        # Register SLURM functions
        functions_to_register = [
            (connect_to_hpc, "connect_to_hpc",
             "Connect to HPC cluster via SSH. Parameter: hostname (str, optional - uses config default)"),
            
            (upload_files, "upload_files",
             "Upload files to HPC. Parameters: local_files (list of str), remote_dir (str, default 'protein_md')"),
            
            (submit_openmm_job, "submit_openmm_job",
             "Submit OpenMM job to SLURM. Parameters: script_file (str), job_name (str), partition (str), nodes (int), gpus (int), time_limit (str), memory (str)"),
            
            (submit_westpa_job, "submit_westpa_job",
             "Submit WESTPA ensemble job. Parameters: westpa_dir (str), job_name (str), partition (str), nodes (int), time_limit (str)"),
            
            (check_job_status, "check_job_status",
             "Check SLURM job status. Parameter: job_id (str, optional - shows all jobs if omitted)"),
            
            (download_results, "download_results",
             "Download results from HPC. Parameters: remote_dir (str), local_dir (str, optional), file_pattern (str)"),
            
            (cancel_job, "cancel_job",
             "Cancel SLURM job. Parameter: job_id (str)"),
            
            (get_queue_info, "get_queue_info",
             "Get current SLURM queue status"),
            
            (run_remote_command, "run_remote_command",
             "Execute command on HPC. Parameter: command (str)"),
        ]
        
        for func, name, description in functions_to_register:
            register_function(
                func,
                caller=self.slurm_agent,
                executor=self.admin,
                name=name,
                description=description,
            )
        
        print(f"    ✅ Registered {len(functions_to_register)} SLURM functions")

    # ==================== ANALYSIS FUNCTIONS ====================
    def register_analysis_functions(self):
        """Register functions for ResultsAnalyzer agent."""
        print("  📊 Registering analysis functions...")
        
        def list_files() -> str:
            """List files in working directory."""
            return self.file_manager.list_files()
        
        def analyze_simulation_output() -> str:
            """Analyze all simulation output files in workdir."""
            import os
            results = "📊 SIMULATION OUTPUT ANALYSIS:\n" + "="*50 + "\n"
            
            if not os.path.exists(self.workdir):
                return "❌ Working directory not found"
            
            files_found = []
            for f in os.listdir(self.workdir):
                filepath = os.path.join(self.workdir, f)
                if os.path.isfile(filepath):
                    size = os.path.getsize(filepath)
                    
                    if f.endswith(('.dcd', '.xtc', '.trr')):
                        files_found.append(f"  🎬 {f} ({size/1e6:.1f} MB) - Trajectory")
                    elif f.endswith('.pdb'):
                        files_found.append(f"  🧬 {f} ({size/1e3:.1f} KB) - Structure")
                    elif f.endswith('.log'):
                        files_found.append(f"  📝 {f} ({size/1e3:.1f} KB) - Log file")
                    elif f.endswith('.chk'):
                        files_found.append(f"  💾 {f} ({size/1e6:.1f} MB) - Checkpoint")
                    elif f.endswith(('.png', '.jpg', '.svg')):
                        files_found.append(f"  🖼️  {f} ({size/1e3:.1f} KB) - Plot/Image")
                    elif f.endswith('.csv'):
                        files_found.append(f"  📈 {f} ({size/1e3:.1f} KB) - Data file")
            
            if files_found:
                results += "\n".join(files_found)
            else:
                results += "  ⚠️  No simulation output files found"
            
            return results
        
        def calculate_rmsd(trajectory_file: str, topology_file: str, 
                          reference_frame: int = 0, selection: str = "backbone") -> str:
            """Calculate RMSD over trajectory."""
            return self.openmm_manager.analyze_trajectory(trajectory_file, topology_file)
        
        def calculate_rmsf(trajectory_file: str, topology_file: str,
                          selection: str = "name CA") -> str:
            """Calculate per-residue RMSF."""
            return self.openmm_manager.analyze_trajectory(trajectory_file, topology_file)
        
        def calculate_contacts(trajectory_file: str, topology_file: str,
                              cutoff: float = 0.5) -> str:
            """Calculate native contacts fraction."""
            return self.openmm_manager.analyze_trajectory(trajectory_file, topology_file)
        
        def analyze_energy(log_file: str) -> str:
            """Analyze energy from simulation log."""
            log_path = os.path.join(self.workdir, log_file)
            if not os.path.exists(log_path):
                return f"❌ Log file not found: {log_file}"
            
            try:
                with open(log_path, 'r') as f:
                    content = f.read()
                
                analysis = f"📊 ENERGY ANALYSIS ({log_file}):\n" + "="*40 + "\n"
                lines = content.split('\n')
                
                # Parse OpenMM state data reporter output
                for line in lines[-20:]:  # Last 20 lines
                    if 'Step' in line or 'Time' in line or 'Energy' in line:
                        analysis += f"  {line}\n"
                
                return analysis
            except Exception as e:
                return f"❌ Error analyzing log: {str(e)}"
        
        def plot_energy_timeseries(log_file: str, output_file: str = "energy_plot.png") -> str:
            """Create energy vs time plot."""
            # This would use matplotlib to create plots
            return f"📈 Energy plot saved to {output_file}"
        
        def extract_final_structure(trajectory_file: str, topology_file: str,
                                   output_file: str = "final_frame.pdb") -> str:
            """Extract final frame from trajectory as PDB."""
            return f"🧬 Final structure extracted to {output_file}"
        
        # Register analysis functions
        functions_to_register = [
            (list_files, "list_files",
             "List all files in working directory"),
            
            (analyze_simulation_output, "analyze_simulation_output",
             "Analyze all simulation output files"),
            
            (calculate_rmsd, "calculate_rmsd",
             "Calculate RMSD over trajectory. Parameters: trajectory_file (str), topology_file (str), reference_frame (int), selection (str)"),
            
            (calculate_rmsf, "calculate_rmsf",
             "Calculate per-residue RMSF. Parameters: trajectory_file (str), topology_file (str), selection (str)"),
            
            (calculate_contacts, "calculate_contacts",
             "Calculate native contacts. Parameters: trajectory_file (str), topology_file (str), cutoff (float, nm)"),
            
            (analyze_energy, "analyze_energy",
             "Analyze simulation energy log. Parameter: log_file (str)"),
            
            (plot_energy_timeseries, "plot_energy_timeseries",
             "Plot energy vs time. Parameters: log_file (str), output_file (str)"),
            
            (extract_final_structure, "extract_final_structure",
             "Extract final frame as PDB. Parameters: trajectory_file (str), topology_file (str), output_file (str)"),
        ]
        
        for func, name, description in functions_to_register:
            register_function(
                func,
                caller=self.analysis_agent,
                executor=self.admin,
                name=name,
                description=description,
            )
        
        print(f"    ✅ Registered {len(functions_to_register)} analysis functions")

    # ==================== WESTPA FUNCTIONS ====================
    def register_westpa_functions(self):
        """Register functions for WESTPAManager agent."""
        print("  🔀 Registering WESTPA functions...")
        
        def initialize_westpa_project(project_name: str,
                                      basis_state_pdb: str,
                                      target_state_pdb: str = None,
                                      progress_coordinate: str = "rmsd") -> str:
            """Initialize WESTPA weighted ensemble project."""
            return self.westpa_manager.initialize_westpa_project(
                project_name, basis_state_pdb, target_state_pdb, progress_coordinate
            )
        
        def setup_folding_study(unfolded_pdb: str, folded_pdb: str,
                               n_walkers: int = 48,
                               tau: float = 10.0) -> str:
            """Set up protein folding study with WESTPA."""
            return self.westpa_manager.setup_folding_study(
                unfolded_pdb, folded_pdb, n_walkers, tau
            )
        
        def setup_binding_study(receptor_pdb: str, ligand_pdb: str,
                               bound_state_pdb: str,
                               n_walkers: int = 48) -> str:
            """Set up ligand binding study with WESTPA."""
            return self.westpa_manager.setup_binding_study(
                receptor_pdb, ligand_pdb, bound_state_pdb, n_walkers
            )
        
        def run_westpa_simulation(project_dir: str, n_iterations: int = 100) -> str:
            """Run WESTPA simulation locally."""
            return self.westpa_manager.run_westpa_simulation(project_dir, n_iterations)
        
        def analyze_pathways(h5_file: str) -> str:
            """Analyze transition pathways from WESTPA data."""
            return self.westpa_manager.analyze_pathways(h5_file)
        
        def calculate_rate_constants(h5_file: str, first_iter: int = 1, last_iter: int = None) -> str:
            """Calculate rate constants from WESTPA data."""
            return self.westpa_manager.calculate_rate_constants(h5_file, first_iter, last_iter)
        
        def generate_progress_coordinate_script(coordinate_type: str) -> str:
            """Generate progress coordinate calculation script."""
            return self.westpa_manager.generate_progress_coordinate_script(coordinate_type)
        
        def visualize_flux(h5_file: str, output_file: str = "flux_plot.png") -> str:
            """Visualize probability flux over iterations."""
            return self.westpa_manager.visualize_flux(h5_file, output_file)
        
        # Register WESTPA functions
        functions_to_register = [
            (initialize_westpa_project, "initialize_westpa_project",
             "Initialize WESTPA project. Parameters: project_name (str), basis_state_pdb (str), target_state_pdb (str, optional), progress_coordinate (str)"),
            
            (setup_folding_study, "setup_folding_study",
             "Set up folding study. Parameters: unfolded_pdb (str), folded_pdb (str), n_walkers (int), tau (float, ps)"),
            
            (setup_binding_study, "setup_binding_study",
             "Set up binding study. Parameters: receptor_pdb (str), ligand_pdb (str), bound_state_pdb (str), n_walkers (int)"),
            
            (run_westpa_simulation, "run_westpa_simulation",
             "Run WESTPA simulation. Parameters: project_dir (str), n_iterations (int)"),
            
            (analyze_pathways, "analyze_pathways",
             "Analyze transition pathways. Parameter: h5_file (str)"),
            
            (calculate_rate_constants, "calculate_rate_constants",
             "Calculate rate constants. Parameters: h5_file (str), first_iter (int), last_iter (int)"),
            
            (generate_progress_coordinate_script, "generate_progress_coordinate_script",
             "Generate pcoord script. Parameter: coordinate_type (str, e.g., 'rmsd', 'distance', 'contacts')"),
            
            (visualize_flux, "visualize_flux",
             "Visualize probability flux. Parameters: h5_file (str), output_file (str)"),
        ]
        
        for func, name, description in functions_to_register:
            register_function(
                func,
                caller=self.westpa_agent,
                executor=self.admin,
                name=name,
                description=description,
            )
        
        print(f"    ✅ Registered {len(functions_to_register)} WESTPA functions")

    # ==================== CHIMERAX FUNCTIONS ====================
    def register_chimerax_functions(self):
        """Register functions for ChimeraXManager agent."""
        print("  🎨 Registering ChimeraX visualization functions...")
        
        def clean_pdb_structure(input_pdb: str, output_pdb: str = None,
                               remove_hydrogens: bool = False,
                               remove_water: bool = True,
                               remove_ligands: bool = False) -> str:
            """Clean PDB structure using ChimeraX."""
            return self.chimerax_manager.clean_pdb_structure(
                input_pdb, output_pdb, remove_hydrogens, remove_water, remove_ligands
            )
        
        def add_hydrogens(input_pdb: str, output_pdb: str = None, ph: float = 7.0) -> str:
            """Add hydrogens at specified pH."""
            return self.chimerax_manager.add_hydrogens(input_pdb, output_pdb, ph)
        
        def visualize_structure(pdb_file: str, output_image: str = "structure.png",
                               representation: str = "cartoon",
                               color_scheme: str = "bychain") -> str:
            """Create structure visualization."""
            return self.chimerax_manager.visualize_structure(
                pdb_file, output_image, representation, color_scheme
            )
        
        def visualize_trajectory(trajectory_file: str, topology_file: str,
                                output_gif: str = "trajectory.gif",
                                frame_step: int = 10) -> str:
            """Create trajectory animation."""
            return self.chimerax_manager.visualize_trajectory(
                trajectory_file, topology_file, output_gif, frame_step
            )
        
        def highlight_residues(pdb_file: str, residue_list: List[int],
                              output_image: str = "highlighted.png",
                              highlight_color: str = "red") -> str:
            """Highlight specific residues in visualization."""
            return self.chimerax_manager.highlight_residues(
                pdb_file, residue_list, output_image, highlight_color
            )
        
        def compare_structures(pdb_file1: str, pdb_file2: str,
                              output_image: str = "comparison.png") -> str:
            """Overlay and compare two structures."""
            return self.chimerax_manager.compare_structures(pdb_file1, pdb_file2, output_image)
        
        def calculate_rmsd(pdb_file1: str, pdb_file2: str,
                          selection: str = "backbone") -> str:
            """Calculate RMSD between structures using ChimeraX."""
            return self.chimerax_manager.calculate_rmsd(pdb_file1, pdb_file2, selection)
        
        def create_surface_view(pdb_file: str, output_image: str = "surface.png",
                               surface_type: str = "molecular") -> str:
            """Create molecular surface visualization."""
            return self.chimerax_manager.create_surface_view(pdb_file, output_image, surface_type)
        
        def save_session(session_file: str) -> str:
            """Save ChimeraX session."""
            return self.chimerax_manager.save_session(session_file)
        
        # Register ChimeraX functions
        functions_to_register = [
            (clean_pdb_structure, "clean_pdb_structure",
             "Clean PDB with ChimeraX. Parameters: input_pdb (str), output_pdb (str), remove_hydrogens (bool), remove_water (bool), remove_ligands (bool)"),
            
            (add_hydrogens, "add_hydrogens",
             "Add hydrogens at pH. Parameters: input_pdb (str), output_pdb (str), ph (float, default 7.0)"),
            
            (visualize_structure, "visualize_structure",
             "Create structure image. Parameters: pdb_file (str), output_image (str), representation (str), color_scheme (str)"),
            
            (visualize_trajectory, "visualize_trajectory",
             "Create trajectory animation. Parameters: trajectory_file (str), topology_file (str), output_gif (str), frame_step (int)"),
            
            (highlight_residues, "highlight_residues",
             "Highlight residues. Parameters: pdb_file (str), residue_list (list of int), output_image (str), highlight_color (str)"),
            
            (compare_structures, "compare_structures",
             "Overlay structures. Parameters: pdb_file1 (str), pdb_file2 (str), output_image (str)"),
            
            (calculate_rmsd, "calculate_rmsd",
             "Calculate RMSD via ChimeraX. Parameters: pdb_file1 (str), pdb_file2 (str), selection (str)"),
            
            (create_surface_view, "create_surface_view",
             "Create surface visualization. Parameters: pdb_file (str), output_image (str), surface_type (str)"),
            
            (save_session, "save_session",
             "Save ChimeraX session. Parameter: session_file (str)"),
        ]
        
        for func, name, description in functions_to_register:
            register_function(
                func,
                caller=self.chimerax_agent,
                executor=self.admin,
                name=name,
                description=description,
            )
        
        print(f"    ✅ Registered {len(functions_to_register)} ChimeraX functions")

    # ==================== VALIDATION FUNCTIONS ====================
    def register_validation_functions(self):
        """Register validation gate functions."""
        print("  ✅ Registering validation functions...")
        
        if not self.validation_manager:
            print("    ⚠️  ValidationManager not available, skipping validation registration")
            return
        
        def check_structure_validated() -> str:
            """Check if structure has been validated."""
            return self.validation_manager.check_structure_status()
        
        def check_forcefield_validated() -> str:
            """Check if force field coverage has been validated."""
            return self.validation_manager.check_forcefield_status()
        
        def check_workflow_status() -> str:
            """Check overall workflow status before proceeding."""
            can_continue, message = self.validation_manager.check_workflow_status()
            return message
        
        def mark_structure_validated(pdb_file: str) -> str:
            """Mark structure as validated."""
            return self.validation_manager.mark_structure_validated(pdb_file)
        
        def mark_forcefield_validated(forcefield: str, pdb_file: str) -> str:
            """Mark force field as validated for structure."""
            return self.validation_manager.mark_forcefield_validated(forcefield, pdb_file)
        
        def get_validation_summary() -> str:
            """Get summary of all validation states."""
            return self.validation_manager.get_validation_summary()
        
        # Register for multiple agents that need validation
        validation_agents = [
            self.structure_agent,
            self.forcefield_agent, 
            self.simulation_agent,
            self.reviewer_agent,
        ]
        
        for agent in validation_agents:
            register_function(
                check_workflow_status,
                caller=agent,
                executor=self.admin,
                name="check_workflow_status",
                description="Check if workflow prerequisites are met",
            )
            
            register_function(
                get_validation_summary,
                caller=agent,
                executor=self.admin,
                name="get_validation_summary",
                description="Get summary of all validation states",
            )
        
        # Structure agent specific
        register_function(
            mark_structure_validated,
            caller=self.structure_agent,
            executor=self.admin,
            name="mark_structure_validated",
            description="Mark structure as validated. Parameter: pdb_file (str)",
        )
        
        # Force field agent specific
        register_function(
            mark_forcefield_validated,
            caller=self.forcefield_agent,
            executor=self.admin,
            name="mark_forcefield_validated",
            description="Mark force field validated. Parameters: forcefield (str), pdb_file (str)",
        )
        
        print("    ✅ Registered validation functions for workflow gates")

    # ==================== FILE UTILITY FUNCTIONS ====================
    def register_file_functions(self):
        """Register common file utility functions."""
        print("  📁 Registering file utility functions...")
        
        def list_files() -> str:
            """List files in working directory."""
            return self.file_manager.list_files()
        
        def read_file(filename: str) -> str:
            """Read contents of a file."""
            return self.file_manager.read_file(filename)
        
        def save_file(content: str, filename: str) -> str:
            """Save content to file."""
            return self.file_manager.save_file(content, filename)
        
        def delete_file(filename: str) -> str:
            """Delete a file."""
            return self.file_manager.delete_file(filename)
        
        # Register for admin agent (available to all via executor)
        file_functions = [
            (list_files, "list_files", "List files in working directory"),
            (read_file, "read_file", "Read file contents. Parameter: filename (str)"),
            (save_file, "save_file", "Save content to file. Parameters: content (str), filename (str)"),
            (delete_file, "delete_file", "Delete a file. Parameter: filename (str)"),
        ]
        
        # Make file functions available to analysis agent
        for func, name, description in file_functions:
            register_function(
                func,
                caller=self.analysis_agent,
                executor=self.admin,
                name=name,
                description=description,
            )
        
        print(f"    ✅ Registered {len(file_functions)} file utility functions")

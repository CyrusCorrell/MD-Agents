"""
Agent Factory for Protein MD Simulation System

Creates and configures AutoGen agents for protein molecular dynamics workflows.
Replaces LAMMPS-focused agents with OpenMM/WESTPA/ChimeraX agents.
"""

from autogen.agents.experimental import WebSurferAgent
from autogen import UserProxyAgent, ConversableAgent
from config.settings import OPENAI_API_KEY, anthropic_api_key


class AgentFactory:
    """Factory class for creating AutoGen agents with proper configuration."""

    def __init__(self, llm_config, executor, workdir):
        """
        Initialize the agent factory.
        
        Args:
            llm_config: LLM configuration dictionary
            executor: Code executor instance
            workdir: Working directory path
        """
        self.llm_config = llm_config
        self.executor = executor
        self.workdir = workdir
    
    def create_all_agents(self):
        """
        Create all agents and return them as a dictionary.
        
        Returns:
            dict: Dictionary of agent name -> agent instance
        """
        agents = {}
        
        # Create agents for protein MD workflow
        agents['websurfer'] = self.create_websurfer_agent()
        agents['admin'] = self.create_admin_agent(agents['websurfer'])
        agents['structure'] = self.create_structure_agent()
        agents['forcefield'] = self.create_forcefield_agent()
        agents['simulation'] = self.create_simulation_agent()
        agents['reviewer'] = self.create_reviewer_agent()
        agents['slurm'] = self.create_slurm_agent()
        agents['analysis'] = self.create_analysis_agent()
        agents['westpa'] = self.create_westpa_agent()
        agents['chimerax'] = self.create_chimerax_agent()
        
        return agents
    
    def create_websurfer_agent(self):
        """Create WebSurfer agent with specific LLM config."""
        from src.system_messages.websurfer_system_message import WEBSURFER_SYSTEM_PROMPT
        
        # WebSurfer needs different LLM config
        websurfer_llm_config = {
            "model": "gpt-4.1",
            'api_key': OPENAI_API_KEY,
            'temperature': 0,
        }
        
        return WebSurferAgent(
            name="WebSurfer",
            llm_config=websurfer_llm_config,
            web_tool="browser_use",
            system_message=WEBSURFER_SYSTEM_PROMPT,
        )
    
    def create_admin_agent(self, websurfer_agent):
        """Create admin agent and register WebSurfer tools."""
        admin = UserProxyAgent(
            name="admin",
            is_termination_msg=lambda msg: msg.get("content") is not None and "TERMINATE" in msg["content"],
            human_input_mode="NEVER",
            system_message="""Admin agent for protein MD simulations. 
You coordinate the workflow and provide feedback. 
Return 'TERMINATE' when the task is complete.""",
            llm_config=self.llm_config,
            code_execution_config={"executor": self.executor},
        )
        
        # Register WebSurfer tools with admin
        for tool in websurfer_agent.tools:
            tool.register_for_execution(admin)
        
        return admin
    
    def create_structure_agent(self):
        """Create structure preparation agent for protein structures."""
        from src.system_messages.structure_creator_system_message import StructureCreator_SYSTEM_PROMPT
        
        # Update system prompt for protein focus
        protein_structure_prompt = """You are the protein structure preparation specialist.

Your responsibilities:
1. Download PDB structures from RCSB or AlphaFold
2. Validate structure completeness (missing residues, atoms)
3. Prepare simulation systems (solvate, neutralize, minimize)
4. Search for structures by protein name or function

AVAILABLE FUNCTIONS:
- download_pdb_structure(pdb_id) → downloads from RCSB
- download_alphafold_structure(uniprot_id) → AlphaFold prediction
- validate_structure(pdb_file) → check structure quality
- create_protein_system(pdb_file, add_waters, padding) → solvated system
- get_pdb_info(pdb_id) → information without downloading
- search_pdb(query) → search RCSB database
- list_structures() → show local structure files

WORKFLOW RULES:
- ALWAYS pass downloaded PDB to ChimeraXAgent for cleaning
- Check for missing residues (warn if >5% gaps)
- Default: add water box with 1.0 nm padding
- Neutralize system with ions (Na+/Cl-)
- Validate structure before passing to simulation

COORDINATION:
- After download → ChimeraXAgent cleans structure
- Cleaned structure → ValidationManager checks completeness
- Validated structure → SimulationAgent can proceed

OUTPUT FORMAT:
- ✅ for success with file paths and structure info
- ⚠️ for warnings (missing residues, etc.)
- ❌ for errors"""
        
        return ConversableAgent(
            name="StructureCreator",
            llm_config=self.llm_config,
            human_input_mode="NEVER",
            code_execution_config=False,
            system_message=protein_structure_prompt
        )
    
    def create_forcefield_agent(self):
        """Create force field management agent."""
        from src.system_messages.forcefield_manager_system_message import FORCEFIELD_MANAGER_SYSTEM_PROMPT
        
        return ConversableAgent(
            name="ForceFieldManager",
            llm_config=self.llm_config,
            human_input_mode="NEVER",
            code_execution_config=False,
            system_message=FORCEFIELD_MANAGER_SYSTEM_PROMPT
        )
    
    def create_simulation_agent(self):
        """Create OpenMM simulation agent."""
        from src.system_messages.simulation_manager_system_message import SIMULATION_MANAGER_SYSTEM_PROMPT
        
        return ConversableAgent(
            name="SimulationManager",
            llm_config=self.llm_config,
            human_input_mode="NEVER",
            code_execution_config=False,
            system_message=SIMULATION_MANAGER_SYSTEM_PROMPT
        )
    
    def create_reviewer_agent(self):
        """Create simulation input reviewer agent."""
        reviewer_prompt = """You are the simulation input reviewer.

Your responsibilities:
1. Review simulation parameters before execution
2. Check force field and structure compatibility
3. Verify workflow gates are satisfied
4. Suggest improvements for simulation setup

REVIEW CHECKLIST:
- Structure validated and cleaned?
- Force field covers all atom types?
- Reasonable simulation parameters?
- Sufficient equilibration planned?
- Output files properly configured?

VALIDATION GATES:
- check_workflow_status() must return ✅ before simulation
- All required files must exist
- Force field must be validated

Provide constructive feedback with specific suggestions."""
        
        return ConversableAgent(
            name="SimulationReviewer",
            llm_config=self.llm_config,
            human_input_mode="NEVER",
            code_execution_config=False,
            system_message=reviewer_prompt
        )
    
    def create_slurm_agent(self):
        """Create SLURM HPC job submission agent."""
        from src.system_messages.slurm_manager_system_message import SLURM_MANAGER_SYSTEM_PROMPT
        
        return ConversableAgent(
            name="SLURMManager",
            llm_config=self.llm_config,
            human_input_mode="NEVER",
            code_execution_config=False,
            system_message=SLURM_MANAGER_SYSTEM_PROMPT
        )
    
    def create_analysis_agent(self):
        """Create results analysis agent."""
        from src.system_messages.results_analyser_system_message import RESULTS_ANALYZER_SYSTEM_PROMPT
        
        # Customize for protein analysis
        protein_analysis_prompt = """You are the results analysis specialist for protein MD simulations.

Your responsibilities:
1. Analyze simulation trajectories (RMSD, RMSF, contacts)
2. Parse and interpret simulation log files
3. Create visualizations and plots
4. Identify significant conformational changes
5. Report simulation quality metrics

ANALYSIS FUNCTIONS:
- analyze_trajectory(trajectory, topology) → RMSD, RMSF, Rg analysis
- parse_simulation_log(log_file) → energy, temperature trends
- list_files() → show available output files
- run_command(cmd) → execute analysis commands

KEY METRICS FOR PROTEINS:
- RMSD: Structural deviation from reference
- RMSF: Per-residue flexibility
- Rg: Radius of gyration (compactness)
- Secondary structure: Helix/sheet content over time
- Contacts: Native contact fraction

QUALITY INDICATORS:
- Equilibration: Energy/temperature stabilization
- Convergence: RMSD plateau
- Sampling: Conformational diversity

OUTPUT: Report findings with statistics and file locations."""
        
        return ConversableAgent(
            name="ResultsAnalyzer",
            llm_config=self.llm_config,
            human_input_mode="NEVER",
            code_execution_config=False,
            system_message=protein_analysis_prompt
        )
    
    def create_westpa_agent(self):
        """Create WESTPA weighted ensemble agent."""
        from src.system_messages.westpa_system_message import WESTPA_SYSTEM_PROMPT
        
        return ConversableAgent(
            name="WESTPAManager",
            llm_config=self.llm_config,
            human_input_mode="NEVER",
            code_execution_config=False,
            system_message=WESTPA_SYSTEM_PROMPT
        )
    
    def create_chimerax_agent(self):
        """Create ChimeraX visualization agent."""
        from src.system_messages.chimerax_system_message import CHIMERAX_SYSTEM_PROMPT
        
        return ConversableAgent(
            name="ChimeraXManager",
            llm_config=self.llm_config,
            human_input_mode="NEVER",
            code_execution_config=False,
            system_message=CHIMERAX_SYSTEM_PROMPT
        )
    
    def get_agent_list(self, agents_dict):
        """
        Get list of agents for group chat in correct order.
        
        Args:
            agents_dict: Dictionary of agents from create_all_agents()
            
        Returns:
            list: Ordered list of agents for group chat
        """
        return [
            agents_dict['admin'],
            agents_dict['structure'],
            agents_dict['forcefield'],
            agents_dict['simulation'],
            agents_dict['reviewer'],
            agents_dict['slurm'],
            agents_dict['analysis'],
            agents_dict['websurfer'],
            agents_dict['westpa'],
            agents_dict['chimerax'],
        ]
    
    @staticmethod
    def create_factory(llm_config, executor, workdir):
        """
        Static factory method to create AgentFactory instance.
        
        Args:
            llm_config: LLM configuration dictionary
            executor: Code executor instance  
            workdir: Working directory path
            
        Returns:
            AgentFactory: Configured factory instance
        """
        return AgentFactory(llm_config, executor, workdir)

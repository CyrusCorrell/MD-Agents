"""
Protein MD Simulation Multi-Agent System

A multi-agent AI framework for protein molecular dynamics simulations using AutoGen.
Natural language prompts trigger coordinated workflows across specialized agents that
download structures, prepare systems, run OpenMM simulations, and analyze results.

Migrated from LAMMPS-Agents materials science framework.
"""

import os
from dotenv import load_dotenv
load_dotenv()

import autogen
from autogen.coding import LocalCommandLineCodeExecutor
from autogen.agentchat.contrib.capabilities.teachability import Teachability
import nest_asyncio
import sys
import asyncio
import datetime
from typing import Any

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

nest_asyncio.apply()

from src.tools.llm_config import get_llm_config
from src.tools.validation_tools import ValidationManager
from src.tools.workflow_logger import WorkflowLogger


class AutoGenSystem:
    """Main orchestration system for protein MD simulations."""
    
    def __init__(self, llm_type: str, workdir: str):
        print("Starting Protein MD Agentic System initialization...")

        self.llm_type = llm_type
        self.llm_config = get_llm_config(llm_type)

        self.workdir = os.path.abspath(workdir)
        if not os.path.exists(self.workdir):
            os.makedirs(self.workdir, exist_ok=True)
            print(f"Created working directory: {self.workdir}")

        self.executor = LocalCommandLineCodeExecutor(
            timeout=1200,
            work_dir=self.workdir,
        )
        
        print("🔧 Setting up components...")
        self._setup_workflow_logger()
        self._setup_specialized_tools()    
        self._setup_validation_manager()   

        self._setup_agents()               
        self._setup_function_registry()    
        self._setup_group_chat()           
        self._setup_teachability()         
        self._instrument_managers()
        print("AutoGenSystem ready!")

    def _setup_workflow_logger(self):
        """Set up Pydantic-based observability logging."""
        try:
            self.workflow_logger = WorkflowLogger(self.workdir)
            self.workflow_logger.log_agent_call("System", "Initializing Protein MD system")
            print("  ✅ WorkflowLogger initialized")
        except Exception as e:
            print(f"  ⚠️ WorkflowLogger failed: {e}")
            self.workflow_logger = None

    def _setup_validation_manager(self):
        """Set up validation manager."""
        try:
            self.validation_manager = ValidationManager(self.workdir)
            self.validation_manager.forcefield_manager = self.forcefield_manager            
            self.validation_manager.structure_creator = self.structure_creator
            print("  ✅ ValidationManager initialized")
        except Exception as e:
            print(f"ValidationManager failed: {e}")
            raise

    def _setup_specialized_tools(self):
        """Initialize all specialized tool managers."""
        try:
            from src.tools.specialized_tools import (
                FileManager,
                StructureCreator,
                ForceFieldManager,
                OpenMMManager,
                SLURMManager,
                WESTPAManager,
                ChimeraXManager,
            )

            print("🔧 Setting up specialized tools...")

            # Initialize file management tools
            self.file_manager = FileManager(self.workdir)
            print("  ✅ FileManager initialized")

            # Initialize structure creator (PDB download/preparation)
            self.structure_creator = StructureCreator(self.workdir)
            print("  ✅ StructureCreator initialized")

            # Initialize OpenMM simulation manager
            self.openmm_manager = OpenMMManager(self.workdir)
            print("  ✅ OpenMMManager initialized")

            # Initialize force field manager
            self.forcefield_manager = ForceFieldManager(self.workdir, None)
            
            # Initialize force field manager attributes for workflow tracking
            if not hasattr(self.forcefield_manager, 'forcefield_validated'):
                self.forcefield_manager.forcefield_validated = False
            if not hasattr(self.forcefield_manager, 'last_forcefield_file'):
                self.forcefield_manager.last_forcefield_file = None
            print("  ✅ ForceFieldManager initialized")

            # Initialize SLURM manager for HPC
            self.slurm_manager = SLURMManager(self.workdir)
            print("  ✅ SLURMManager initialized")

            # Initialize WESTPA manager for rare event sampling
            self.westpa_manager = WESTPAManager(self.workdir)
            print("  ✅ WESTPAManager initialized")

            # Initialize ChimeraX manager for visualization
            self.chimerax_manager = ChimeraXManager(self.workdir)
            print("  ✅ ChimeraXManager initialized")

            print("✅ All specialized tools ready!")

        except Exception as e:
            print(f"Specialized tools failed: {e}")
            raise

    def _setup_agents(self):
        """Set up all agents using the factory."""
        try:
            from src.tools.agent_factory import AgentFactory

            print("Setting up agents...")

            # Create agent factory
            agent_factory = AgentFactory(self.llm_config, self.executor, self.workdir)

            # Create all agents
            self.agents = agent_factory.create_all_agents()

            # Extract individual agents for backward compatibility
            self.admin = self.agents['admin']
            self.structure_agent = self.agents['structure']
            self.forcefield_agent = self.agents['forcefield']
            self.simulation_agent = self.agents['simulation']
            self.reviewer_agent = self.agents['reviewer']
            self.slurm_agent = self.agents['slurm']
            self.analysis_agent = self.agents['analysis']
            self.websurfer = self.agents['websurfer']
            self.westpa_agent = self.agents['westpa']
            self.chimerax_agent = self.agents['chimerax']

            # Link websurfer to forcefield manager
            if hasattr(self, 'forcefield_manager') and self.websurfer:
                if hasattr(self.forcefield_manager, 'set_websurfer'):
                    self.forcefield_manager.set_websurfer(self.websurfer)
                else:
                    self.forcefield_manager.websurfer = self.websurfer

            print("✅ Agents initialized")

        except Exception as e:
            print(f"❌ Agents setup failed: {e}")
            raise

    def get_managers_dict(self):
        """Get dictionary of all managers for function registry."""
        return {
            'file_manager': self.file_manager,
            'structure_creator': self.structure_creator,
            'forcefield_manager': self.forcefield_manager,
            'openmm_manager': self.openmm_manager,
            'slurm_manager': self.slurm_manager,
            'westpa_manager': self.westpa_manager,
            'chimerax_manager': self.chimerax_manager,
            'validation_manager': self.validation_manager,
            'workflow_logger': self.workflow_logger,
        }

    def _setup_function_registry(self):
        """Set up function registry and register all functions."""
        try:
            from src.tools.function_registry import FunctionRegistry

            print("Setting up function registry...")

            managers_dict = self.get_managers_dict()

            self.function_registry = FunctionRegistry(self.agents, managers_dict, self.workdir)
            self.function_registry.register_all_functions()

            print("Function registry ready")

        except Exception as e:
            print(f"Function registry failed: {e}")
            raise

    def _setup_group_chat(self, previous_chat_file: str = None):
        """Set up group chat with all specialized agents."""
        try:
            print("Setting up group chat...")
            previous_messages = []
            if previous_chat_file:
                previous_messages = self._load_previous_messages(previous_chat_file)

            self.groupchat = autogen.GroupChat(
                agents=[
                    self.admin,
                    self.structure_agent,
                    self.forcefield_agent,
                    self.simulation_agent,
                    self.reviewer_agent,
                    self.slurm_agent,
                    self.analysis_agent,  
                    self.websurfer,
                    self.westpa_agent,
                    self.chimerax_agent,
                ],
                messages=previous_messages,
                max_round=800,
                select_speaker_auto_llm_config=self.llm_config,
                speaker_selection_method="auto",
            )

            from src.system_messages.manager_system_message import MANAGER_SYSTEM_PROMPT
            
            self.manager = autogen.GroupChatManager(
                groupchat=self.groupchat,
                llm_config=self.llm_config,
                system_message=MANAGER_SYSTEM_PROMPT,
            )

            print(f"  ✅ Group chat configured with {len(self.groupchat.agents)} agents")

        except Exception as e:
            print(f"Group chat failed: {e}")
            raise

    def _setup_teachability(self):
        """Set up teachability for the agents."""
        try:
            print("Setting up teachability...")

            self.teachability = Teachability(
                verbosity=0,
                reset_db=False,
                path_to_db_dir=os.path.abspath(os.path.join(
                    os.path.dirname(__file__), 
                    f"teachability_db_protein_{self.llm_type}"
                )),
                recall_threshold=6,
                llm_config=self.llm_config
            )
            
            for agent in [self.simulation_agent, self.admin, self.manager]:
                self.teachability.add_to_agent(agent)

            print("  ✅ Teachability ready")

        except Exception as e:
            print(f"Teachability failed: {e}")
            print("Continuing without teachability...")

    def _instrument_managers(self):
        """Inject workflow logger into all managers for observability."""
        if not self.workflow_logger:
            return
            
        managers = [
            self.file_manager,
            self.structure_creator,
            self.forcefield_manager,
            self.openmm_manager,
            self.slurm_manager,
            self.westpa_manager,
            self.chimerax_manager,
        ]
        
        for manager in managers:
            if hasattr(manager, 'workflow_logger'):
                manager.workflow_logger = self.workflow_logger
            else:
                setattr(manager, 'workflow_logger', self.workflow_logger)

    def initiate_chat(self, prompt: str) -> Any:
        """Start a chat session with the given prompt."""
        try:
            if self.workflow_logger:
                self.workflow_logger.log_agent_call("User", f"Starting chat: {prompt[:100]}...")
            
            result = self.admin.initiate_chat(
                self.manager,
                message=prompt,
            )

            self._save_chat_result(prompt, result)
            
            return result
            
        except Exception as e:
            print(f"Chat failed: {str(e)}")
            if self.workflow_logger:
                self.workflow_logger.log_agent_call("System", f"Chat failed: {str(e)}")
            raise

    def _load_previous_messages(self, chat_file_path: str) -> list:
        """Load and parse previous chat messages from saved file."""
        try:
            if not os.path.exists(chat_file_path):
                print(f"Chat file not found: {chat_file_path}")
                return []
            
            with open(chat_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            messages = []
            
            import re
            
            agent_patterns = [
                r"admin \(to chat_manager\):",
                r"structure_agent:",
                r"forcefield_agent:",
                r"simulation_agent:",
                r"reviewer_agent:",
                r"slurm_agent:",
                r"analysis_agent:",
                r"websurfer:",
                r"westpa_agent:",
                r"chimerax_agent:",
                r"chat_manager:"
            ]
            
            lines = content.split('\n')
            current_speaker = None
            current_message = []
            
            for line in lines:
                speaker_found = False
                for pattern in agent_patterns:
                    if re.match(pattern, line):
                        if current_speaker and current_message:
                            messages.append({
                                "content": '\n'.join(current_message).strip(),
                                "name": current_speaker
                            })
                        
                        current_speaker = pattern.replace(":", "").replace(" (to chat_manager)", "")
                        current_message = []
                        speaker_found = True
                        break
                
                if not speaker_found and current_speaker:
                    current_message.append(line)
            
            if current_speaker and current_message:
                messages.append({
                    "content": '\n'.join(current_message).strip(),
                    "name": current_speaker
                })
            
            print(f"✅ Loaded {len(messages)} previous messages")
            return messages
            
        except Exception as e:
            print(f"❌ Failed to load previous messages: {e}")
            return []

    def _save_chat_result(self, prompt: str, result):
        """Save chat result to text file."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        results_dir = "results"
        if not os.path.exists(results_dir):
            os.makedirs(results_dir, exist_ok=True)
        
        result_file = f"results/chat_result_{timestamp}.txt"
        
        try:
            with open(result_file, 'w', encoding='utf-8') as f:
                f.write("="*80 + "\n")
                f.write(f"PROTEIN MD AGENT CONVERSATION RESULT\n")
                f.write(f"Timestamp: {datetime.datetime.now()}\n")
                f.write(f"Prompt: {prompt}\n")
                f.write("="*80 + "\n\n")
                
                f.write(str(result))
                
                f.write(f"\n\n" + "="*80 + "\n")
                f.write(f"End of conversation - {datetime.datetime.now()}\n")
                f.write("="*80 + "\n")
            
            print(f"💾 Chat result saved: {result_file}")
            
            if self.workflow_logger:
                self.workflow_logger.log_agent_call("System", f"Chat saved to {result_file}")
            
        except Exception as e:
            print(f"Failed to save chat result: {e}")


if __name__ == "__main__":
    try:
        base_workdir = "protein_md_runs"
        llm_type = "gpt4o"
        
        # Example prompts for protein MD simulations
        prompt_equilibration = """Download the structure for lysozyme (PDB ID: 1LYZ), 
        clean it with ChimeraX, solvate with TIP3P water, 
        and run a 10 ns NPT equilibration using AMBER ff14SB force field."""
        
        prompt_folding = """Set up a WESTPA weighted ensemble simulation to study 
        the folding pathway of the Trp-cage miniprotein (PDB: 1L2Y)."""
        
        prompt_simple = """Download PDB structure 1LYZ and prepare it for simulation."""
        
        n_runs = 1

        print(f"Initializing Protein MD System for {n_runs} run(s)...")

        results_summary = []

        for i in range(1, n_runs + 1):
            print("\n" + "="*80)
            print(f"🔁 Starting Run {i}/{n_runs}")
            print("="*80)

            run_workdir = os.path.join(base_workdir, f"run_{i:02d}")
            os.makedirs(run_workdir, exist_ok=True)

            try:
                autogen_system = AutoGenSystem(
                    llm_type=llm_type,
                    workdir=run_workdir,
                )

                import time
                time.sleep(1)

                chat_result = autogen_system.initiate_chat(prompt_simple)

                results_summary.append({"run": i, "status": "success", "workdir": run_workdir})
                print(f"✅ Run {i} completed successfully!\n")

            except Exception as e:
                results_summary.append({"run": i, "status": f"failed: {e}", "workdir": run_workdir})
                print(f"❌ Run {i} failed: {e}\n")

        # Save summary file
        summary_file = os.path.join(base_workdir, "evaluation_summary.txt")
        with open(summary_file, "w", encoding="utf-8") as f:
            f.write("Protein MD Simulation Summary\n")
            f.write("="*60 + "\n")
            for r in results_summary:
                f.write(f"Run {r['run']:02d}: {r['status']} (dir: {r['workdir']})\n")

        print(f"📄 Summary saved to: {summary_file}")

        success_count = sum(1 for r in results_summary if r["status"] == "success")
        print(f"\n✅ Successful runs: {success_count}/{n_runs}")
        print("Evaluation complete.")

    except Exception as e:
        print(f"System failed during evaluation: {e}")
        import traceback
        traceback.print_exc()

# LAMMPS-Agents Codebase Guide

## Project Architecture

This is a **multi-agent AI framework** for atomistic simulations using AutoGen. Natural language prompts trigger coordinated workflows across specialized agents that create structures, download potentials, generate LAMMPS inputs, run simulations, and analyze results.

### Core Components

- **`lammps_agents.py`**: Main orchestration. Creates `AutoGenSystem` which initializes agents, managers, function registry, and group chat
- **`src/tools/agent_factory.py`**: Creates 10+ specialized agents (StructureCreator, PotentialManager, LAMMPSInputCreator, HPCManager, WebSurfer, PhonopyCalculator, etc.)
- **`src/tools/function_registry.py`**: Registers ~100+ functions to agents via `@register_function` decorators. Maps agent capabilities to manager methods
- **`src/tools/specialized_tools/`**: Manager classes that implement actual functionality (FileManager, StructureCreator, PotentialManager, HPCManager, PhonopyManager, etc.)
- **`src/system_messages/`**: Detailed prompts guiding each agent's behavior and decision-making

### Critical Workflow Pattern

**VALIDATION GATES** enforce workflow correctness:

1. **StructureCreator** → creates `.lmp` files via `atomsk`
2. **PotentialManager** → downloads/validates EAM/MEAM potentials (must pass `check_workflow_status()`)
3. **VALIDATION GATE** → `ValidationManager.check_workflow_status()` MUST return "✅" before proceeding
4. **LAMMPSInputCreator** → generates LAMMPS input scripts only after validation passes
5. **HPCManager/LocalRunManager** → executes simulations
6. **ResultsAnalyzer** → parses outputs, creates plots

**Never skip validation gates.** Agents check `potential_validated` and `structure_validated` flags before proceeding.

## Agent-Function Registration

Functions connect to agents via `FunctionRegistry`:

```python
# In function_registry.py
register_function(
    create_crystal_structure,         # Python function
    caller=self.structure_agent,      # Agent that calls it
    executor=self.lammps_admin,       # Agent that executes it
    name="create_structure",          # Function name for LLM
    description="Create crystal..."   # What LLM sees
)
```

**To add new capabilities**: Register functions in `FunctionRegistry.register_*_functions()` methods, not in agent creation.

## Environment Setup

**Config loading hierarchy**:
1. `.env` file (copy from `.env_example`)
2. `config.settings` module (if exists)
3. `os.getenv()` fallback

**Required API keys**: `OPENAI_API_KEY`, `anthropic_api_key` (optional)

**LLM selection**: Edit `llm_type` in `lammps_agents.py` main block:
- `"gpt4o"` - GPT-4o (default)
- `"gpt-4.1"` - GPT-4 Turbo
- `"o3-mini"` - OpenAI o3-mini
- `"claude_35"` - Claude 3.5 Sonnet

Use `get_llm_config(llm_type)` in [src/tools/llm_config.py](src/tools/llm_config.py) to configure models.

## External Dependencies

**Required software** (not Python packages):
- **Atomsk**: Creates crystal structures. All structure creation calls `atomsk --create` subprocess commands
- **LAMMPS**: Molecular dynamics engine. Called via `subprocess` or SSH to HPC systems
- **Phonopy**: Lattice dynamics calculations (phonon dispersion, DOS)

**Docker alternative**: [Dockerfile](Dockerfile) bundles LAMMPS + Atomsk + Python deps for containerized execution

## Running Simulations

**Local execution** (default in codebase):
```python
# HPCManager is aliased to LocalRunManager in _setup_specialized_tools()
self.hpc_manager = self.local_run_manager
```

**HPC execution**: Modify [src/tools/specialized_tools/hpc_manager.py](src/tools/specialized_tools/hpc_manager.py) with SSH/SLURM commands for remote clusters

**Typical workflow**:
```bash
python lammps_agents.py  # Edit prompt in __main__ block
```

Results saved to `lammps_run_test/run_XX/` subdirectories.

## Teachability System

Uses AutoGen's `Teachability` capability with ChromaDB to learn from human corrections:

```python
# In _setup_teachability()
self.teachability = Teachability(
    path_to_db_dir="teachability_db_gpt4o/",
    recall_threshold=6,
)
```

Stores user feedback/corrections in `teachability_db_*/` for future reference. Agents query past interactions before acting.

## Property Calculation Specializations

- **Elastic constants**: Use `lammps_elastic_agent` with files in `src/tools/default_files/` (displace.mod, in.elastic)
- **Phonon dispersion**: PhonopyCalculator requires relaxed structure + validated potential → generates force constants → band structure plots
- **Melting point**: MeltingPointsManager creates solid-liquid interface → monitors phase transition via dump files

Always **relax structures first** before property calculations (per manager system message rules).

## Common Patterns

**Manager state tracking**: Managers use flags like `potential_validated`, `last_potential_file` to track workflow state. Check these in validation methods.

**File operations**: All managers work relative to `self.workdir` passed during initialization. Use `os.path.join(self.workdir, filename)` for paths.

**Error handling**: Managers return detailed status strings (e.g., "✅ Structure created: 1000 atoms") that agents parse to decide next actions.

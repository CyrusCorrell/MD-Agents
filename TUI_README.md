# Protein MD Simulation TUI

An interactive Terminal User Interface (TUI) for the multi-agent protein molecular dynamics simulation framework.

![TUI Demo](https://img.shields.io/badge/Interface-Terminal%20UI-blue)
![Python](https://img.shields.io/badge/Python-3.11+-green)

## Features

### 📊 Real-Time Monitoring
- **Workflow Status**: Track progress through structure → forcefield → validation → simulation → analysis
- **Agent Activity**: Monitor which agents are active and what they're doing
- **Console Output**: Live logging of all system messages and events

### ⚙️ Interactive Configuration
- **Simulation Type**: Standard MD, WESTPA weighted ensemble, or free energy calculations
- **Structure Source**: Download from RCSB PDB, AlphaFold, or use local files
- **Force Field Selection**: AMBER14, AMBER19, CHARMM36, OpenFF
- **Execution Options**: Local or HPC/SLURM, with solvation and visualization controls

### 📈 Results Visualization
- **Summary Tab**: Overview of simulation outcomes
- **Files Tab**: Browse generated files (structures, trajectories, logs)
- **Metrics Tab**: Key simulation metrics and statistics
- **Visualization Tab**: Links to generated plots and movies

## Installation

```bash
# Install the TUI package
pip install textual

# Or install all requirements
pip install -r requirements.txt
```

## Quick Start

### Launch the TUI

```bash
python protein_tui.py
```

### Basic Workflow

1. **Select Simulation Type** (radio buttons in Setup panel)
   - Standard MD: Equilibration and production runs
   - WESTPA: Rare event sampling (protein folding, binding)
   - Free Energy: Alchemical transformations

2. **Choose Structure Source**
   - RCSB PDB ID: Enter 4-letter code (e.g., `1UBQ` for ubiquitin)
   - AlphaFold: Enter UniProt ID for predicted structures
   - Local File: Path to existing PDB file

3. **Configure Force Field**
   - Default: `amber14-all` (recommended for proteins)
   - CHARMM36: Alternative for lipid/membrane systems
   - OpenFF: Small molecules and ligands

4. **Set Simulation Parameters**
   - Steps: Number of MD steps (default: 1,000,000)
   - Temperature: Simulation temperature in Kelvin (default: 300K)
   - Solvate: Add water box (recommended)
   - HPC: Submit to SLURM cluster

5. **Start Simulation**
   - Press `Start Simulation` button or keyboard shortcut `s`
   - Monitor progress in Workflow Status panel
   - View agent coordination in Agent Activity panel

### Keyboard Shortcuts

- `s`: Start simulation
- `v`: Validate configuration
- `c`: Clear console
- `q`: Quit application

## Interface Layout

```
┌─────────────────────────────────────────────────────────┐
│ Protein MD Simulation - Multi-Agent Framework           │
├──────────────────┬──────────────────┬───────────────────┤
│  Workflow Status │  Agent Activity  │  Simulation Setup │
│  ⚪ Structure    │  [12:34:56]      │  ⚙️ Configuration │
│  ⚪ Force Field  │  Manager: Init   │  • Sim Type       │
│  ⚪ Validation   │  StructureAgent  │  • PDB Input      │
│  ⚪ Simulation   │  ...             │  • Force Field    │
│  ⚪ Analysis     │                  │  • Parameters     │
│                  │                  │  [Start] [Valid]  │
├──────────────────┴──────────────────┤                   │
│  Console Output                     │                   │
│  [12:34:56] ℹ️ System initialized   │                   │
│  [12:34:57] ✅ OpenMM found         │                   │
│  ...                                │                   │
├─────────────────────────────────────┴───────────────────┤
│  Results & Analysis                                     │
│  [Summary] [Files] [Metrics] [Visualization]            │
│  • Trajectory: trajectory.dcd (125 MB)                  │
│  • RMSD plot: rmsd.png                                  │
└─────────────────────────────────────────────────────────┘
 s Start | v Validate | c Clear | q Quit
```

## Integration with AutoGen System

The TUI seamlessly integrates with the existing multi-agent framework:

### Workflow Orchestration

```python
# TUI builds natural language prompts from UI inputs
prompt = "Perform a molecular dynamics simulation of protein 1UBQ using OpenMM..."

# Passes to AutoGen system
autogen_system = AutoGenSystem(llm_type="gpt4o", workdir=run_dir)
result = autogen_system.initiate_chat(prompt)
```

### Agent Monitoring

The TUI hooks into the `WorkflowLogger` for real-time updates:

```python
# Agent activity is logged and displayed
self.add_agent_activity("StructureCreator", "Downloading PDB 1UBQ")
self.add_agent_activity("ChimeraXAgent", "Cleaning structure")
self.add_agent_activity("ForceFieldManager", "Validating AMBER14")
```

### Status Tracking

Workflow gates update the status panel:

```python
self.update_workflow_status("structure", "✅ Structure downloaded")
self.update_workflow_status("forcefield", "🔄 Validating...")
self.update_workflow_status("validation", "✅ Validation passed")
```

## Example Usage Scenarios

### 1. Standard Protein MD Simulation

**Goal**: Equilibrate and run 10ns MD on ubiquitin

**Steps**:
1. Structure Source: RCSB PDB ID → `1UBQ`
2. Force Field: `amber14-all`
3. Steps: `10000000` (10M steps ≈ 10ns with 1fs timestep)
4. Temperature: `300`K
5. Enable solvation
6. Start simulation

**Expected Agents**:
- StructureCreator → downloads PDB
- ChimeraXAgent → cleans structure, adds hydrogens
- ForceFieldManager → validates AMBER14
- ValidationManager → checks workflow gates
- OpenMMManager → runs equilibration + production
- ResultsAnalyzer → calculates RMSD, RMSF, generates plots

### 2. WESTPA Rare Event Sampling

**Goal**: Sample protein folding pathways

**Steps**:
1. Simulation Type: Weighted Ensemble (WESTPA)
2. Structure Source: AlphaFold UniProt ID → `P0CG48` (unfolded)
3. Force Field: `amber14-all`
4. Enable HPC (WESTPA requires many walkers)
5. Start simulation

**Expected Agents**:
- StructureCreator → downloads AlphaFold prediction
- WESTPAAgent → initializes weighted ensemble
- SLURMManager → submits HPC job with 48 walkers
- WESTPAAgent → analyzes pathways after completion

### 3. Free Energy Calculation

**Goal**: Compute binding free energy of ligand to protein

**Steps**:
1. Simulation Type: Free Energy Calculation
2. Structure: Protein-ligand complex PDB
3. Force Field: `openff-2.0.0` (for ligand) + `amber14-all` (protein)
4. Configure alchemical transformation
5. Submit to HPC

## Observability Features

The TUI provides full transparency into the agentic workflow:

### Console Logging

All events are timestamped and categorized:

```
[12:34:56] ℹ️ System initialized
[12:34:57] ✅ OpenMM found
[12:35:00] 🔄 Downloading PDB 1UBQ...
[12:35:03] ✅ Structure downloaded: 1231 atoms
[12:35:05] 🔄 ChimeraX cleaning structure...
[12:35:08] ✅ Structure cleaned: cleaned.pdb
[12:35:10] ⚠️ Force field missing TIP3P-FB parameters
[12:35:12] ✅ Force field validated (with warnings)
```

### Agent Activity Timeline

Track which agents are active at each workflow stage:

```
[12:35:00] StructureCreator: Downloading PDB 1UBQ
[12:35:05] ChimeraXAgent: Cleaning structure
[12:35:10] ForceFieldManager: Validating AMBER14
[12:35:15] ValidationManager: Running validation gates
[12:35:20] OpenMMManager: Initializing simulation
[12:35:25] OpenMMManager: Running equilibration (NVT)
[12:36:00] OpenMMManager: Running production (NPT)
```

### Workflow Status Gates

Visual indication of validation gates:

- ⚪ Not Started
- 🔄 In Progress
- ✅ Completed Successfully
- ⚠️ Completed with Warnings
- ❌ Failed

## Advanced Features

### Custom Prompts

For power users, you can directly edit the generated prompt:

```python
# In get_simulation_config(), add custom prompt field
config["custom_prompt"] = "Advanced simulation with umbrella sampling..."
```

### Batch Simulations

Run multiple simulations sequentially:

```python
# Modify start_simulation() to loop over PDB IDs
pdb_ids = ["1UBQ", "1L2Y", "2MHC"]
for pdb_id in pdb_ids:
    config["pdb_id"] = pdb_id
    await self.run_simulation(config)
```

### HPC Integration

When HPC checkbox is enabled:

1. TUI uploads files to HPC cluster via SSH
2. Generates SLURM submission script
3. Monitors job queue status
4. Downloads results when complete

Status updates show SLURM job state:

```
[12:40:00] 📤 Uploading files to HPC
[12:40:15] ✅ SLURM job submitted: 1234567
[12:40:20] ⏳ Job queued (position 5)
[12:45:00] ▶️ Job running (12 nodes, 48 GPUs)
[14:30:00] ✅ Job completed
[14:30:05] 📥 Downloading results...
```

## Troubleshooting

### TUI Won't Start

**Error**: `ModuleNotFoundError: No module named 'textual'`

**Solution**:
```bash
pip install textual
```

### AutoGenSystem Not Found

**Warning**: `AutoGenSystem not loaded - demo mode`

**Solution**: Ensure `lammps_agents.py` is in the same directory or Python path:
```bash
export PYTHONPATH=$PYTHONPATH:/path/to/protein-md-agents
```

### OpenMM Not Detected

**Error**: `❌ OpenMM not found`

**Solution**:
```bash
conda install -c conda-forge openmm
# or
pip install openmm
```

### ChimeraX Command Failed

**Error**: `ChimeraX executable not found`

**Solution**: Install ChimeraX and add to PATH:
```bash
# Linux/Mac
export PATH=$PATH:/path/to/chimerax/bin

# Windows
set PATH=%PATH%;C:\Program Files\ChimeraX\bin
```

## Development Mode

For development/testing without the full AutoGen system:

```python
# Run in demo mode (simulates workflow)
python protein_tui.py

# TUI will detect missing AutoGenSystem and run simulations
# with mock progress updates
```

## Configuration Files

The TUI respects the same configuration as the main system:

- `.env`: API keys (OpenAI, Anthropic)
- `config.settings`: Default parameters
- Working directory: `protein_md_runs/` (configurable)

## Future Enhancements

- [ ] **Live Trajectory Viewer**: Real-time 3D visualization of running simulations
- [ ] **Graph View**: Network diagram of agent interactions
- [ ] **Resource Monitor**: CPU/GPU usage, memory, disk I/O
- [ ] **Teachability Interface**: Review and edit learned knowledge
- [ ] **Workflow Templates**: Save/load common simulation workflows
- [ ] **Multi-Simulation Dashboard**: Manage multiple concurrent runs
- [ ] **Remote Monitoring**: Web interface for HPC job monitoring

## Contributing

Contributions welcome! Key areas:

1. **Visualization**: Integrate MDTraj/NGLview for trajectory display
2. **Analysis**: Add interactive plotting (e.g., using Plotext for terminal plots)
3. **Templates**: Pre-built workflows for common tasks
4. **Testing**: Unit tests for TUI components

## License

Same license as parent project (see main README).

## Support

For issues:
1. Check console output for error messages
2. Verify dependencies are installed
3. Ensure `.env` file contains valid API keys
4. Open issue on GitHub with TUI logs

## Credits

Built with [Textual](https://textual.textualize.io/) - modern TUI framework for Python.

# Protein MD Agents - Quick Start Guide

Get started with the multi-agent protein molecular dynamics simulation framework in 5 minutes.

## Prerequisites

### Required Software

1. **Python 3.9+**
   ```bash
   python --version
   ```

2. **OpenMM** (molecular dynamics engine)
   ```bash
   # Install via conda (recommended)
   conda install -c conda-forge openmm
   
   # Or via pip (limited GPU support)
   pip install openmm
   ```

3. **Optional: ChimeraX** (for visualization)
   - Download from: https://www.cgl.ucsf.edu/chimerax/
   - Install and note the installation path

4. **Optional: WESTPA** (for rare event sampling)
   ```bash
   conda install -c conda-forge westpa
   ```

### API Keys

You'll need at least one LLM API key:

- **OpenAI**: Get from https://platform.openai.com/api-keys
- **Anthropic Claude** (optional): Get from https://console.anthropic.com/

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/ANL-NST/LAMMPS-Agents.git
cd LAMMPS-Agents
```

### 2. Install Dependencies

```bash
# Install protein MD requirements
pip install -r requirements_protein.txt

# Install browser automation (for WebSurfer agent)
playwright install
```

### 3. Configure Environment

Create a `.env` file in the project root:

```bash
cp .env_example .env
```

Edit `.env` with your API keys:

```env
# Required: OpenAI API key
OPENAI_API_KEY=sk-your-key-here

# Optional: Anthropic API key (for Claude models)
anthropic_api_key=your-key-here

# Optional: HPC configuration
HPC_HOSTNAME=your-cluster.edu
HPC_USERNAME=your-username
HPC_KEY_PATH=/path/to/ssh/key
```

## Running the System

### Basic Usage

The main entry point is `protein_agents.py`:

```bash
python protein_agents.py
```

### Example 1: Simple Protein Structure Analysis

Edit the prompt in `protein_agents.py` (line ~470):

```python
if __name__ == "__main__":
    # Initialize the system
    system = AutoGenSystem(llm_type="gpt4o")
    
    # Example 1: Download and analyze ubiquitin
    initial_message = """
    Download the structure of ubiquitin (PDB ID: 1UBQ) and analyze it.
    Validate the structure and recommend an appropriate force field.
    """
    
    system.run_workflow(initial_message)
```

Run it:
```bash
python protein_agents.py
```

**Expected Output:**
- Downloads `1UBQ.pdb` to `lammps_run_test/`
- Structure validation report (atom count, residue count, chains)
- Force field recommendations
- Validation summary

### Example 2: Equilibration Simulation

```python
initial_message = """
1. Download ubiquitin (PDB ID: 1UBQ)
2. Validate the structure and force field coverage
3. Create a solvated system with AMBER14 force field
4. Run energy minimization
5. Run a short equilibration (50,000 steps NVT + 100,000 steps NPT)
"""

system.run_workflow(initial_message)
```

**Expected Output:**
- Prepared system: `ubiquitin_solvated.pdb`
- Minimized structure: `minimized.pdb`
- Equilibration trajectory: `equilibration.dcd`
- Log files with energy data
- Checkpoint files for continuation

### Example 3: Production Run with SLURM

```python
initial_message = """
1. Download 1UBQ and prepare for simulation
2. Generate an OpenMM production script for 10 ns at 300K
3. Submit the job to the HPC cluster (GPU partition, 24 hours)
4. Monitor job status
"""

system.run_workflow(initial_message)
```

**Prerequisites:**
- HPC credentials in `.env`
- SSH key configured
- SLURM cluster with GPU partition

### Example 4: WESTPA Folding Study

```python
initial_message = """
Set up a WESTPA protein folding study:
1. Use PDB 1UBQ as the folded state
2. Create an unfolded initial state
3. Initialize a WESTPA project with RMSD progress coordinate
4. Configure 48 walkers with 10 ps tau
5. Generate the necessary WESTPA configuration files
"""

system.run_workflow(initial_message)
```

**Output:**
- WESTPA project directory: `westpa_folding/`
- Configuration files: `west.cfg`, `bstates/`, `tstates/`
- Progress coordinate scripts

## Available LLM Models

Choose your model by setting `llm_type` in `protein_agents.py`:

```python
# Cloud API Models:
system = AutoGenSystem(llm_type="gpt4o")         # GPT-4o (default, recommended)
system = AutoGenSystem(llm_type="gpt-4.1")       # GPT-4 Turbo
system = AutoGenSystem(llm_type="o3-mini")       # OpenAI o3-mini
system = AutoGenSystem(llm_type="claude_35")     # Claude 3.5 Sonnet

# Local Ollama Models (no cloud API required):
system = AutoGenSystem(llm_type="ollama_small")  # 7B-8B models (fast)
system = AutoGenSystem(llm_type="ollama_medium") # 13B-20B models (balanced)
system = AutoGenSystem(llm_type="ollama_large")  # 70B+ models (best reasoning)
```

## Local Inference with Ollama

Run the multi-agent system entirely locally without cloud API dependencies using [Ollama](https://ollama.com/).

### Installing Ollama

**Linux/WSL:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**macOS:**
```bash
brew install ollama
```

**Windows:**
Download from https://ollama.com/download

### Pulling Models

Pull models before first use:

```bash
# Small models (7B-8B) - ~4GB, fast responses
ollama pull llama3.1:8b
ollama pull mistral:7b
ollama pull qwen2.5:7b

# Medium models (13B-20B) - ~8-15GB, balanced
ollama pull llama3.1:latest
ollama pull mixtral:8x7b

# Large models (70B+) - ~40GB+, best reasoning
ollama pull llama3.1:70b
```

### Starting Ollama Server

```bash
# Start the Ollama server (runs on http://localhost:11434)
ollama serve
```

### Using Ollama with Protein Agents

```python
from protein_agents import AutoGenSystem

# Use medium-sized local model
system = AutoGenSystem(llm_type="ollama_medium")

initial_message = """
Download ubiquitin (PDB ID: 1UBQ) and analyze its structure.
"""

system.run_workflow(initial_message)
```

### Custom Model Configuration

Configure specific models in your `.env` file:

```env
# Use custom Ollama models per size tier
OLLAMA_MODEL_SMALL=mistral:7b
OLLAMA_MODEL_MEDIUM=mixtral:8x7b
OLLAMA_MODEL_LARGE=llama3.1:70b

# Custom Ollama server URL (for remote deployments)
OLLAMA_BASE_URL=http://192.168.1.100:11434/v1
```

### Performance Considerations

| Model Size | VRAM Required | Tokens/sec* | Best For |
|------------|---------------|-------------|----------|
| 7B-8B      | 6-8 GB        | 30-50       | Fast tasks, structure creation |
| 13B-20B    | 10-16 GB      | 15-30       | Coordination, general reasoning |
| 70B+       | 40+ GB        | 5-15        | Complex planning, code generation |

*Approximate values, varies by hardware

For detailed model selection and troubleshooting, see [docs/ollama-guide.md](docs/ollama-guide.md).

## Agent Capabilities

The system includes 10 specialized agents:

| Agent | Capabilities |
|-------|-------------|
| **StructureCreator** | Download PDB/AlphaFold structures, validate, extract chains |
| **ForceFieldManager** | Validate OpenMM force fields, check residue coverage |
| **SimulationManager** | Run minimization, equilibration, production MD |
| **SimulationReviewer** | Validate workflow prerequisites, check simulation inputs |
| **SLURMManager** | Submit/monitor jobs on HPC clusters via SSH |
| **ResultsAnalyzer** | Analyze trajectories, calculate RMSD/RMSF, plot energy |
| **WESTPAManager** | Set up weighted ensemble simulations for rare events |
| **ChimeraXAgent** | Clean structures, create visualizations, calculate RMSD |
| **LAMMPSAdmin** | Coordinator agent (manages workflow) |
| **WebSurfer** | Search for PDB IDs, force field parameters online |

## Understanding Workflow Validation Gates

The system enforces **validation gates** before proceeding:

```
1. Structure Download → Validation Gate (check PDB format, atom counts)
                             ↓ ✅ Pass
2. Force Field Selection → Validation Gate (check residue coverage)
                             ↓ ✅ Pass
3. System Preparation → Ready for Simulation
```

Agents automatically check `check_workflow_status()` before critical operations.

## Output Structure

All outputs are saved in timestamped directories:

```
lammps_run_test/
├── run_01/
│   ├── 1UBQ.pdb                    # Downloaded structure
│   ├── 1UBQ_solvated.pdb          # Prepared system
│   ├── minimized.pdb               # Energy minimized
│   ├── equilibration.dcd           # Trajectory
│   ├── production.dcd              # Production trajectory
│   ├── simulation.log              # OpenMM log
│   ├── checkpoint.chk              # Restart file
│   └── analysis/
│       ├── rmsd_plot.png
│       └── energy_plot.png
├── run_02/
...
```

## Teachability System

The agents learn from your corrections:

```python
# During a run, if an agent makes a mistake, correct it:
"Actually, use CHARMM36 force field instead of AMBER14"

# The correction is stored in teachability_db_gpt4o/
# Future runs will remember this preference
```

Database location: `teachability_db_gpt4o/` (for GPT-4o model)

## Troubleshooting

### Issue: "OpenMM not found"

**Solution:** Install via conda:
```bash
conda install -c conda-forge openmm
```

### Issue: "Structure validation failed"

**Cause:** PDB has missing atoms or non-standard residues

**Solution:** Use ChimeraX to clean:
```python
initial_message = """
Download PDB 1ABC and use ChimeraX to:
1. Remove water and ligands
2. Add missing hydrogens at pH 7.0
3. Save cleaned structure
Then validate and proceed with simulation setup
"""
```

### Issue: "Force field coverage validation failed"

**Cause:** Non-standard residues (e.g., modified amino acids, ligands)

**Solution:** 
1. Remove non-standard residues before simulation
2. Or provide custom force field parameters
3. Or use a more comprehensive force field (e.g., CHARMM36)

### Issue: "SSH connection failed" (SLURM)

**Cause:** HPC credentials not configured

**Solution:** Check `.env` file:
```env
HPC_HOSTNAME=login.cluster.edu
HPC_USERNAME=your-username
HPC_KEY_PATH=/home/user/.ssh/id_rsa
```

Test SSH manually:
```bash
ssh -i ~/.ssh/id_rsa username@login.cluster.edu
```

## Advanced: Custom Simulations

### Running Custom OpenMM Scripts

The system can generate standalone scripts:

```python
initial_message = """
Generate an OpenMM simulation script with:
- AMBER99SB-ILDN force field
- TIP3P water model
- 300K temperature, NPT ensemble
- 2 fs timestep
- 100 ns production run
Save as 'custom_simulation.py'
"""
```

Then run locally:
```bash
python lammps_run_test/run_01/custom_simulation.py
```

### Integrating Custom Analysis

Add custom analysis by extending ResultsAnalyzer:

```python
# In your prompt:
initial_message = """
After simulation completes:
1. Calculate RMSD vs time
2. Calculate radius of gyration
3. Compute secondary structure content using MDTraj
4. Create plots for all metrics
"""
```

## Next Steps

1. **Explore Example Workflows**: See `examples/` directory (coming soon)
2. **Customize Agents**: Modify system messages in `src/system_messages/`
3. **Add New Tools**: Extend managers in `src/tools/specialized_tools/`
4. **GPU Acceleration**: Configure OpenMM with CUDA for faster simulations
5. **Advanced Sampling**: Explore WESTPA for protein folding/binding studies

## Resources

- **OpenMM Documentation**: http://docs.openmm.org/
- **MDTraj**: https://www.mdtraj.org/
- **WESTPA**: https://westpa.github.io/westpa/
- **ChimeraX**: https://www.cgl.ucsf.edu/chimerax/docs/user/index.html
- **AutoGen**: https://microsoft.github.io/autogen/

## Getting Help

- **Issues**: https://github.com/ANL-NST/LAMMPS-Agents/issues
- **Discussions**: https://github.com/ANL-NST/LAMMPS-Agents/discussions

## License

This project is licensed under the MIT License - see LICENSE file for details.

---

**Ready to simulate!** 🧬🔬

Try the first example to download and analyze ubiquitin:
```bash
python protein_agents.py
```

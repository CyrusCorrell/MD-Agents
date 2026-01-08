# Quick Start Guide - Protein MD TUI

## Installation (3 minutes)

### Step 1: Install Textual
```bash
pip install textual
```

### Step 2: Launch TUI
```bash
# Windows
launch_tui.bat

# Linux/Mac
chmod +x launch_tui.sh
./launch_tui.sh

# Direct Python
python protein_tui.py
```

## First Simulation (5 minutes)

### Example: Ubiquitin Equilibration

1. **Launch TUI**: Run `python protein_tui.py`

2. **Configure Simulation**:
   - Simulation Type: ☑ **Standard MD**
   - Structure Source: ☑ **RCSB PDB ID**
   - PDB Input: `1UBQ`
   - Force Field: `amber14-all` (default)
   - Steps: `1000000`
   - Temperature: `300` K
   - ☑ Add solvent box
   - ☐ Run on HPC/SLURM (leave unchecked for local)

3. **Start**:
   - Press `s` or click **Start Simulation**
   - Watch workflow progress in Status panel
   - Monitor agent activity in real-time

4. **Results**:
   - Switch to "Results & Analysis" panel
   - Click "Files" tab to see generated files
   - Check "Metrics" tab for RMSD/RMSF plots

**Expected Output**:
```
protein_md_runs/run_20260107_235800/
├── 1ubq.pdb              # Downloaded structure
├── cleaned.pdb           # After ChimeraX cleaning
├── solvated.pdb          # With water box
├── trajectory.dcd        # MD trajectory
├── simulation.log        # OpenMM log
├── rmsd.png             # RMSD plot
└── rmsf.png             # RMSF plot
```

## Common Workflows

### 1. Quick Test (1 minute)
**Goal**: Validate setup without running full simulation

```
PDB ID: 1UBQ
Steps: 10000 (10k steps, ~10ps)
Temperature: 300K
☑ Solvate
```

Press `v` (Validate) to check configuration without running.

### 2. Standard Equilibration (30 minutes)
**Goal**: Equilibrate protein in water box

```
PDB ID: 1L2Y (Trp-cage, small fast-folding protein)
Steps: 5000000 (5M steps, ~5ns)
Temperature: 300K
☑ Solvate
☐ HPC
```

Expected time: ~30 minutes on modern CPU/GPU

### 3. Production Run (2-4 hours)
**Goal**: Generate trajectory for analysis

```
PDB ID: 2MHC (MHC complex)
Steps: 50000000 (50M steps, ~50ns)
Temperature: 300K
☑ Solvate
☑ HPC (recommended)
☑ Enable visualization
```

Submit to HPC for faster completion.

### 4. WESTPA Folding (8-24 hours)
**Goal**: Sample protein folding pathways

```
Simulation Type: ☑ Weighted Ensemble (WESTPA)
Structure: AlphaFold UniProt ID
ID: P0CG48 (HIV-1 capsid protein, unfolded)
Force Field: amber14-all
☑ HPC (required for WESTPA)
```

WESTPA runs 48 parallel walkers, needs HPC cluster.

## Keyboard Shortcuts

| Key | Action | Description |
|-----|--------|-------------|
| `s` | Start Simulation | Begin configured workflow |
| `v` | Validate | Check config without running |
| `c` | Clear Console | Clear output log |
| `q` | Quit | Exit TUI |
| `Tab` | Navigate | Move between panels |
| `Enter` | Select | Activate buttons/inputs |

## Interpreting Status Indicators

### Workflow Status Panel

| Symbol | Meaning |
|--------|---------|
| ⚪ | Not started |
| 🔄 | In progress |
| ✅ | Completed successfully |
| ⚠️ | Completed with warnings |
| ❌ | Failed (see console for details) |

### Console Log Levels

| Icon | Level | Example |
|------|-------|---------|
| ℹ️ | Info | `System initialized` |
| ✅ | Success | `Structure downloaded: 1231 atoms` |
| ⚠️ | Warning | `Force field missing some parameters` |
| ❌ | Error | `PDB download failed: invalid ID` |

## Agent Activity Timeline

Watch agents work in real-time:

```
[12:34:56] StructureCreator: Downloading PDB 1UBQ
[12:35:01] ChimeraXAgent: Cleaning structure
[12:35:05] ForceFieldManager: Validating AMBER14
[12:35:08] ValidationManager: ✅ All gates passed
[12:35:10] OpenMMManager: Starting simulation
[12:45:00] ResultsAnalyzer: Calculating RMSD
```

## Troubleshooting

### Issue: "No PDB ID provided"
**Solution**: Enter PDB ID in input field (e.g., `1UBQ`)

### Issue: "Force field incomplete"
**Solution**: Try different force field or use custom parameters
- Standard proteins: `amber14-all`
- Membrane proteins: `charmm36`
- Small molecules: `openff-2.0.0`

### Issue: "Simulation failed: atom clash"
**Solution**: 
1. Enable "Add solvent box" checkbox
2. Ensure ChimeraX cleaned structure
3. Try minimization before MD

### Issue: HPC job stays "Queued"
**Solution**: 
1. Check SLURM queue position (console log)
2. Wait for resources to become available
3. Reduce requested nodes/GPUs
4. Check HPC job limits (`squeue -u $USER`)

### Issue: TUI won't start
**Solution**:
```bash
# Install/upgrade Textual
pip install --upgrade textual

# Check Python version (need 3.11+)
python --version

# Run diagnostics
python launch_tui.py
```

## Advanced Tips

### Tip 1: Batch Simulations
Edit `protein_tui.py` to loop over multiple PDB IDs:

```python
pdb_ids = ["1UBQ", "1L2Y", "2MHC"]
for pdb_id in pdb_ids:
    config["pdb_id"] = pdb_id
    await self.run_simulation(config)
```

### Tip 2: Custom Prompts
Add custom instructions to the generated prompt:

```python
# In build_prompt()
prompt += "Additionally, calculate secondary structure content. "
```

### Tip 3: Monitor HPC Jobs
Check job status from console:

```bash
# On HPC cluster
squeue -u $USER
sacct -j JOBID --format=JobID,State,Elapsed,CPUTime
```

### Tip 4: Resume Failed Simulations
If simulation crashes, resume from checkpoint:

```python
# In OpenMM
simulation.loadCheckpoint('checkpoint.chk')
simulation.step(remaining_steps)
```

## Configuration Presets

### Preset 1: Fast Test
```
Steps: 10000
Temperature: 300K
☑ Solvate
☐ HPC
Time: ~1 minute
```

### Preset 2: Overnight Run
```
Steps: 20000000 (20M, ~20ns)
Temperature: 300K
☑ Solvate
☑ HPC
Time: ~8 hours
```

### Preset 3: High-Temperature Unfolding
```
Steps: 10000000
Temperature: 400K (high)
☑ Solvate
Purpose: Study thermal denaturation
```

### Preset 4: Cold Denaturation
```
Steps: 10000000
Temperature: 250K (low)
☑ Solvate
Purpose: Study cold-induced unfolding
```

## Results Interpretation

### Files Tab
- **PDB files** (`.pdb`): Structures at various stages
- **Trajectories** (`.dcd`, `.xtc`): Atomic positions over time
- **Logs** (`.log`, `.out`): Simulation output
- **Plots** (`.png`): RMSD, RMSF, energy graphs

### Metrics Tab
- **RMSD**: Backbone deviation from starting structure
  - Low (<2Å): Stable, equilibrated
  - High (>5Å): Large conformational change
- **RMSF**: Per-residue flexibility
  - Loops: High RMSF (flexible)
  - Helices/sheets: Low RMSF (rigid)

### Visualization Tab
- **Trajectory movies**: ChimeraX-generated animations
- **Contact maps**: Residue-residue interactions
- **Secondary structure**: Helix/sheet content over time

## Next Steps

1. **Analyze Results**: Use MDTraj/MDAnalysis for detailed analysis
2. **Visualize**: Open trajectories in VMD/PyMOL/ChimeraX
3. **Compare**: Run multiple replicates with different seeds
4. **Publish**: Generate publication-quality figures

## Getting Help

- Check console output for error messages
- Read `TUI_README.md` for detailed documentation
- Review agent system messages in `src/system_messages/`
- Open GitHub issue with TUI logs

## Demo Mode

If AutoGen/OpenMM not installed, TUI runs in demo mode:
- Simulates workflow progress
- Shows how interface works
- No actual calculations performed

Install dependencies for full functionality:
```bash
pip install autogen-agentchat autogen-ext
conda install -c conda-forge openmm
```

---

**Happy Simulating!** 🧬🚀

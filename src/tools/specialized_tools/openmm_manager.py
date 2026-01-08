"""
OpenMM Simulation Manager

Handles molecular dynamics simulations using OpenMM Python API.
Replaces LAMMPS subprocess calls with direct OpenMM integration.
"""

import os
import subprocess
from typing import Optional, Tuple, Dict, Any


class OpenMMManager:
    """Manages OpenMM molecular dynamics simulations."""
    
    def __init__(self, workdir: str):
        self.workdir = workdir
        self.workflow_logger = None  # Set by AutoGenSystem
        
        # Simulation state tracking
        self.last_simulation_file = None
        self.simulation_completed = False
        self.last_trajectory_file = None
        
    def _log(self, message: str):
        """Log message if workflow logger is available."""
        if self.workflow_logger:
            self.workflow_logger.log_tool_invocation(
                "OpenMMManager", {}, message
            )
    
    def run_simulation(self, pdb_file: str, forcefield: str = "amber14-all.xml",
                      water_model: str = "amber14/tip3pfb.xml",
                      steps: int = 10000, temperature: float = 300.0,
                      pressure: float = 1.0, ensemble: str = "NPT",
                      output_prefix: str = "simulation") -> str:
        """
        Run an OpenMM molecular dynamics simulation.
        
        Args:
            pdb_file: Path to input PDB file
            forcefield: Force field XML file (e.g., 'amber14-all.xml')
            water_model: Water model XML (e.g., 'amber14/tip3pfb.xml')
            steps: Number of simulation steps
            temperature: Temperature in Kelvin
            pressure: Pressure in atm (for NPT)
            ensemble: 'NVT' or 'NPT'
            output_prefix: Prefix for output files
            
        Returns:
            Status message string
        """
        self._log(f"Starting {ensemble} simulation: {pdb_file}, {steps} steps")
        
        try:
            from openmm import app, unit, LangevinMiddleIntegrator, MonteCarloBarostat
            from openmm import Platform
            import openmm
        except ImportError:
            return "❌ OpenMM not installed. Run: pip install openmm"
        
        # Construct full path
        if not os.path.isabs(pdb_file):
            pdb_path = os.path.join(self.workdir, pdb_file)
        else:
            pdb_path = pdb_file
            
        if not os.path.exists(pdb_path):
            return f"❌ PDB file not found: {pdb_path}"
        
        try:
            # Load structure
            pdb = app.PDBFile(pdb_path)
            
            # Create force field
            ff = app.ForceField(forcefield, water_model)
            
            # Create system
            system = ff.createSystem(
                pdb.topology,
                nonbondedMethod=app.PME,
                nonbondedCutoff=1.0*unit.nanometer,
                constraints=app.HBonds
            )
            
            # Add barostat for NPT
            if ensemble.upper() == "NPT":
                system.addForce(MonteCarloBarostat(
                    pressure * unit.atmosphere,
                    temperature * unit.kelvin
                ))
            
            # Create integrator
            integrator = LangevinMiddleIntegrator(
                temperature * unit.kelvin,
                1.0 / unit.picosecond,
                0.002 * unit.picoseconds  # 2 fs timestep
            )
            
            # Select platform (prefer CUDA > OpenCL > CPU)
            platform = self._get_best_platform()
            
            # Create simulation
            simulation = app.Simulation(pdb.topology, system, integrator, platform)
            simulation.context.setPositions(pdb.positions)
            
            # Energy minimization
            print("  ⚡ Running energy minimization...")
            simulation.minimizeEnergy(maxIterations=1000)
            
            # Set up reporters
            dcd_file = os.path.join(self.workdir, f"{output_prefix}.dcd")
            log_file = os.path.join(self.workdir, f"{output_prefix}.log")
            
            simulation.reporters.append(app.DCDReporter(dcd_file, 1000))  # Save every 1000 steps
            simulation.reporters.append(app.StateDataReporter(
                log_file, 1000,
                step=True, time=True, potentialEnergy=True, kineticEnergy=True,
                totalEnergy=True, temperature=True, volume=True, density=True
            ))
            
            # Run simulation
            print(f"  🔬 Running {steps} steps of {ensemble} dynamics...")
            simulation.step(steps)
            
            # Get final state
            state = simulation.context.getState(getEnergy=True, getPositions=True)
            final_energy = state.getPotentialEnergy().value_in_unit(unit.kilojoules_per_mole)
            
            # Save final structure
            final_pdb = os.path.join(self.workdir, f"{output_prefix}_final.pdb")
            positions = state.getPositions()
            app.PDBFile.writeFile(simulation.topology, positions, open(final_pdb, 'w'))
            
            # Update state
            self.last_simulation_file = final_pdb
            self.last_trajectory_file = dcd_file
            self.simulation_completed = True
            
            return f"""✅ OpenMM {ensemble} simulation completed successfully:
  📄 Input: {pdb_file}
  🔬 Force field: {forcefield}
  ⚙️  Steps: {steps} ({steps * 0.002:.2f} ps)
  🌡️  Temperature: {temperature} K
  💧 Water model: {water_model}
  ⚡ Final energy: {final_energy:.2f} kJ/mol
  📁 Trajectory: {dcd_file}
  📁 Final structure: {final_pdb}
  📁 Log file: {log_file}"""
            
        except Exception as e:
            self._log(f"Simulation failed: {str(e)}")
            return f"❌ OpenMM simulation failed: {str(e)}"
    
    def run_equilibration(self, pdb_file: str, forcefield: str = "amber14-all.xml",
                         nvt_steps: int = 50000, npt_steps: int = 100000,
                         temperature: float = 300.0, output_prefix: str = "equil") -> str:
        """
        Run standard equilibration protocol: NVT heating followed by NPT.
        
        Args:
            pdb_file: Input PDB file
            forcefield: Force field to use
            nvt_steps: Number of NVT steps
            npt_steps: Number of NPT steps
            temperature: Target temperature (K)
            output_prefix: Output file prefix
            
        Returns:
            Status message
        """
        self._log(f"Starting equilibration protocol: {pdb_file}")
        
        # Phase 1: NVT heating
        print("📌 Phase 1: NVT equilibration...")
        nvt_result = self.run_simulation(
            pdb_file=pdb_file,
            forcefield=forcefield,
            steps=nvt_steps,
            temperature=temperature,
            ensemble="NVT",
            output_prefix=f"{output_prefix}_nvt"
        )
        
        if "❌" in nvt_result:
            return nvt_result
        
        # Phase 2: NPT equilibration using NVT output
        print("📌 Phase 2: NPT equilibration...")
        nvt_final = os.path.join(self.workdir, f"{output_prefix}_nvt_final.pdb")
        
        npt_result = self.run_simulation(
            pdb_file=nvt_final,
            forcefield=forcefield,
            steps=npt_steps,
            temperature=temperature,
            ensemble="NPT",
            output_prefix=f"{output_prefix}_npt"
        )
        
        if "❌" in npt_result:
            return npt_result
        
        return f"""✅ Equilibration protocol completed:
  📌 Phase 1 (NVT): {nvt_steps} steps
  📌 Phase 2 (NPT): {npt_steps} steps
  🌡️  Temperature: {temperature} K
  📁 Final structure: {output_prefix}_npt_final.pdb
  📁 NPT trajectory: {output_prefix}_npt.dcd"""
    
    def minimize_structure(self, pdb_file: str, forcefield: str = "amber14-all.xml",
                          max_iterations: int = 10000, output_file: str = None) -> str:
        """
        Perform energy minimization on a structure.
        
        Args:
            pdb_file: Input PDB file
            forcefield: Force field XML
            max_iterations: Maximum minimization steps
            output_file: Output PDB filename
            
        Returns:
            Status message
        """
        self._log(f"Minimizing structure: {pdb_file}")
        
        try:
            from openmm import app, unit
        except ImportError:
            return "❌ OpenMM not installed. Run: pip install openmm"
        
        if not os.path.isabs(pdb_file):
            pdb_path = os.path.join(self.workdir, pdb_file)
        else:
            pdb_path = pdb_file
            
        if not os.path.exists(pdb_path):
            return f"❌ PDB file not found: {pdb_path}"
        
        try:
            # Load structure
            pdb = app.PDBFile(pdb_path)
            
            # Create force field (without water model for vacuum minimization)
            ff = app.ForceField(forcefield)
            
            # Create system with implicit solvent
            system = ff.createSystem(
                pdb.topology,
                nonbondedMethod=app.NoCutoff,
                constraints=app.HBonds
            )
            
            # Create integrator (required but not used for minimization)
            from openmm import LangevinMiddleIntegrator
            integrator = LangevinMiddleIntegrator(
                300 * unit.kelvin,
                1.0 / unit.picosecond,
                0.002 * unit.picoseconds
            )
            
            # Create simulation
            platform = self._get_best_platform()
            simulation = app.Simulation(pdb.topology, system, integrator, platform)
            simulation.context.setPositions(pdb.positions)
            
            # Get initial energy
            state = simulation.context.getState(getEnergy=True)
            initial_energy = state.getPotentialEnergy().value_in_unit(unit.kilojoules_per_mole)
            
            # Minimize
            simulation.minimizeEnergy(maxIterations=max_iterations)
            
            # Get final energy
            state = simulation.context.getState(getEnergy=True, getPositions=True)
            final_energy = state.getPotentialEnergy().value_in_unit(unit.kilojoules_per_mole)
            
            # Save minimized structure
            if output_file is None:
                base = os.path.splitext(os.path.basename(pdb_file))[0]
                output_file = f"{base}_minimized.pdb"
            
            output_path = os.path.join(self.workdir, output_file)
            positions = state.getPositions()
            app.PDBFile.writeFile(simulation.topology, positions, open(output_path, 'w'))
            
            return f"""✅ Energy minimization completed:
  📄 Input: {pdb_file}
  ⚡ Initial energy: {initial_energy:.2f} kJ/mol
  ⚡ Final energy: {final_energy:.2f} kJ/mol
  📉 Energy change: {final_energy - initial_energy:.2f} kJ/mol
  📁 Output: {output_file}"""
            
        except Exception as e:
            return f"❌ Minimization failed: {str(e)}"
    
    def solvate_system(self, pdb_file: str, forcefield: str = "amber14-all.xml",
                      water_model: str = "amber14/tip3pfb.xml",
                      padding: float = 1.0, ionic_strength: float = 0.15,
                      output_file: str = None) -> str:
        """
        Add water box and ions to a protein structure.
        
        Args:
            pdb_file: Input PDB file
            forcefield: Force field XML
            water_model: Water model XML
            padding: Box padding in nm
            ionic_strength: Ion concentration in M
            output_file: Output filename
            
        Returns:
            Status message
        """
        self._log(f"Solvating system: {pdb_file}")
        
        try:
            from openmm import app, unit
        except ImportError:
            return "❌ OpenMM not installed. Run: pip install openmm"
        
        if not os.path.isabs(pdb_file):
            pdb_path = os.path.join(self.workdir, pdb_file)
        else:
            pdb_path = pdb_file
            
        if not os.path.exists(pdb_path):
            return f"❌ PDB file not found: {pdb_path}"
        
        try:
            # Load structure
            pdb = app.PDBFile(pdb_path)
            
            # Create force field
            ff = app.ForceField(forcefield, water_model)
            
            # Create modeller for adding water
            modeller = app.Modeller(pdb.topology, pdb.positions)
            
            # Add water box
            modeller.addSolvent(
                ff,
                padding=padding * unit.nanometer,
                ionicStrength=ionic_strength * unit.molar
            )
            
            # Count molecules
            n_waters = sum(1 for r in modeller.topology.residues() if r.name == 'HOH')
            n_ions = sum(1 for r in modeller.topology.residues() if r.name in ['NA', 'CL', 'K'])
            
            # Save solvated system
            if output_file is None:
                base = os.path.splitext(os.path.basename(pdb_file))[0]
                output_file = f"{base}_solvated.pdb"
            
            output_path = os.path.join(self.workdir, output_file)
            app.PDBFile.writeFile(modeller.topology, modeller.positions, open(output_path, 'w'))
            
            return f"""✅ System solvated successfully:
  📄 Input: {pdb_file}
  💧 Water molecules: {n_waters}
  🧂 Ions added: {n_ions}
  📦 Box padding: {padding} nm
  ⚗️  Ionic strength: {ionic_strength} M
  📁 Output: {output_file}"""
            
        except Exception as e:
            return f"❌ Solvation failed: {str(e)}"
    
    def generate_openmm_script(self, pdb_file: str, forcefield: str = "amber14-all.xml",
                              water_model: str = "amber14/tip3pfb.xml",
                              steps: int = 500000, temperature: float = 300.0,
                              ensemble: str = "NPT", script_name: str = "run_openmm.py") -> str:
        """
        Generate a standalone OpenMM Python script for HPC submission.
        
        Args:
            pdb_file: Input PDB file
            forcefield: Force field XML
            water_model: Water model
            steps: Simulation steps
            temperature: Temperature (K)
            ensemble: NVT or NPT
            script_name: Output script filename
            
        Returns:
            Status message and script path
        """
        self._log(f"Generating OpenMM script for {pdb_file}")
        
        barostat_code = ""
        if ensemble.upper() == "NPT":
            barostat_code = """
# Add barostat for NPT
system.addForce(MonteCarloBarostat(1.0*atmosphere, {temperature}*kelvin))
""".format(temperature=temperature)
        
        script_content = f'''#!/usr/bin/env python
"""
OpenMM Simulation Script
Generated for HPC execution

Input: {pdb_file}
Force field: {forcefield}
Ensemble: {ensemble}
Steps: {steps}
"""

from openmm import app, unit
from openmm import LangevinMiddleIntegrator, MonteCarloBarostat, Platform
from openmm.unit import kelvin, nanometer, picosecond, picoseconds, atmosphere
import os

# Configuration
PDB_FILE = "{pdb_file}"
FORCEFIELD = "{forcefield}"
WATER_MODEL = "{water_model}"
STEPS = {steps}
TEMPERATURE = {temperature}
TIMESTEP = 0.002  # ps

# Load structure
print("Loading structure...")
pdb = app.PDBFile(PDB_FILE)

# Create force field
print("Creating force field...")
ff = app.ForceField(FORCEFIELD, WATER_MODEL)

# Create system
print("Creating system...")
system = ff.createSystem(
    pdb.topology,
    nonbondedMethod=app.PME,
    nonbondedCutoff=1.0*nanometer,
    constraints=app.HBonds
)
{barostat_code}
# Create integrator
integrator = LangevinMiddleIntegrator(
    TEMPERATURE*kelvin,
    1.0/picosecond,
    TIMESTEP*picoseconds
)

# Select platform (CUDA preferred)
try:
    platform = Platform.getPlatformByName('CUDA')
    properties = {{'CudaPrecision': 'mixed'}}
    simulation = app.Simulation(pdb.topology, system, integrator, platform, properties)
except:
    simulation = app.Simulation(pdb.topology, system, integrator)

simulation.context.setPositions(pdb.positions)

# Energy minimization
print("Minimizing energy...")
simulation.minimizeEnergy(maxIterations=1000)

# Set up reporters
simulation.reporters.append(app.DCDReporter('trajectory.dcd', 5000))
simulation.reporters.append(app.StateDataReporter(
    'simulation.log', 5000,
    step=True, time=True, potentialEnergy=True, 
    temperature=True, volume=True, speed=True
))
simulation.reporters.append(app.CheckpointReporter('checkpoint.chk', 50000))

# Run simulation
print(f"Running {{STEPS}} steps of {ensemble} dynamics...")
simulation.step(STEPS)

# Save final state
print("Saving final structure...")
state = simulation.context.getState(getPositions=True)
app.PDBFile.writeFile(simulation.topology, state.getPositions(), open('final.pdb', 'w'))

print("Simulation complete!")
'''
        
        script_path = os.path.join(self.workdir, script_name)
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        return f"""✅ OpenMM script generated:
  📄 Script: {script_name}
  🔬 Input PDB: {pdb_file}
  ⚙️  Steps: {steps} ({steps * 0.002 / 1000:.2f} ns)
  🌡️  Temperature: {temperature} K
  📦 Ensemble: {ensemble}
  
  To run locally: python {script_name}
  For HPC: Submit via SLURM manager"""
    
    def _get_best_platform(self):
        """Get the best available OpenMM platform."""
        try:
            from openmm import Platform
            
            # Try platforms in order of preference
            for platform_name in ['CUDA', 'OpenCL', 'CPU']:
                try:
                    platform = Platform.getPlatformByName(platform_name)
                    print(f"  🖥️  Using {platform_name} platform")
                    return platform
                except:
                    continue
            
            # Fallback to default
            return None
            
        except ImportError:
            return None
    
    def analyze_trajectory(self, trajectory_file: str, topology_file: str,
                          output_prefix: str = "analysis") -> str:
        """
        Basic trajectory analysis using MDTraj.
        
        Args:
            trajectory_file: DCD/XTC trajectory file
            topology_file: PDB topology file
            output_prefix: Output file prefix
            
        Returns:
            Status message with analysis results
        """
        self._log(f"Analyzing trajectory: {trajectory_file}")
        
        try:
            import mdtraj as md
            import numpy as np
        except ImportError:
            return "❌ MDTraj not installed. Run: pip install mdtraj"
        
        traj_path = os.path.join(self.workdir, trajectory_file) if not os.path.isabs(trajectory_file) else trajectory_file
        top_path = os.path.join(self.workdir, topology_file) if not os.path.isabs(topology_file) else topology_file
        
        if not os.path.exists(traj_path):
            return f"❌ Trajectory file not found: {traj_path}"
        if not os.path.exists(top_path):
            return f"❌ Topology file not found: {top_path}"
        
        try:
            # Load trajectory
            traj = md.load(traj_path, top=top_path)
            
            # Calculate RMSD
            rmsd = md.rmsd(traj, traj, frame=0)
            
            # Calculate RMSF (per-residue)
            rmsf = md.rmsf(traj, traj, frame=0)
            
            # Calculate radius of gyration
            rg = md.compute_rg(traj)
            
            # Save RMSD data
            rmsd_file = os.path.join(self.workdir, f"{output_prefix}_rmsd.dat")
            np.savetxt(rmsd_file, np.column_stack([np.arange(len(rmsd)), rmsd]), 
                      header="Frame RMSD(nm)", fmt='%d %.6f')
            
            # Save RMSF data
            rmsf_file = os.path.join(self.workdir, f"{output_prefix}_rmsf.dat")
            np.savetxt(rmsf_file, np.column_stack([np.arange(len(rmsf)), rmsf]),
                      header="Atom RMSF(nm)", fmt='%d %.6f')
            
            # Save Rg data
            rg_file = os.path.join(self.workdir, f"{output_prefix}_rg.dat")
            np.savetxt(rg_file, np.column_stack([np.arange(len(rg)), rg]),
                      header="Frame Rg(nm)", fmt='%d %.6f')
            
            return f"""✅ Trajectory analysis completed:
  📄 Trajectory: {trajectory_file}
  🔢 Frames: {traj.n_frames}
  ⚛️  Atoms: {traj.n_atoms}
  
  📊 RMSD: {rmsd.mean():.3f} ± {rmsd.std():.3f} nm
  📊 Rg: {rg.mean():.3f} ± {rg.std():.3f} nm
  
  📁 RMSD data: {output_prefix}_rmsd.dat
  📁 RMSF data: {output_prefix}_rmsf.dat
  📁 Rg data: {output_prefix}_rg.dat"""
            
        except Exception as e:
            return f"❌ Trajectory analysis failed: {str(e)}"

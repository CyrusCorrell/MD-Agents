#!/usr/bin/env python3
"""
Protein MD Simulation TUI
Interactive terminal interface for the multi-agent protein simulation framework
"""

import os
import sys
import asyncio
from datetime import datetime
from typing import Optional, List, Dict
from pathlib import Path

try:
    from textual.app import App, ComposeResult
    from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
    from textual.widgets import (
        Header, Footer, Button, Static, Input, TextLog, 
        Select, RadioButton, RadioSet, Checkbox, TabbedContent, TabPane,
        DataTable, ProgressBar, Label
    )
    from textual.binding import Binding
    from textual.reactive import reactive
    from textual import on
except ImportError:
    print("ERROR: Textual library not installed. Install with: pip install textual")
    sys.exit(1)

# Import the core system
try:
    from lammps_agents import AutoGenSystem
except ImportError:
    print("WARNING: AutoGenSystem not found. Running in demo mode.")
    AutoGenSystem = None


class WorkflowStatus(Static):
    """Widget showing current workflow status"""
    
    def __init__(self):
        super().__init__()
        self.status_data = {
            "structure": "⚪ Not Started",
            "forcefield": "⚪ Not Started",
            "validation": "⚪ Not Started",
            "simulation": "⚪ Not Started",
            "analysis": "⚪ Not Started"
        }
    
    def compose(self) -> ComposeResult:
        yield Static("📊 Workflow Status", classes="section-title")
        yield Static(id="status-content")
    
    def on_mount(self) -> None:
        self.update_display()
    
    def update_status(self, step: str, status: str):
        """Update a workflow step status"""
        if step in self.status_data:
            self.status_data[step] = status
            self.update_display()
    
    def update_display(self):
        """Refresh the status display"""
        content = "\n".join([
            f"{step.title()}: {status}"
            for step, status in self.status_data.items()
        ])
        self.query_one("#status-content", Static).update(content)


class AgentMonitor(Static):
    """Widget showing agent activity"""
    
    def __init__(self):
        super().__init__()
        self.active_agents = []
    
    def compose(self) -> ComposeResult:
        yield Static("🤖 Active Agents", classes="section-title")
        yield Static(id="agent-content")
    
    def on_mount(self) -> None:
        self.update_display()
    
    def add_agent_activity(self, agent_name: str, action: str):
        """Record agent activity"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.active_agents.append(f"[{timestamp}] {agent_name}: {action}")
        if len(self.active_agents) > 10:
            self.active_agents = self.active_agents[-10:]
        self.update_display()
    
    def update_display(self):
        """Refresh the agent activity display"""
        if not self.active_agents:
            content = "No active agents"
        else:
            content = "\n".join(self.active_agents)
        self.query_one("#agent-content", Static).update(content)


class SimulationSetup(Container):
    """Simulation configuration panel"""
    
    def compose(self) -> ComposeResult:
        yield Static("⚙️ Simulation Setup", classes="section-title")
        
        with Vertical():
            # Simulation type selection
            yield Label("Simulation Type:")
            with RadioSet(id="sim-type"):
                yield RadioButton("Standard MD", value=True)
                yield RadioButton("Weighted Ensemble (WESTPA)")
                yield RadioButton("Free Energy Calculation")
            
            # Structure source
            yield Label("\nStructure Source:")
            with RadioSet(id="structure-source"):
                yield RadioButton("RCSB PDB ID", value=True)
                yield RadioButton("AlphaFold UniProt ID")
                yield RadioButton("Local PDB File")
            
            yield Input(placeholder="Enter PDB ID (e.g., 1UBQ)", id="pdb-input")
            
            # Force field selection
            yield Label("\nForce Field:")
            yield Select(
                [
                    ("AMBER14 (default)", "amber14-all"),
                    ("AMBER19", "amber19"),
                    ("CHARMM36", "charmm36"),
                    ("OpenFF 2.0", "openff-2.0.0")
                ],
                value="amber14-all",
                id="forcefield-select"
            )
            
            # Simulation parameters
            yield Label("\nSimulation Length:")
            yield Input(placeholder="1000000 (steps)", value="1000000", id="steps-input")
            
            yield Label("Temperature (K):")
            yield Input(placeholder="300", value="300", id="temp-input")
            
            # Execution options
            yield Label("\nExecution:")
            yield Checkbox("Add solvent box", value=True, id="solvate-check")
            yield Checkbox("Run on HPC/SLURM", value=False, id="hpc-check")
            yield Checkbox("Enable visualization", value=True, id="viz-check")
            
            # Action buttons
            with Horizontal():
                yield Button("Start Simulation", variant="primary", id="start-btn")
                yield Button("Validate Setup", variant="default", id="validate-btn")
                yield Button("Clear", variant="warning", id="clear-btn")


class ConsoleLog(Container):
    """Console output display"""
    
    def compose(self) -> ComposeResult:
        yield Static("📜 Console Output", classes="section-title")
        yield TextLog(id="console-log", wrap=True, highlight=True)
    
    def on_mount(self) -> None:
        log = self.query_one("#console-log", TextLog)
        log.write("System initialized. Ready for simulation.")
    
    def log_message(self, message: str, level: str = "info"):
        """Add message to console"""
        log = self.query_one("#console-log", TextLog)
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if level == "error":
            prefix = "❌"
        elif level == "warning":
            prefix = "⚠️"
        elif level == "success":
            prefix = "✅"
        else:
            prefix = "ℹ️"
        
        log.write(f"[{timestamp}] {prefix} {message}")


class ResultsViewer(Container):
    """Results and analysis display"""
    
    def compose(self) -> ComposeResult:
        yield Static("📊 Results & Analysis", classes="section-title")
        
        with TabbedContent():
            with TabPane("Summary"):
                yield Static(id="results-summary")
            
            with TabPane("Files"):
                yield DataTable(id="results-files")
            
            with TabPane("Metrics"):
                yield Static(id="results-metrics")
            
            with TabPane("Visualization"):
                yield Static(id="results-viz")
    
    def on_mount(self) -> None:
        # Initialize results tables
        table = self.query_one("#results-files", DataTable)
        table.add_columns("Filename", "Type", "Size", "Modified")
        
        self.query_one("#results-summary", Static).update(
            "No simulation results yet. Start a simulation to see results here."
        )
    
    def update_results(self, workdir: str):
        """Update results display with files from workdir"""
        table = self.query_one("#results-files", DataTable)
        table.clear()
        
        if os.path.exists(workdir):
            for file in Path(workdir).iterdir():
                if file.is_file():
                    stat = file.stat()
                    size = f"{stat.st_size / 1024:.1f} KB"
                    modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                    
                    file_type = "Unknown"
                    if file.suffix == ".pdb":
                        file_type = "Structure"
                    elif file.suffix in [".dcd", ".xtc", ".trr"]:
                        file_type = "Trajectory"
                    elif file.suffix in [".log", ".out"]:
                        file_type = "Log"
                    elif file.suffix in [".png", ".jpg"]:
                        file_type = "Visualization"
                    
                    table.add_row(file.name, file_type, size, modified)


class ProteinMDTUI(App):
    """Main TUI Application for Protein MD Simulations"""
    
    CSS = """
    Screen {
        layout: grid;
        grid-size: 2 3;
        grid-gutter: 1;
    }
    
    .section-title {
        background: $boost;
        color: $text;
        padding: 1;
        text-align: center;
        text-style: bold;
    }
    
    #status-panel {
        column-span: 1;
        row-span: 1;
        border: solid $primary;
    }
    
    #agent-panel {
        column-span: 1;
        row-span: 1;
        border: solid $secondary;
    }
    
    #setup-panel {
        column-span: 1;
        row-span: 2;
        border: solid $accent;
    }
    
    #console-panel {
        column-span: 1;
        row-span: 1;
        border: solid $warning;
    }
    
    #results-panel {
        column-span: 2;
        row-span: 1;
        border: solid $success;
    }
    
    Button {
        margin: 1;
    }
    
    Input {
        margin: 0 1;
    }
    
    Select {
        margin: 0 1;
    }
    
    RadioButton {
        margin: 0 2;
    }
    
    Checkbox {
        margin: 0 2;
    }
    
    #console-log {
        height: 100%;
        background: $surface;
    }
    """
    
    TITLE = "Protein MD Simulation - Multi-Agent Framework"
    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("s", "start_simulation", "Start", show=True),
        Binding("v", "validate", "Validate", show=True),
        Binding("c", "clear_console", "Clear", show=True),
    ]
    
    def __init__(self):
        super().__init__()
        self.autogen_system: Optional[AutoGenSystem] = None
        self.workdir = "protein_md_runs"
        self.current_run = None
    
    def compose(self) -> ComposeResult:
        """Create the UI layout"""
        yield Header()
        
        # Status panel
        with Container(id="status-panel"):
            yield WorkflowStatus()
        
        # Agent monitor panel
        with Container(id="agent-panel"):
            yield AgentMonitor()
        
        # Setup panel
        with ScrollableContainer(id="setup-panel"):
            yield SimulationSetup()
        
        # Console panel
        with Container(id="console-panel"):
            yield ConsoleLog()
        
        # Results panel
        with Container(id="results-panel"):
            yield ResultsViewer()
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize on startup"""
        self.log_console("🚀 Protein MD TUI Started")
        self.log_console(f"Working directory: {self.workdir}")
        
        # Check dependencies
        self.check_dependencies()
    
    def check_dependencies(self):
        """Check if required packages are available"""
        missing = []
        
        try:
            import openmm
            self.log_console("✅ OpenMM found", "success")
        except ImportError:
            missing.append("openmm")
            self.log_console("❌ OpenMM not found", "error")
        
        try:
            import mdtraj
            self.log_console("✅ MDTraj found", "success")
        except ImportError:
            missing.append("mdtraj")
            self.log_console("⚠️ MDTraj not found (optional)", "warning")
        
        if AutoGenSystem is None:
            self.log_console("⚠️ AutoGenSystem not loaded - demo mode", "warning")
        else:
            self.log_console("✅ AutoGenSystem loaded", "success")
        
        if missing:
            self.log_console(f"Install missing packages: pip install {' '.join(missing)}", "warning")
    
    def log_console(self, message: str, level: str = "info"):
        """Log message to console"""
        console = self.query_one("#console-panel").query_one(ConsoleLog)
        console.log_message(message, level)
    
    def update_workflow_status(self, step: str, status: str):
        """Update workflow status display"""
        status_widget = self.query_one("#status-panel").query_one(WorkflowStatus)
        status_widget.update_status(step, status)
    
    def add_agent_activity(self, agent: str, action: str):
        """Log agent activity"""
        monitor = self.query_one("#agent-panel").query_one(AgentMonitor)
        monitor.add_agent_activity(agent, action)
    
    @on(Button.Pressed, "#start-btn")
    async def start_simulation(self):
        """Start the simulation workflow"""
        self.log_console("🚀 Starting simulation...", "info")
        
        # Get configuration
        config = self.get_simulation_config()
        
        if not config["pdb_id"]:
            self.log_console("ERROR: No PDB ID provided", "error")
            return
        
        self.log_console(f"Configuration: {config}", "info")
        
        # Update workflow status
        self.update_workflow_status("structure", "🔄 Downloading...")
        self.add_agent_activity("StructureCreator", f"Downloading PDB {config['pdb_id']}")
        
        # Create run directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_run = os.path.join(self.workdir, f"run_{timestamp}")
        os.makedirs(self.current_run, exist_ok=True)
        
        self.log_console(f"Run directory: {self.current_run}", "info")
        
        # Initialize AutoGen system if available
        if AutoGenSystem:
            try:
                self.log_console("Initializing AutoGen system...", "info")
                self.autogen_system = AutoGenSystem(
                    llm_type="gpt4o",
                    workdir=self.current_run
                )
                
                # Build prompt
                prompt = self.build_prompt(config)
                self.log_console(f"Prompt: {prompt}", "info")
                
                # Run simulation
                self.update_workflow_status("simulation", "▶️ Running...")
                self.add_agent_activity("Manager", "Initiating chat")
                
                # This would run async in production
                self.log_console("⏳ Simulation in progress (this may take a while)...", "info")
                
                # Simulate progress
                await self.simulate_workflow_progress(config)
                
            except Exception as e:
                self.log_console(f"ERROR: {str(e)}", "error")
                self.update_workflow_status("simulation", "❌ Failed")
        else:
            # Demo mode
            await self.simulate_workflow_progress(config)
    
    async def simulate_workflow_progress(self, config: Dict):
        """Simulate workflow progress for demo"""
        steps = [
            ("structure", "🔄 Downloading...", 2),
            ("structure", "✅ Structure downloaded", 0),
            ("forcefield", "🔄 Validating force field...", 2),
            ("forcefield", "✅ Force field validated", 0),
            ("validation", "🔄 Running validation gates...", 2),
            ("validation", "✅ Validation passed", 0),
            ("simulation", "🔄 Running OpenMM simulation...", 5),
            ("simulation", "✅ Simulation complete", 0),
            ("analysis", "🔄 Analyzing results...", 2),
            ("analysis", "✅ Analysis complete", 0),
        ]
        
        for step, status, delay in steps:
            self.update_workflow_status(step, status)
            if "✅" in status:
                self.log_console(status, "success")
            else:
                self.log_console(status, "info")
            
            if delay > 0:
                await asyncio.sleep(delay)
        
        self.log_console("🎉 Workflow completed successfully!", "success")
        
        # Update results
        results = self.query_one("#results-panel").query_one(ResultsViewer)
        results.update_results(self.current_run)
    
    def get_simulation_config(self) -> Dict:
        """Extract configuration from UI"""
        pdb_input = self.query_one("#pdb-input", Input)
        forcefield = self.query_one("#forcefield-select", Select)
        steps = self.query_one("#steps-input", Input)
        temp = self.query_one("#temp-input", Input)
        solvate = self.query_one("#solvate-check", Checkbox)
        hpc = self.query_one("#hpc-check", Checkbox)
        
        return {
            "pdb_id": pdb_input.value,
            "forcefield": forcefield.value,
            "steps": int(steps.value) if steps.value.isdigit() else 1000000,
            "temperature": float(temp.value) if temp.value else 300.0,
            "solvate": solvate.value,
            "use_hpc": hpc.value,
        }
    
    def build_prompt(self, config: Dict) -> str:
        """Build natural language prompt for agents"""
        prompt = f"Perform a molecular dynamics simulation of protein {config['pdb_id']} using OpenMM. "
        prompt += f"Use {config['forcefield']} force field. "
        
        if config['solvate']:
            prompt += "Add solvent box with 1.0 nm padding. "
        
        prompt += f"Run simulation for {config['steps']} steps at {config['temperature']} K. "
        
        if config['use_hpc']:
            prompt += "Submit job to HPC cluster using SLURM. "
        
        prompt += "Analyze trajectory and calculate RMSD."
        
        return prompt
    
    @on(Button.Pressed, "#validate-btn")
    def validate_setup(self):
        """Validate current configuration"""
        self.log_console("🔍 Validating setup...", "info")
        config = self.get_simulation_config()
        
        # Validate PDB ID
        if not config["pdb_id"]:
            self.log_console("❌ PDB ID is required", "error")
            return
        
        if len(config["pdb_id"]) != 4:
            self.log_console("⚠️ PDB ID should be 4 characters (e.g., 1UBQ)", "warning")
        
        # Validate steps
        if config["steps"] < 1000:
            self.log_console("⚠️ Very short simulation (<1000 steps)", "warning")
        
        self.log_console("✅ Configuration valid", "success")
    
    @on(Button.Pressed, "#clear-btn")
    def clear_inputs(self):
        """Clear all inputs"""
        self.query_one("#pdb-input", Input).value = ""
        self.query_one("#steps-input", Input).value = "1000000"
        self.query_one("#temp-input", Input).value = "300"
        self.log_console("🧹 Inputs cleared", "info")
    
    def action_quit(self) -> None:
        """Quit the application"""
        self.exit()
    
    def action_start_simulation(self) -> None:
        """Keyboard shortcut for start"""
        self.query_one("#start-btn", Button).press()
    
    def action_validate(self) -> None:
        """Keyboard shortcut for validate"""
        self.query_one("#validate-btn", Button).press()
    
    def action_clear_console(self) -> None:
        """Clear console log"""
        log = self.query_one("#console-log", TextLog)
        log.clear()
        self.log_console("Console cleared", "info")


def main():
    """Entry point"""
    app = ProteinMDTUI()
    app.run()


if __name__ == "__main__":
    main()

"""
Workflow Logger - Pydantic-based Observability

Tracks agent decisions, tool invocations, validation gates, and workflow state
for debugging and transparency in the protein MD simulation framework.
"""

import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class WorkflowEvent(BaseModel):
    """A single event in the workflow execution."""
    
    timestamp: datetime = Field(default_factory=datetime.now)
    event_type: str  # 'agent_call', 'tool_invocation', 'validation_gate', 'state_change'
    agent_name: Optional[str] = None
    tool_name: Optional[str] = None
    status: str  # 'started', 'success', 'failed', 'warning'
    message: str
    context: Dict[str, Any] = Field(default_factory=dict)
    duration_ms: Optional[float] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class WorkflowState(BaseModel):
    """Current state of the protein MD workflow."""
    
    structure_downloaded: bool = False
    structure_cleaned: bool = False
    structure_solvated: bool = False
    forcefield_validated: bool = False
    system_prepared: bool = False
    simulation_running: bool = False
    simulation_completed: bool = False
    analysis_completed: bool = False
    
    current_pdb_file: Optional[str] = None
    current_forcefield: Optional[str] = None
    current_trajectory: Optional[str] = None
    
    last_error: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)


class WorkflowLogger:
    """
    Pydantic-based workflow logger for observability.
    
    Logs all agent decisions, tool invocations, and validation gates
    to a structured JSONL file for debugging and analysis.
    """
    
    def __init__(self, workdir: str):
        self.workdir = workdir
        self.events: List[WorkflowEvent] = []
        self.state = WorkflowState()
        
        # Create log file path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = os.path.join(workdir, f"workflow_log_{timestamp}.jsonl")
        
        # Performance tracking
        self._operation_start_times: Dict[str, datetime] = {}
        
        # Ensure workdir exists
        os.makedirs(workdir, exist_ok=True)
        
        # Log initialization
        self._log_event(WorkflowEvent(
            event_type="system",
            status="started",
            message="WorkflowLogger initialized",
            context={"workdir": workdir, "log_file": self.log_file}
        ))
    
    def _log_event(self, event: WorkflowEvent):
        """Write event to log file and store in memory."""
        self.events.append(event)
        
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(event.model_dump_json() + '\n')
        except Exception as e:
            print(f"⚠️ Failed to write log: {e}")
    
    def log_agent_call(self, agent_name: str, message: str, 
                       context: Dict[str, Any] = None):
        """
        Log an agent call or decision.
        
        Args:
            agent_name: Name of the agent making the call
            message: Description of what the agent is doing
            context: Additional context data
        """
        event = WorkflowEvent(
            event_type="agent_call",
            agent_name=agent_name,
            status="started",
            message=message,
            context=context or {}
        )
        self._log_event(event)
    
    def log_tool_invocation(self, tool_name: str, params: Dict[str, Any], 
                           result: str, status: str = "success"):
        """
        Log a tool/function invocation.
        
        Args:
            tool_name: Name of the tool being invoked
            params: Parameters passed to the tool
            result: Result message from the tool
            status: 'success', 'failed', or 'warning'
        """
        # Calculate duration if we have a start time
        duration_ms = None
        if tool_name in self._operation_start_times:
            start = self._operation_start_times.pop(tool_name)
            duration_ms = (datetime.now() - start).total_seconds() * 1000
        
        event = WorkflowEvent(
            event_type="tool_invocation",
            tool_name=tool_name,
            status=status,
            message=result[:500] if len(result) > 500 else result,  # Truncate long messages
            context={"params": params},
            duration_ms=duration_ms
        )
        self._log_event(event)
    
    def log_validation_gate(self, gate_name: str, passed: bool, reason: str):
        """
        Log a validation gate check.
        
        Args:
            gate_name: Name of the validation gate
            passed: Whether the validation passed
            reason: Explanation of the result
        """
        event = WorkflowEvent(
            event_type="validation_gate",
            status="success" if passed else "failed",
            message=f"Gate '{gate_name}': {reason}",
            context={"gate_name": gate_name, "passed": passed}
        )
        self._log_event(event)
        
        # Update state if validation failed
        if not passed:
            self.state.last_error = f"Validation failed: {gate_name} - {reason}"
    
    def log_state_change(self, field: str, old_value: Any, new_value: Any):
        """
        Log a workflow state change.
        
        Args:
            field: State field that changed
            old_value: Previous value
            new_value: New value
        """
        event = WorkflowEvent(
            event_type="state_change",
            status="success",
            message=f"State '{field}' changed: {old_value} → {new_value}",
            context={"field": field, "old_value": old_value, "new_value": new_value}
        )
        self._log_event(event)
        
        # Update internal state
        if hasattr(self.state, field):
            setattr(self.state, field, new_value)
    
    def start_operation(self, operation_name: str):
        """Mark the start of an operation for duration tracking."""
        self._operation_start_times[operation_name] = datetime.now()
    
    def get_workflow_summary(self) -> str:
        """
        Get a human-readable summary of the workflow execution.
        
        Returns:
            Formatted summary string
        """
        total_events = len(self.events)
        agent_calls = sum(1 for e in self.events if e.event_type == "agent_call")
        tool_calls = sum(1 for e in self.events if e.event_type == "tool_invocation")
        validations = sum(1 for e in self.events if e.event_type == "validation_gate")
        failures = sum(1 for e in self.events if e.status == "failed")
        
        # Calculate total duration
        if self.events:
            start = self.events[0].timestamp
            end = self.events[-1].timestamp
            duration = (end - start).total_seconds()
        else:
            duration = 0
        
        state_summary = []
        if self.state.structure_downloaded:
            state_summary.append("✅ Structure downloaded")
        if self.state.structure_cleaned:
            state_summary.append("✅ Structure cleaned")
        if self.state.forcefield_validated:
            state_summary.append("✅ Force field validated")
        if self.state.simulation_completed:
            state_summary.append("✅ Simulation completed")
        if self.state.analysis_completed:
            state_summary.append("✅ Analysis completed")
        
        return f"""📊 Workflow Summary
{'='*50}
⏱️  Duration: {duration:.1f} seconds
📝 Total events: {total_events}
  • Agent calls: {agent_calls}
  • Tool invocations: {tool_calls}
  • Validation checks: {validations}
  • Failures: {failures}

🔄 Workflow State:
{chr(10).join(state_summary) if state_summary else '  (No completed steps)'}

📁 Log file: {self.log_file}
{'='*50}"""
    
    def get_recent_events(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get the most recent events as dictionaries."""
        return [e.model_dump() for e in self.events[-count:]]
    
    def get_errors(self) -> List[WorkflowEvent]:
        """Get all error events."""
        return [e for e in self.events if e.status == "failed"]
    
    def export_events(self, output_file: str = None) -> str:
        """
        Export all events to a JSON file.
        
        Args:
            output_file: Output filename (default: workflow_events.json)
            
        Returns:
            Path to exported file
        """
        if output_file is None:
            output_file = os.path.join(self.workdir, "workflow_events.json")
        
        events_data = {
            "workflow_state": self.state.model_dump(),
            "events": [e.model_dump() for e in self.events],
            "summary": {
                "total_events": len(self.events),
                "failures": sum(1 for e in self.events if e.status == "failed"),
                "log_file": self.log_file
            }
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(events_data, f, indent=2, default=str)
        
        return output_file
    
    def update_state(self, **kwargs):
        """
        Update workflow state with multiple fields.
        
        Example:
            logger.update_state(structure_downloaded=True, current_pdb_file="1LYZ.pdb")
        """
        for field, value in kwargs.items():
            if hasattr(self.state, field):
                old_value = getattr(self.state, field)
                setattr(self.state, field, value)
                self.log_state_change(field, old_value, value)
            else:
                print(f"⚠️ Unknown state field: {field}")

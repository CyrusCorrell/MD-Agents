"""
SLURM Manager for HPC Job Submission

Manages OpenMM and WESTPA job submission to SLURM-based HPC clusters.
Handles SSH connections, file transfers, job submission, and status monitoring.
"""

import os
import subprocess
from typing import Tuple, Optional, List


class SLURMManager:
    """Manage OpenMM and WESTPA jobs on SLURM HPC clusters."""
    
    def __init__(self, workdir: str):
        self.workdir = workdir
        self.workflow_logger = None  # Set by AutoGenSystem
        
        # HPC configuration from environment
        self.hpc_host = os.getenv('HPC_HOST', 'localhost')
        self.hpc_username = os.getenv('HPC_USERNAME', os.getenv('USER', 'user'))
        self.ssh_key_path = os.getenv('HPC_SSH_KEY_PATH', os.path.expanduser('~/.ssh/id_rsa'))
        self.hpc_workdir = os.getenv('HPC_WORKDIR', f'/scratch/{self.hpc_username}/protein_md')
        self.partition = os.getenv('HPC_PARTITION', 'gpu')
        
        # Connection state
        self.ssh_client = None
        self.sftp_client = None
        self.connected = False
        
        # Job tracking
        self.submitted_jobs = {}
    
    def _log(self, message: str):
        """Log message if workflow logger is available."""
        if self.workflow_logger:
            self.workflow_logger.log_tool_invocation("SLURMManager", {}, message)
    
    def connect_to_hpc(self) -> str:
        """
        Establish SSH connection to HPC cluster.
        
        Returns:
            Status message
        """
        self._log(f"Connecting to HPC: {self.hpc_host}")
        
        try:
            import paramiko
        except ImportError:
            return "❌ Paramiko not installed. Run: pip install paramiko"
        
        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Connect using SSH key
            if os.path.exists(self.ssh_key_path):
                self.ssh_client.connect(
                    hostname=self.hpc_host,
                    username=self.hpc_username,
                    key_filename=self.ssh_key_path
                )
            else:
                # Fall back to password (will prompt if needed)
                self.ssh_client.connect(
                    hostname=self.hpc_host,
                    username=self.hpc_username
                )
            
            # Create SFTP client for file transfers
            self.sftp_client = self.ssh_client.open_sftp()
            
            # Create working directory on HPC
            stdin, stdout, stderr = self.ssh_client.exec_command(f"mkdir -p {self.hpc_workdir}")
            stdout.read()  # Wait for completion
            
            self.connected = True
            
            return f"""✅ Connected to HPC cluster:
  🖥️  Host: {self.hpc_host}
  👤 User: {self.hpc_username}
  📁 Work dir: {self.hpc_workdir}"""
            
        except Exception as e:
            self.connected = False
            return f"❌ HPC connection failed: {str(e)}"
    
    def disconnect(self) -> str:
        """Close SSH connection."""
        try:
            if self.sftp_client:
                self.sftp_client.close()
            if self.ssh_client:
                self.ssh_client.close()
            self.connected = False
            return "✅ Disconnected from HPC"
        except Exception as e:
            return f"⚠️ Disconnect warning: {str(e)}"
    
    def upload_files(self, local_files: List[str], remote_subdir: str = "") -> str:
        """
        Upload files to HPC cluster.
        
        Args:
            local_files: List of local file paths
            remote_subdir: Subdirectory on HPC (relative to hpc_workdir)
            
        Returns:
            Status message
        """
        if not self.connected:
            return "❌ Not connected to HPC. Call connect_to_hpc() first."
        
        self._log(f"Uploading {len(local_files)} files to HPC")
        
        remote_dir = os.path.join(self.hpc_workdir, remote_subdir) if remote_subdir else self.hpc_workdir
        
        try:
            # Create remote directory
            stdin, stdout, stderr = self.ssh_client.exec_command(f"mkdir -p {remote_dir}")
            stdout.read()
            
            uploaded = []
            failed = []
            
            for local_file in local_files:
                # Handle relative paths
                if not os.path.isabs(local_file):
                    local_path = os.path.join(self.workdir, local_file)
                else:
                    local_path = local_file
                
                if not os.path.exists(local_path):
                    failed.append(f"{local_file} (not found)")
                    continue
                
                filename = os.path.basename(local_path)
                remote_path = f"{remote_dir}/{filename}"
                
                try:
                    self.sftp_client.put(local_path, remote_path)
                    uploaded.append(filename)
                except Exception as e:
                    failed.append(f"{filename} ({str(e)})")
            
            result = f"✅ Upload completed:\n  📤 Uploaded: {len(uploaded)} files"
            if uploaded:
                result += f"\n  📁 Files: {', '.join(uploaded)}"
            if failed:
                result += f"\n  ❌ Failed: {', '.join(failed)}"
            
            return result
            
        except Exception as e:
            return f"❌ Upload failed: {str(e)}"
    
    def download_results(self, remote_files: List[str], remote_subdir: str = "",
                        local_subdir: str = "") -> str:
        """
        Download result files from HPC cluster.
        
        Args:
            remote_files: List of remote filenames (or wildcards)
            remote_subdir: Remote subdirectory
            local_subdir: Local subdirectory for downloads
            
        Returns:
            Status message
        """
        if not self.connected:
            return "❌ Not connected to HPC. Call connect_to_hpc() first."
        
        self._log(f"Downloading results from HPC")
        
        remote_dir = os.path.join(self.hpc_workdir, remote_subdir) if remote_subdir else self.hpc_workdir
        local_dir = os.path.join(self.workdir, local_subdir) if local_subdir else self.workdir
        
        os.makedirs(local_dir, exist_ok=True)
        
        try:
            downloaded = []
            failed = []
            
            for remote_file in remote_files:
                # Handle wildcards
                if '*' in remote_file:
                    stdin, stdout, stderr = self.ssh_client.exec_command(
                        f"ls {remote_dir}/{remote_file} 2>/dev/null"
                    )
                    matching_files = stdout.read().decode().strip().split('\n')
                    matching_files = [f for f in matching_files if f]
                else:
                    matching_files = [f"{remote_dir}/{remote_file}"]
                
                for remote_path in matching_files:
                    if not remote_path:
                        continue
                    filename = os.path.basename(remote_path)
                    local_path = os.path.join(local_dir, filename)
                    
                    try:
                        self.sftp_client.get(remote_path, local_path)
                        downloaded.append(filename)
                    except Exception as e:
                        failed.append(f"{filename} ({str(e)})")
            
            result = f"✅ Download completed:\n  📥 Downloaded: {len(downloaded)} files"
            if downloaded:
                result += f"\n  📁 Files: {', '.join(downloaded[:10])}"
                if len(downloaded) > 10:
                    result += f" ... and {len(downloaded) - 10} more"
            if failed:
                result += f"\n  ❌ Failed: {', '.join(failed)}"
            
            return result
            
        except Exception as e:
            return f"❌ Download failed: {str(e)}"
    
    def submit_openmm_job(self, pdb_file: str, script_name: str = "run_openmm.py",
                         nodes: int = 1, gpus_per_node: int = 1,
                         walltime: str = "24:00:00", job_name: str = None) -> Tuple[bool, str]:
        """
        Submit OpenMM simulation job to SLURM.
        
        Args:
            pdb_file: Input PDB file
            script_name: OpenMM Python script
            nodes: Number of compute nodes
            gpus_per_node: GPUs per node
            walltime: Wall time limit (HH:MM:SS)
            job_name: SLURM job name
            
        Returns:
            Tuple of (success, message)
        """
        if not self.connected:
            return False, "❌ Not connected to HPC. Call connect_to_hpc() first."
        
        if job_name is None:
            job_name = f"openmm_{os.path.splitext(pdb_file)[0]}"
        
        self._log(f"Submitting OpenMM job: {job_name}")
        
        slurm_script = f"""#!/bin/bash
#SBATCH --job-name={job_name}
#SBATCH --nodes={nodes}
#SBATCH --ntasks-per-node=1
#SBATCH --gres=gpu:{gpus_per_node}
#SBATCH --partition={self.partition}
#SBATCH --time={walltime}
#SBATCH --output=openmm_%j.out
#SBATCH --error=openmm_%j.err

# Load required modules (adjust for your HPC)
module load cuda/11.8 2>/dev/null || true
module load python/3.11 2>/dev/null || true

# Activate virtual environment if exists
if [ -f "$HOME/openmm_env/bin/activate" ]; then
    source $HOME/openmm_env/bin/activate
fi

# Change to working directory
cd {self.hpc_workdir}

# Run simulation
echo "Starting OpenMM simulation..."
python {script_name}

echo "OpenMM job completed: $(date)"
"""
        
        try:
            # Write SLURM script to HPC
            script_path = f"{self.hpc_workdir}/submit_openmm.sh"
            stdin, stdout, stderr = self.ssh_client.exec_command(
                f"cat > {script_path} << 'EOF'\n{slurm_script}\nEOF"
            )
            stdout.read()  # Wait for completion
            
            # Make script executable
            self.ssh_client.exec_command(f"chmod +x {script_path}")
            
            # Submit job
            stdin, stdout, stderr = self.ssh_client.exec_command(
                f"cd {self.hpc_workdir} && sbatch submit_openmm.sh"
            )
            
            output = stdout.read().decode()
            error = stderr.read().decode()
            
            if "Submitted batch job" in output:
                job_id = output.split()[-1]
                self.submitted_jobs[job_id] = {
                    'type': 'openmm',
                    'name': job_name,
                    'status': 'submitted'
                }
                return True, f"""✅ OpenMM job submitted to SLURM:
  🆔 Job ID: {job_id}
  📄 Job name: {job_name}
  🖥️  Nodes: {nodes}, GPUs: {gpus_per_node}
  ⏱️  Wall time: {walltime}
  📁 Work dir: {self.hpc_workdir}"""
            else:
                return False, f"❌ SLURM submission failed: {error or output}"
                
        except Exception as e:
            return False, f"❌ Job submission error: {str(e)}"
    
    def submit_westpa_job(self, iterations: int, walkers: int = 48,
                         walltime: str = "48:00:00") -> Tuple[bool, str]:
        """
        Submit WESTPA weighted ensemble job to SLURM.
        
        Args:
            iterations: Number of WE iterations
            walkers: Number of walkers (trajectories)
            walltime: Wall time limit
            
        Returns:
            Tuple of (success, message)
        """
        if not self.connected:
            return False, "❌ Not connected to HPC. Call connect_to_hpc() first."
        
        self._log(f"Submitting WESTPA job: {iterations} iterations, {walkers} walkers")
        
        # Calculate GPUs needed (one per walker, up to available)
        gpus = min(walkers, 8)  # Typically max 8 GPUs per node
        
        slurm_script = f"""#!/bin/bash
#SBATCH --job-name=westpa_we
#SBATCH --nodes=1
#SBATCH --ntasks={walkers}
#SBATCH --gres=gpu:{gpus}
#SBATCH --partition={self.partition}
#SBATCH --time={walltime}
#SBATCH --output=westpa_%j.out
#SBATCH --error=westpa_%j.err

# Load modules
module load cuda/11.8 2>/dev/null || true
module load python/3.11 2>/dev/null || true

# Activate WESTPA environment
if [ -f "$HOME/westpa_env/bin/activate" ]; then
    source $HOME/westpa_env/bin/activate
fi

cd {self.hpc_workdir}/westpa

# Initialize WESTPA (first time only)
if [ ! -d "west_data" ]; then
    echo "Initializing WESTPA..."
    ./init.sh
fi

# Run weighted ensemble
echo "Starting WESTPA simulation..."
w_run --max-iterations {iterations}

echo "WESTPA job completed: $(date)"
"""
        
        try:
            # Ensure westpa directory exists
            self.ssh_client.exec_command(f"mkdir -p {self.hpc_workdir}/westpa")
            
            # Write SLURM script
            script_path = f"{self.hpc_workdir}/westpa/submit_westpa.sh"
            stdin, stdout, stderr = self.ssh_client.exec_command(
                f"cat > {script_path} << 'EOF'\n{slurm_script}\nEOF"
            )
            stdout.read()
            
            # Submit job
            stdin, stdout, stderr = self.ssh_client.exec_command(
                f"cd {self.hpc_workdir}/westpa && sbatch submit_westpa.sh"
            )
            
            output = stdout.read().decode()
            error = stderr.read().decode()
            
            if "Submitted batch job" in output:
                job_id = output.split()[-1]
                self.submitted_jobs[job_id] = {
                    'type': 'westpa',
                    'iterations': iterations,
                    'status': 'submitted'
                }
                return True, f"""✅ WESTPA job submitted to SLURM:
  🆔 Job ID: {job_id}
  🔄 Iterations: {iterations}
  🚶 Walkers: {walkers}
  🖥️  GPUs: {gpus}
  ⏱️  Wall time: {walltime}"""
            else:
                return False, f"❌ WESTPA submission failed: {error or output}"
                
        except Exception as e:
            return False, f"❌ WESTPA job error: {str(e)}"
    
    def check_job_status(self, job_id: str) -> str:
        """
        Check status of a SLURM job.
        
        Args:
            job_id: SLURM job ID
            
        Returns:
            Status message
        """
        if not self.connected:
            return "❌ Not connected to HPC."
        
        try:
            # Check job status using squeue
            stdin, stdout, stderr = self.ssh_client.exec_command(
                f"squeue -j {job_id} -h -o '%T %M %L'"
            )
            output = stdout.read().decode().strip()
            
            if output:
                parts = output.split()
                status = parts[0] if len(parts) > 0 else "UNKNOWN"
                runtime = parts[1] if len(parts) > 1 else "N/A"
                remaining = parts[2] if len(parts) > 2 else "N/A"
                
                status_emoji = {
                    'PENDING': '⏳',
                    'RUNNING': '🔄',
                    'COMPLETING': '⏹️',
                    'COMPLETED': '✅',
                    'FAILED': '❌',
                    'CANCELLED': '🚫',
                    'TIMEOUT': '⏰'
                }
                
                emoji = status_emoji.get(status, '❓')
                
                return f"""{emoji} Job {job_id} Status:
  📊 State: {status}
  ⏱️  Runtime: {runtime}
  ⏳ Remaining: {remaining}"""
            else:
                # Job not in queue - check sacct for completed jobs
                stdin, stdout, stderr = self.ssh_client.exec_command(
                    f"sacct -j {job_id} -n -o State,Elapsed,ExitCode --parsable2"
                )
                sacct_output = stdout.read().decode().strip()
                
                if sacct_output:
                    lines = sacct_output.split('\n')
                    if lines:
                        parts = lines[0].split('|')
                        status = parts[0] if len(parts) > 0 else "UNKNOWN"
                        elapsed = parts[1] if len(parts) > 1 else "N/A"
                        exit_code = parts[2] if len(parts) > 2 else "N/A"
                        
                        if job_id in self.submitted_jobs:
                            self.submitted_jobs[job_id]['status'] = status
                        
                        return f"""Job {job_id} completed:
  📊 Final state: {status}
  ⏱️  Total runtime: {elapsed}
  🔢 Exit code: {exit_code}"""
                
                return f"❓ Job {job_id} not found in queue or history"
                
        except Exception as e:
            return f"❌ Status check failed: {str(e)}"
    
    def cancel_job(self, job_id: str) -> str:
        """Cancel a SLURM job."""
        if not self.connected:
            return "❌ Not connected to HPC."
        
        try:
            stdin, stdout, stderr = self.ssh_client.exec_command(f"scancel {job_id}")
            error = stderr.read().decode()
            
            if error:
                return f"❌ Cancel failed: {error}"
            
            if job_id in self.submitted_jobs:
                self.submitted_jobs[job_id]['status'] = 'cancelled'
            
            return f"✅ Job {job_id} cancelled"
            
        except Exception as e:
            return f"❌ Cancel error: {str(e)}"
    
    def list_jobs(self) -> str:
        """List all user's jobs in SLURM queue."""
        if not self.connected:
            return "❌ Not connected to HPC."
        
        try:
            stdin, stdout, stderr = self.ssh_client.exec_command(
                f"squeue -u {self.hpc_username} -o '%.10i %.20j %.8T %.10M %.9l %.6D %R'"
            )
            output = stdout.read().decode()
            
            if output.strip():
                return f"📋 Jobs for {self.hpc_username}:\n{output}"
            else:
                return "📋 No jobs currently in queue"
                
        except Exception as e:
            return f"❌ List jobs failed: {str(e)}"
    
    def get_cluster_info(self) -> str:
        """Get HPC cluster information."""
        if not self.connected:
            return "❌ Not connected to HPC."
        
        try:
            # Get partition info
            stdin, stdout, stderr = self.ssh_client.exec_command(
                "sinfo -o '%P %.5a %.10l %.6D %.6t %N'"
            )
            partition_info = stdout.read().decode()
            
            # Get GPU info if available
            stdin, stdout, stderr = self.ssh_client.exec_command(
                "sinfo -o '%P %G' | head -10"
            )
            gpu_info = stdout.read().decode()
            
            return f"""🖥️  HPC Cluster Information:
  
📊 Partitions:
{partition_info}

🎮 GPU Resources:
{gpu_info}"""
            
        except Exception as e:
            return f"❌ Cluster info failed: {str(e)}"

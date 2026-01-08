# Ollama Local Model Guide

Run the Protein MD Agents framework entirely locally using [Ollama](https://ollama.com/) for LLM inference.

## Overview

Ollama enables running open-source LLMs locally without cloud API dependencies. This guide covers model selection, performance optimization, and troubleshooting for the multi-agent simulation system.

## Installation

### Linux / WSL

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### macOS

```bash
brew install ollama
```

### Windows

Download the installer from https://ollama.com/download

### Verify Installation

```bash
ollama --version
ollama serve  # Start the server
```

## Model Selection Strategy

The framework supports three Ollama size tiers, each optimized for different agent roles:

### Small Models (7B-8B) - `ollama_small`

**Best for:** Fast tasks, simple structure queries, validation checks

| Model | Command | Size | Context Window |
|-------|---------|------|----------------|
| Llama 3.1 8B | `ollama pull llama3.1:8b` | 4.7 GB | 128K |
| Mistral 7B | `ollama pull mistral:7b` | 4.1 GB | 32K |
| Qwen 2.5 7B | `ollama pull qwen2.5:7b` | 4.4 GB | 128K |

**Recommended agents:**
- StructureCreator (downloading PDB files, basic validation)
- FileManager (file operations)
- Basic validation tasks

### Medium Models (13B-20B) - `ollama_medium`

**Best for:** Coordination tasks, general reasoning, balanced performance

| Model | Command | Size | Context Window |
|-------|---------|------|----------------|
| Llama 3.1 (default) | `ollama pull llama3.1:latest` | 8.0 GB | 128K |
| Mixtral 8x7B | `ollama pull mixtral:8x7b` | 26 GB | 32K |
| Qwen 2.5 14B | `ollama pull qwen2.5:14b` | 8.9 GB | 128K |

**Recommended agents:**
- LAMMPSAdmin (coordinator)
- ForceFieldManager
- SimulationManager

### Large Models (70B+) - `ollama_large`

**Best for:** Complex reasoning, simulation planning, code generation

| Model | Command | Size | Context Window |
|-------|---------|------|----------------|
| Llama 3.1 70B | `ollama pull llama3.1:70b` | 40 GB | 128K |
| Qwen 2.5 72B | `ollama pull qwen2.5:72b` | 41 GB | 128K |

**Recommended agents:**
- SimulationReviewer (complex validation)
- ResultsAnalyzer (data analysis)
- WESTPAManager (advanced workflows)

## Performance Benchmarks

### Hardware Requirements

| Model Size | Minimum VRAM | Recommended VRAM | RAM (CPU fallback) |
|------------|--------------|------------------|-------------------|
| 7B-8B | 6 GB | 8 GB | 16 GB |
| 13B-20B | 10 GB | 16 GB | 32 GB |
| 70B+ | 40 GB | 48+ GB | 64+ GB |

### Inference Speed (tokens/second)

*Tested on NVIDIA RTX 4090 (24GB VRAM)*

| Model | Q4_K_M | Q8_0 | FP16 |
|-------|--------|------|------|
| Llama 3.1 8B | 80-100 | 50-70 | 30-40 |
| Llama 3.1 70B | 15-25 | 8-12 | N/A* |
| Mixtral 8x7B | 25-35 | 15-20 | N/A* |

*FP16 requires more VRAM than available on consumer GPUs

### CPU Inference (Apple M2 Max)

| Model | Tokens/sec |
|-------|------------|
| Llama 3.1 8B | 25-35 |
| Llama 3.1 70B | 3-5 |

## Quantization Options

Ollama uses quantization to reduce model size and increase speed. Common options:

### Q4_K_M (Default)
- **Size reduction:** ~75%
- **Quality:** Good for most tasks
- **Speed:** Fastest
- **Use when:** Running on consumer hardware

### Q8_0
- **Size reduction:** ~50%
- **Quality:** Near-original performance
- **Speed:** Moderate
- **Use when:** You have extra VRAM and need better quality

### Pulling Specific Quantizations

```bash
# Default (Q4_K_M)
ollama pull llama3.1:8b

# Specific quantization
ollama pull llama3.1:8b-instruct-q8_0
```

## Configuration

### Environment Variables

Set in your `.env` file:

```env
# Ollama server URL (default: http://localhost:11434/v1)
OLLAMA_BASE_URL=http://localhost:11434/v1

# API key (default: "ollama", only needed for custom deployments)
OLLAMA_API_KEY=ollama

# Model selection per size tier
OLLAMA_MODEL_SMALL=llama3.1:8b
OLLAMA_MODEL_MEDIUM=llama3.1:latest
OLLAMA_MODEL_LARGE=llama3.1:70b
```

### Remote Ollama Server

For distributed setups or running Ollama on a separate machine:

```env
# Remote server
OLLAMA_BASE_URL=http://192.168.1.100:11434/v1

# If using authentication proxy
OLLAMA_API_KEY=your-custom-key
```

### Ollama Server Configuration

Create `~/.ollama/config.json` for advanced settings:

```json
{
  "gpu_layers": 35,
  "num_thread": 8,
  "num_ctx": 8192
}
```

## Usage Examples

### Basic Usage

```python
from protein_agents import AutoGenSystem

# Initialize with medium Ollama model
system = AutoGenSystem(llm_type="ollama_medium")

initial_message = """
Download ubiquitin (PDB ID: 1UBQ) and validate its structure.
"""

system.run_workflow(initial_message)
```

### Multi-Model Strategy (Future Feature)

> **Note:** This is a planned feature. Currently, all agents use the same model.

In future versions, you may be able to assign different models to different agents:

```python
# Planned API (not yet implemented)
system = AutoGenSystem(
    coordinator_model="ollama_medium",
    reasoning_model="ollama_large", 
    fast_model="ollama_small"
)
```

## Troubleshooting

### Connection Refused

**Error:** `Connection refused at http://localhost:11434`

**Solutions:**
1. Ensure Ollama server is running:
   ```bash
   ollama serve
   ```
2. Check if port 11434 is available:
   ```bash
   lsof -i :11434  # Linux/macOS
   netstat -ano | findstr :11434  # Windows
   ```
3. Try explicit host binding:
   ```bash
   OLLAMA_HOST=0.0.0.0:11434 ollama serve
   ```

### Out of Memory (OOM)

**Error:** `CUDA out of memory` or `Failed to allocate memory`

**Solutions:**
1. Use a smaller model:
   ```bash
   ollama pull llama3.1:8b  # Instead of 70b
   ```
2. Use higher quantization:
   ```bash
   ollama pull llama3.1:8b-instruct-q4_K_M
   ```
3. Reduce context window in Ollama:
   ```bash
   ollama run llama3.1:8b --num-ctx 4096
   ```
4. Enable CPU offloading (slower but works):
   ```bash
   OLLAMA_GPU_LAYERS=20 ollama serve
   ```

### Slow Inference

**Symptoms:** Tokens/sec below expected benchmarks

**Solutions:**
1. Ensure GPU is being used:
   ```bash
   nvidia-smi  # Check GPU utilization
   ```
2. Check for memory pressure:
   ```bash
   free -h  # Linux
   ```
3. Use smaller quantization:
   ```bash
   ollama pull llama3.1:8b-instruct-q4_K_M
   ```
4. Close other GPU applications

### Model Not Found

**Error:** `model 'xyz' not found`

**Solutions:**
1. Pull the model first:
   ```bash
   ollama pull llama3.1:8b
   ```
2. List available models:
   ```bash
   ollama list
   ```
3. Check model name spelling in `.env`

### WebSurfer Agent Issues

The WebSurfer agent may require cloud APIs for optimal performance. If using local models exclusively:

1. WebSurfer might have reduced capabilities
2. Consider disabling WebSurfer for fully local workflows
3. Use manual PDB downloads instead of web searches

## Best Practices

### 1. Pre-pull Models Before Running

```bash
# Pull all models you might need
ollama pull llama3.1:8b
ollama pull llama3.1:latest
```

### 2. Monitor Resource Usage

```bash
# Watch GPU memory
watch -n 1 nvidia-smi

# Watch Ollama logs
journalctl -u ollama -f  # Linux systemd
```

### 3. Use Appropriate Model Sizes

- Start with `ollama_small` for testing
- Use `ollama_medium` for production workflows
- Reserve `ollama_large` for complex reasoning tasks

### 4. Consider Hybrid Mode (Future)

For cost-sensitive production use, consider:
- Local Ollama for simple tasks (free)
- Cloud API for complex reasoning (paid per token)

## Model Recommendations by Task

| Task | Recommended Config |
|------|-------------------|
| Quick structure downloads | `ollama_small` |
| General simulation setup | `ollama_medium` |
| Complex WESTPA workflows | `ollama_large` or cloud API |
| Trajectory analysis | `ollama_medium` |
| Force field validation | `ollama_medium` |
| Code generation | `ollama_large` |

## Further Resources

- [Ollama Documentation](https://github.com/ollama/ollama/blob/main/docs/README.md)
- [Model Library](https://ollama.com/library)
- [AutoGen with Local Models](https://microsoft.github.io/autogen/docs/topics/non-openai-models/local-lm-studio)
- [GPU Compatibility](https://github.com/ollama/ollama/blob/main/docs/gpu.md)

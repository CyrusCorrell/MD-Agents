Plan: Ollama Local Model Integration
Integrate Ollama support for local LLM inference, allowing the protein MD multiagent system to run without cloud API dependencies.

Steps
Extend src/tools/llm_config.py with Ollama configurations

Add 3 Ollama config entries to get_llm_config() dictionary: ollama_small (7B-8B models), ollama_medium (13B-20B), ollama_large (70B+)
Each config needs base_url: "http://localhost:11434/v1", api_key: "ollama", and model name from Ollama library
Add optional environment variables OLLAMA_BASE_URL and OLLAMA_API_KEY for custom deployments
Update QUICKSTART.md with Ollama setup section

Add "Local Inference with Ollama" section after API Keys configuration
Include Ollama installation command (curl -fsSL https://ollama.com/install.sh | sh)
Document model pulling (ollama pull llama3.1, ollama pull mistral)
Add example usage: system = AutoGenSystem(llm_type="ollama_medium")
Note context window and performance considerations for local models
Create .env_example entry for Ollama configuration

Add commented Ollama configuration block with OLLAMA_BASE_URL and OLLAMA_MODEL
Include examples for common models (llama3.1:8b, mistral:7b, qwen2.5:7b)
Test agent compatibility with Ollama backend

Verify ConversableAgent initialization with base_url parameter works with AutoGen 0.4.0.dev6
Test WebSurfer agent (currently hardcoded to gpt-4.1) - may need conditional override
Test GroupChatManager orchestration with local inference latency
Document model selection strategy in new docs/ollama-guide.md

Create model sizing recommendations: fast agents (8B), reasoning agents (70B), coordinator (13B+)
Add benchmark table: tokens/sec, context window, VRAM requirements
Include troubleshooting: connection refused, slow inference, out-of-memory errors
Further Considerations
Multi-model deployment - Should we support different Ollama models per agent? e.g., StructureCreator uses fast 8B model, SimulationManager uses reasoning-heavy 70B model
Hybrid mode - Allow mixing cloud APIs (GPT-4 for complex reasoning) with local Ollama (simple tasks) to optimize cost vs performance?
Quantization options - Document Q4_K_M vs Q8 quantization trade-offs for users with limited VRAM
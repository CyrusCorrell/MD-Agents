import os
from pathlib import Path
from typing import Dict, Any

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception as e:
    print(f"Could not load .env automatically: {e}")


def _get_ollama_base_url() -> str:
    """Get Ollama base URL from environment or use default."""
    return os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")


def _get_ollama_api_key() -> str:
    """Get Ollama API key from environment or use default."""
    return os.getenv("OLLAMA_API_KEY", "ollama")


def get_llm_config(llm_type: str) -> Dict[str, Any]:
    """
    Get LLM configuration based on the selected model type.    
    Args:
        llm_type (str): Type of LLM to use ('gpt4', 'claude', 'ollama_small', etc.)        
    Returns:
        dict: LLM configuration dictionary
    """
    llm_configs = {
        'gpt4o-mini': {
            "model": "gpt-4o-mini",
            'api_key': os.getenv("OPENAI_API_KEY"), 
            'temperature':0,
            "cache_seed": 0,
        },
        'gpt-4.1': {
            "model": "gpt-4.1",
            'api_key': os.getenv("OPENAI_API_KEY"), 
            'temperature':0,
            "cache_seed": 0,
        },
        'gpt4o': {
            "model": "gpt-4o",
            'api_key': os.getenv("OPENAI_API_KEY"), 
            'temperature':0,
           # "cache_seed": 0,
        },
        'o3-mini': {
            "model": "o3-mini",
            'api_key': os.getenv("OPENAI_API_KEY"),
            #'temperature':0,
           # "cache_seed": 0,
        },

        'claude_35': {
            "model": "claude-3-5-sonnet-20240620",
            'api_key': os.getenv("anthropic_api_key"),
            'api_type': 'anthropic',
            'temperature':0,
            "cache_seed": 0,
   
        },

        'ArgoLLMs': {  # Local client operates only within the organization
            "model": "gpto1preview",
            "model_client_cls": "ArgoModelClient",
            'temperature': 0,
            "cache_seed": 0,
        },

        # Ollama Local Models - Small (7B-8B parameters)
        # Good for: Fast responses, simple tasks, structure creation
        # Models: llama3.1:8b, mistral:7b, qwen2.5:7b
        'ollama_small': {
            "model": os.getenv("OLLAMA_MODEL_SMALL", "llama3.1:8b"),
            "api_key": _get_ollama_api_key(),
            "base_url": _get_ollama_base_url(),
            "temperature": 0,
            "cache_seed": 0,
        },

        # Ollama Local Models - Medium (13B-20B parameters)
        # Good for: Balanced performance, coordination tasks, general reasoning
        # Models: llama3.1:13b, mixtral:8x7b, qwen2.5:14b
        'ollama_medium': {
            "model": os.getenv("OLLAMA_MODEL_MEDIUM", "llama3.1:latest"),
            "api_key": _get_ollama_api_key(),
            "base_url": _get_ollama_base_url(),
            "temperature": 0,
            "cache_seed": 0,
        },

        # Ollama Local Models - Large (70B+ parameters)
        # Good for: Complex reasoning, simulation planning, code generation
        # Models: llama3.1:70b, qwen2.5:72b
        'ollama_large': {
            "model": os.getenv("OLLAMA_MODEL_LARGE", "llama3.1:70b"),
            "api_key": _get_ollama_api_key(),
            "base_url": _get_ollama_base_url(),
            "temperature": 0,
            "cache_seed": 0,
        },
    }
    
    return llm_configs.get(llm_type, llm_configs['ArgoLLMs'])
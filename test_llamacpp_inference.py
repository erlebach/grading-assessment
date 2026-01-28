#!/usr/bin/env python3
"""Quick diagnostic test for llama.cpp inference."""

import sys
import time
from config.llm_config import configure_llm, load_env_config

def test_llamacpp():
    """Test llama.cpp model loading and inference."""
    print("=" * 60)
    print("Testing llama.cpp configuration and inference")
    print("=" * 60)

    # Load config
    print("\n1. Loading configuration...")
    config = load_env_config()
    print(f"   Model path: {config['llamacpp_model_path']}")
    print(f"   Context size: {config['llamacpp_n_ctx']}")
    print(f"   GPU layers: {config['llamacpp_n_gpu_layers']}")
    print(f"   Temperature: {config['llamacpp_temperature']}")
    print(f"   Max tokens: {config['llamacpp_max_tokens']}")

    # Initialize LLM
    print("\n2. Initializing llama.cpp model...")
    print("   (This may take 30-60 seconds for a 20B model)")
    start_time = time.time()

    try:
        llm = configure_llm("llamacpp")
        load_time = time.time() - start_time
        print(f"   ✓ Model loaded in {load_time:.2f} seconds")
    except Exception as e:
        print(f"   ✗ Error loading model: {e}")
        return False

    # Test simple inference
    print("\n3. Testing simple inference...")
    test_prompt = "What is 2+2? Answer briefly:"
    print(f"   Prompt: {test_prompt}")
    print("   Generating response...")

    start_time = time.time()
    try:
        response = llm.complete(test_prompt)
        inference_time = time.time() - start_time
        print(f"   ✓ Response generated in {inference_time:.2f} seconds")
        print(f"   Response: {response.text[:200]}")
    except Exception as e:
        print(f"   ✗ Error during inference: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 60)
    print("✓ llama.cpp is working correctly!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_llamacpp()
    sys.exit(0 if success else 1)

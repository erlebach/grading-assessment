#!/usr/bin/env python3
"""Minimal llama.cpp test to isolate the crash."""

import sys

# Test 1: Can we import llama_cpp?
print("Test 1: Importing llama_cpp...")
try:
    from llama_cpp import Llama
    print("✓ Import successful")
except Exception as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

# Test 2: Can we initialize with minimal parameters?
print("\nTest 2: Initializing with minimal parameters...")
model_path = "/Users/erlebach/data/llm_models/gpt-oss-20b-Q4_K_M.gguf"

try:
    print(f"  Model path: {model_path}")
    print("  Parameters: n_ctx=512, n_gpu_layers=0, verbose=True")
    llm = Llama(
        model_path=model_path,
        n_ctx=512,  # Very small context to reduce memory
        n_gpu_layers=0,  # CPU only
        verbose=True,
    )
    print("✓ Model loaded successfully!")
except Exception as e:
    print(f"✗ Model loading failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Can we generate?
print("\nTest 3: Generating text...")
try:
    output = llm("What is 2+2?", max_tokens=10)
    print(f"✓ Generated: {output}")
except Exception as e:
    print(f"✗ Generation failed: {e}")
    sys.exit(1)

print("\n✓✓✓ All tests passed!")

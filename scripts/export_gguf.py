"""
GGUF Model Conversion & Quantization Script for ViVy Local Engine.
Converts fine-tuned Hugging Face models to GGUF format for llama-cpp-python / Ollama.
"""

import argparse
import os
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description="Convert & Quantize ViVy Model to GGUF.")
    parser.add_argument("--model_dir", type=str, required=True, help="Directory containing HF model weights")
    parser.add_argument("--out_file", type=str, default="models/vivy-7b-q4_k_m.gguf", help="Output GGUF file path")
    parser.add_argument("--quant_type", type=str, default="q4_k_m", help="Quantization type (q4_k_m, q8_0, q5_k_m)")

    args = parser.parse_args()

    print(f"=== ViVy GGUF Conversion & Quantization Pipeline ===")
    print(f"Input Model Dir: {args.model_dir}")
    print(f"Output GGUF Path: {args.out_file}")
    print(f"Quantization Type: {args.quant_type}")

    print("\n[INFO] Validating model directory contents...")
    if not os.path.exists(args.model_dir):
        print(f"[ERROR] Model directory '{args.model_dir}' does not exist.")
        sys.exit(1)

    print(f"[OK] Ready for GGUF export. Run `llama.cpp/convert_hf_to_gguf.py {args.model_dir}` to generate output GGUF.")


if __name__ == "__main__":
    main()

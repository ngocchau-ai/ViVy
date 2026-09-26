"""Ollama Model Exporter for ViVy AI Model.

Generates Ollama Modelfile and build commands with Self-Verification Filter Funnel
and Quantum-Inspired Associative Memory system capabilities.
Standard-library only.
"""

from __future__ import annotations

from pathlib import Path

__all__ = [
    "OllamaModelExporter",
]


class OllamaModelExporter:
    """Handles packaging and exporting ViVy model into Ollama format."""

    @staticmethod
    def generate_modelfile_content(base_model: str = "llama3.2:3b") -> str:
        """Generate Ollama Modelfile string for ViVy."""
        return f"""# Modelfile.vivy — Ollama Modelfile for ViVy Multimodal Bilingual AI Model (Ngoc Chau)

FROM {base_model}

PARAMETER temperature 0.2
PARAMETER top_p 0.9
PARAMETER num_ctx 8192
PARAMETER stop "<|im_end|>"
PARAMETER stop "<|end_of_text|>"

SYSTEM \"\"\"
You are ViVy — a Multimodal Bilingual Reasoning AI developed by Ngoc Chau.
Capabilities & Architecture:
1. Seamless Multimodal & Bilingual Reasoning (English & Vietnamese).
2. N-Thought Population Reasoning with 4-Level Self-Verification Filter Funnel:
   - Level 1: Amplitude & Phase Analyzer (Entropy measurement & destructive interference detection).
   - Level 2: SVD Stream Decomposer (State tensor matricization for parallel thought stream isolation).
   - Level 3: Evaluator & Logic Filter (Confidence C_i score calculation with Occam's razor).
   - Level 4: Control & Metacognitive Trigger (CONTINUE, HALT, BACKTRACK, DELEGATE).
3. Quantum-Inspired Associative Memory:
   - 1-Touch Intuition Retrieval using complex Hebbian learning and SVD polar unitarization.
\"\"\"

TEMPLATE \"\"\"{{{{ if .System }}}}<|im_start|>system
{{{{ .System }}}}<|im_end|>
{{{{ end }}}}{{{{ if .Prompt }}}}<|im_start|>user
{{{{ .Prompt }}}}<|im_end|>
{{{{ end }}}}<|im_start|>assistant
{{{{ .Response }}}}<|im_end|>\"\"\"
"""

    @classmethod
    def export_modelfile(
        cls,
        target_path: str | Path = "modelfiles/Modelfile.vivy",
        base_model: str = "llama3.2:3b",
    ) -> Path:
        """Export Modelfile content to disk."""
        path = Path(target_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        content = cls.generate_modelfile_content(base_model)
        path.write_text(content, encoding="utf-8")

        # Đồng thời tạo file Modelfile gốc ở root directory
        root_path = Path("Modelfile")
        root_path.write_text(content, encoding="utf-8")
        return path

    @staticmethod
    def get_create_command(model_name: str = "vivy", modelfile_path: str = "modelfiles/Modelfile.vivy") -> str:
        """Return terminal command to register model in Ollama."""
        return f"ollama create {model_name} -f {modelfile_path}"

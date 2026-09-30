# ViVy 1 (Legacy) - Local Codegraph

```json
{
  "module": "ViVy1",
  "status": "isolated_legacy",
  "files": [
    {
      "path": "modelfiles/Modelfile.vivy",
      "type": "ollama_modelfile",
      "base_model": "llama3.2:3b",
      "description": "Original Modelfile for ViVy reasoning model."
    },
    {
      "path": "modelfiles/Modelfile.vivy-4b",
      "type": "ollama_modelfile",
      "base_model": "llama3.2:3b",
      "description": "Distilled ViVy 4B Modelfile."
    },
    {
      "path": "modelfiles/Modelfile.learning_data",
      "type": "text",
      "description": "Deprecation notice explaining transition to PyTorch ViVy Core."
    },
    {
      "path": "scripts/compress_vivy_40b_to_4b.py",
      "type": "python_script",
      "description": "Distillation pipeline from 40B MoE to 4B."
    },
    {
      "path": "scripts/package_vivy_ollama.py",
      "type": "python_script",
      "description": "Packaging script for exporting Modelfile.vivy."
    }
  ]
}
```

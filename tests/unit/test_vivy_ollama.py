"""Unit tests for ViVy Ollama integration and packaging."""

from __future__ import annotations

from pathlib import Path

from nps_core.vivy_ollama import (
    OllamaModelExporter,
    OllamaViVyBridgeServer,
    OllamaViVyClient,
)


def test_ollama_model_exporter(tmp_path: Path) -> None:
    modelfile_path = tmp_path / "Modelfile.vivy"
    saved = OllamaModelExporter.export_modelfile(modelfile_path)

    assert saved.exists()
    content = saved.read_text(encoding="utf-8")
    assert "FROM llama3.2:3b" in content
    assert "SYSTEM" in content
    assert "ViVy" in content

    cmd = OllamaModelExporter.get_create_command("vivy", str(saved))
    assert cmd == f"ollama create vivy -f {saved}"


def test_ollama_client_payload() -> None:
    client = OllamaViVyClient(model_name="vivy:latest")
    payload = client.format_chat_payload("Chào ViVy!")

    assert payload["model"] == "vivy:latest"
    assert payload["messages"][0]["content"] == "Chào ViVy!"

    reasoning_res = client.process_local_reasoning("Chào ViVy!")
    assert reasoning_res["model"] == "vivy:latest"
    assert reasoning_res["message"]["role"] == "assistant"
    assert reasoning_res["done"] is True
    assert "ViVy" in reasoning_res["message"]["content"]


def test_ollama_bridge_server_init() -> None:
    server = OllamaViVyBridgeServer(port=18434)
    server.start_in_background()
    assert server.server is not None
    server.close()
    assert server.server is None

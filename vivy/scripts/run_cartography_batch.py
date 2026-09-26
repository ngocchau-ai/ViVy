"""
Batch Knowledge Cartographer for existing models in the workspace.
Scans models, builds CoarseKnowledgeAtlas, and exports .catlas files.

[ISOLATED 26/09/2026] GIỮ LÀM TÀI LIỆU SO SÁNH / THAM KHẢO — CẢ 3 PATH DƯỚI ĐÂY ĐỀU SAI.
  - `models_to_scan[0]` → `D:\\Vivy1\\artifacts\\kaggle_gemma\\...` : path cũ.
    Bản thật: `D:\\models\\gemma4-e4b\\vivy-gemma-e4b-q4km.gguf`.
  - `models_to_scan[1]` → `qwen2.5-coder-7b-instruct-q4_k_m.gguf` : KHÔNG tồn tại,
    user chỉ thị gỡ tham chiếu 26/09/2026 (kéo theo xóa 2 runtime qwen_coder).
  - `models_to_scan[2]` → `vivy2.gguf` : đã giải phóng NVMe 21/09/2026.
  - `ws / "atlases"` : sau reorg D2/D5 atlas sống ở `cautreo/atlases/`, không phải `vivy/atlases/`.
Giữ nguyên để đối chiếu cách build CoarseKnowledgeAtlas. Nguồn sự thật về trọng số:
`models/model_manifest.json` (`full_path`) + `MODEL_ROOT = D:\\models`.
"""

import sys
from pathlib import Path

# Ensure paths
ws = Path(__file__).resolve().parents[1]
if str(ws) not in sys.path:
    sys.path.insert(0, str(ws))

from integration.cautreo_cartographer import CautreoCartographer  # noqa: E402


def main():
    atlas_dir = ws / "atlases"
    atlas_dir.mkdir(parents=True, exist_ok=True)

    cartographer = CautreoCartographer(ram_ratio=0.10)
    print("=" * 60)
    print("  CAUTREO KNOWLEDGE CARTOGRAPHY BATCH SCANNER")
    print(f"  RAM Buffer Limit (10%): {cartographer.max_buffer_bytes / (1024*1024):.1f} MB")
    print("=" * 60)

    models_to_scan = [
        ("gemma4-e4b", 48, r"D:\Vivy1\artifacts\kaggle_gemma\vivy-gemma-e4b-q4km.gguf"),
        ("qwen2.5-coder-7b", 28, r"D:\91s_Vivy\Vivy_final\models\qwen2.5-coder-7b-instruct-q4_k_m.gguf"),
        ("vivy2", 24, r"D:\91s_Vivy\Vivy_final\models\vivy2.gguf"),
    ]

    for model_id, layers, path in models_to_scan:
        print(f"\n[*] Scanning Knowledge Cartography for: {model_id} ({layers} layers)...")
        atlas = cartographer.scan_model(model_id, total_layers=layers, model_path=path)
        out_catlas = atlas_dir / f"{model_id}.catlas"
        ok = atlas.export_catlas(str(out_catlas))
        if ok:
            sz_kb = out_catlas.stat().st_size / 1024
            print(f"  [SUCCESS] Exported: {out_catlas.name} ({sz_kb:.1f} KB)")
            print(atlas.render_ascii_continents())
        else:
            print(f"  [FAILED] Failed to export atlas for {model_id}")

    print("\n" + "=" * 60)
    print(f"  All atlases preserved in: {atlas_dir}")
    print("=" * 60)

if __name__ == "__main__":
    main()

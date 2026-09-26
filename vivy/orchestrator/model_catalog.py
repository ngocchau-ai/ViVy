"""model_catalog.py — Autonomous Local Model Discovery & Capability Tagging.

Triển khai cơ chế quét kho mô hình (models/), nhận diện năng lực và gán nhãn
cho ViVy (Lõi nhận thức Gemma 4EB) khi khởi động, giúp ViVy:
1. Thoát khỏi tình trạng "mù danh mục" (Model Catalog Blindness).
2. Tự động nhận diện N nhiệm vụ cơ bản thông qua bộ tín hiệu quy chuẩn (Task Archetypes).
3. Phân rã input phức tạp thành các sub-task và chỉ định model chuyên môn phù hợp.

Changelog:
    21/09/2026 (Antigravity IDE): Initial implementation per CEO Directive & User Request.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# N Foundational Task Archetypes (Bộ tín hiệu quy chuẩn N nhiệm vụ)
# ---------------------------------------------------------------------------


class TaskArchetype(StrEnum):
    """N Nhiệm vụ cơ bản của hệ sinh thái ViVy & Cautreo."""

    ARCH_SPEC_AND_PLAN = "ARCH_SPEC_AND_PLAN"          # Quy hoạch kiến trúc, lập plan, phân rã bài toán
    NATIVE_SYSTEM_CODING = "NATIVE_SYSTEM_CODING"      # C/C++ native, C-ABI pointers, ctypes DLL bindings
    REFACTOR_AND_TESTING = "REFACTOR_AND_TESTING"      # Tái cấu trúc mã nguồn, unit test pytest, bugfix
    KNOWLEDGE_FORAGING = "KNOWLEDGE_FORAGING"          # Thu thập tài liệu, tìm kiếm web, đọc spec ngoài
    DYNAMIC_ORCHESTRATION_QA = "DYNAMIC_ORCHESTRATION_QA"  # Chấm điểm rubric, thẩm định 4 trục, Dream Engine
    FAST_DATA_PARSING = "FAST_DATA_PARSING"            # Bóc tách JSON, xử lý chuỗi tốc độ cao
    MULTIMODAL_IMAGE_REASONING = "MULTIMODAL_IMAGE_REASONING"  # Phân tích thị giác, biểu đồ trading, ảnh y khoa/tài liệu
    DESKTOP_GUI_VISION = "DESKTOP_GUI_VISION"          # Quan sát desktop màn hình CUA, định vị button/input/ cửa sổ


# Bảng ánh xạ tín hiệu (Signals) cho từng Archetype
ARCHETYPE_SIGNALS: dict[TaskArchetype, list[str]] = {
    TaskArchetype.ARCH_SPEC_AND_PLAN: [
        "[TASK: ARCH]",
        "[TASK: PLAN]",
        "ARCHITECTURE",
        "KIẾN TRÚC",
        "THIẾT KẾ HỆ THỐNG",
        "PHÂN RÃ BÀI TOÁN",
    ],
    TaskArchetype.NATIVE_SYSTEM_CODING: [
        "[TASK: C_ABI]",
        "[TASK: LOWLEVEL]",
        "[SPECIALIST_REQUEST: CODING]",
        "C-ABI",
        "CTYPES",
        "CAUTREO.DLL",
        "MALLOC",
        "POINTER",
        "MAKEFILE",
        "HEADER C",
    ],
    TaskArchetype.REFACTOR_AND_TESTING: [
        "[TASK: REFACTOR]",
        "[TASK: TEST]",
        "PYTEST",
        "UNIT TEST",
        "TÁI CẤU TRÚC",
        "REFUCTOR",
        "BUGFIX",
    ],
    TaskArchetype.KNOWLEDGE_FORAGING: [
        "[TASK: FORAGE]",
        "[TASK: DOCS]",
        "SEARCH",
        "FORAGE",
        "TÌM KIẾM",
        "TÀI LIỆU NGOÀI",
    ],
    TaskArchetype.DYNAMIC_ORCHESTRATION_QA: [
        "[TASK: QA]",
        "[TASK: AUDIT]",
        "CHẤM ĐIỂM",
        "RUBRIC",
        "SCORE GRAPH",
        "DREAM ENGINE",
        "INVARIANT CHECK",
    ],
    TaskArchetype.FAST_DATA_PARSING: [
        "[TASK: PARSE]",
        "[TASK: FAST]",
        "PARSE JSON",
        "TRÍCH XUẤT CHUỖI",
        "TOKENIZE THÔ",
    ],
    TaskArchetype.MULTIMODAL_IMAGE_REASONING: [
        "[TASK: VISION]",
        "[TASK: MULTIMODAL]",
        "[IMAGE]",
        "HÌNH ẢNH",
        "MULTIMODAL",
        "CHART",
        "BIỂU ĐỒ",
        "VISION",
        "ĐA PHƯƠNG THỨC",
    ],
    TaskArchetype.DESKTOP_GUI_VISION: [
        "[TASK: GUI]",
        "[TASK: DESKTOP]",
        "[CUA: VISION]",
        "SCREENSHOT",
        "WINDOW CAPTURE",
        "GIAO DIỆN",
        "CUA DRIVER",
        "DESKTOP SCREEN",
    ],
}


@dataclass
class ModelMetadata:
    """Thông tin và nhãn năng lực của một model cục bộ."""

    id: str
    filename: str
    role: str
    size_gb: float
    quant: str
    is_active_soul: bool = False
    status: str = "ACTIVE"
    tags: list[str] = field(default_factory=list)
    strengths: str = ""
    benchmark: str = ""
    full_path: str = ""
    mmproj_path: str = ""


@dataclass
class ModelCatalog:
    """Danh mục toàn bộ model mà ViVy nhận diện được sau khi khởi động."""

    orchestrator_core: str
    models: dict[str, ModelMetadata] = field(default_factory=dict)
    task_archetype_mapping: dict[TaskArchetype, str] = field(default_factory=dict)

    def get_specialist_for_task(self, archetype: TaskArchetype) -> str:
        """Trả về model phù hợp nhất cho archetype này."""
        return self.task_archetype_mapping.get(archetype, self.orchestrator_core)


class ModelCatalogScanner:
    """Quét và phân tích thư mục models/ khi khởi động hệ thống."""

    def __init__(
        self,
        models_dir: Path | str | None = None,
        model_root: Path | str | None = None,
    ):
        if models_dir is not None:
            self.models_dir = Path(models_dir)
        else:
            cand_paths: list[Path] = []
            env_m = os.environ.get("VIVY_MODELS_MANIFEST_DIR")
            if env_m and env_m.strip():
                cand_paths.append(Path(env_m.strip()))
            cand_paths.extend([
                Path(__file__).resolve().parent.parent.parent / "models",
                Path("Vivy final/models"),
                Path("models"),
                Path("../Vivy final/models"),
            ])
            self.models_dir = next((p for p in cand_paths if p.is_dir()), Path("models"))

        # Physical Model Root (chứa file GGUF thực tế)
        env_root = os.environ.get("MODEL_ROOT") or os.environ.get("VIVY_MODELS_DIR")
        if model_root is not None:
            self.model_root = Path(model_root)
        elif env_root and Path(env_root).is_dir():
            self.model_root = Path(env_root)
        elif Path("D:/models").is_dir():
            self.model_root = Path("D:/models")
        else:
            self.model_root = self.models_dir

    def scan(self) -> ModelCatalog:
        """Quét và gán nhãn cho toàn bộ models có sẵn trên đĩa."""
        manifest_path = self.models_dir / "model_manifest.json"
        models_dict: dict[str, ModelMetadata] = {}
        mapping: dict[TaskArchetype, str] = {}
        orchestrator_core = "gemma4-e4b"

        if manifest_path.is_file():
            try:
                data = json.loads(manifest_path.read_text(encoding="utf-8"))
                orchestrator_core = data.get("orchestrator_core", "gemma4-e4b")
                for item in data.get("models", []):
                    meta = ModelMetadata(
                        id=item.get("id", ""),
                        filename=item.get("filename", ""),
                        role=item.get("role", "GENERAL"),
                        size_gb=float(item.get("size_gb", 0.0)),
                        quant=item.get("quant", "UNKNOWN"),
                        is_active_soul=bool(item.get("is_active_soul", False)),
                        status=item.get("status", "ACTIVE"),
                        tags=item.get("tags", []),
                        strengths=item.get("strengths", ""),
                        benchmark=item.get("benchmark", ""),
                        full_path=item.get("full_path", ""),
                        mmproj_path=item.get("mmproj_path", ""),
                    )
                    models_dict[meta.id] = meta

                for k, v in data.get("task_archetype_mapping", {}).items():
                    try:
                        arch = TaskArchetype(k)
                        mapping[arch] = v
                    except ValueError:
                        pass
            except Exception as e:
                logger.warning("Failed to parse model_manifest.json: %s, falling back to disk discovery", e)

        # Quét bổ sung và resolve đường dẫn thực tế từ self.model_root
        if self.model_root and self.model_root.is_dir():
            # 1. Gemma 4 E4B
            gemma_cand = self.model_root / "gemma4-e4b" / "vivy-gemma-e4b-q4km.gguf"
            if gemma_cand.is_file() and "gemma4-e4b" in models_dict:
                models_dict["gemma4-e4b"].full_path = str(gemma_cand)

            # 2. Qwen2-VL-72B Multimodal Pool
            qwen_vl_cand = self.model_root / "qwen2-vl-72b" / "Qwen2-VL-72B-Instruct-Q4_K_M.gguf"
            mmproj_cand = self.model_root / "qwen2-vl-72b" / "mmproj-Qwen2-VL-72B-Instruct-f16.gguf"
            if qwen_vl_cand.is_file():
                if "qwen2-vl-72b" not in models_dict:
                    models_dict["qwen2-vl-72b"] = ModelMetadata(
                        id="qwen2-vl-72b",
                        filename="Qwen2-VL-72B-Instruct-Q4_K_M.gguf",
                        role="MULTIMODAL_KNOWLEDGE_POOL",
                        size_gb=44.16,
                        quant="Q4_K_M",
                        is_active_soul=False,
                        status="DOWNLOADED_ON_DISK",
                        tags=["MULTIMODAL_IMAGE_REASONING", "DESKTOP_GUI_VISION", "CHART_ANALYSIS"],
                        strengths="Thị giác đa phương thức, biểu đồ tài chính, giao diện máy tính CUA",
                        benchmark="MMBench 84.5 | DocVQA 94.2 | 72B Top-K Salience",
                        full_path=str(qwen_vl_cand),
                        mmproj_path=str(mmproj_cand) if mmproj_cand.is_file() else "",
                    )
                else:
                    models_dict["qwen2-vl-72b"].full_path = str(qwen_vl_cand)
                    if mmproj_cand.is_file():
                        models_dict["qwen2-vl-72b"].mmproj_path = str(mmproj_cand)

                mapping[TaskArchetype.MULTIMODAL_IMAGE_REASONING] = "qwen2-vl-72b"
                mapping[TaskArchetype.DESKTOP_GUI_VISION] = "qwen2-vl-72b"

        if models_dict:
            return ModelCatalog(
                orchestrator_core=orchestrator_core,
                models=models_dict,
                task_archetype_mapping=mapping,
            )

        # Heuristic fallback discovery if no manifest exists
        return self._discover_from_disk()

    def _discover_from_disk(self) -> ModelCatalog:
        models_dict: dict[str, ModelMetadata] = {}
        mapping: dict[TaskArchetype, str] = {
            TaskArchetype.ARCH_SPEC_AND_PLAN: "gemma4-e4b",
            TaskArchetype.KNOWLEDGE_FORAGING: "gemma4-e4b",
            TaskArchetype.DYNAMIC_ORCHESTRATION_QA: "gemma4-e4b",
            TaskArchetype.NATIVE_SYSTEM_CODING: "qwen2.5-coder:7b",
            TaskArchetype.REFACTOR_AND_TESTING: "qwen2.5-coder:7b",
            TaskArchetype.FAST_DATA_PARSING: "vivy2",
            TaskArchetype.MULTIMODAL_IMAGE_REASONING: "qwen2-vl-72b",
            TaskArchetype.DESKTOP_GUI_VISION: "qwen2-vl-72b",
        }

        search_dirs = [self.models_dir]
        if self.model_root and self.model_root != self.models_dir and self.model_root.is_dir():
            search_dirs.append(self.model_root)

        for sdir in search_dirs:
            for f in sdir.rglob("*.gguf"):
                fname = f.name.lower()
                size_gb = round(f.stat().st_size / (1024**3), 2)
                if "gemma" in fname:
                    models_dict["gemma4-e4b"] = ModelMetadata(
                        id="gemma4-e4b",
                        filename=f.name,
                        role="COGNITIVE_REASONER",
                        size_gb=size_gb,
                        quant="Q4_K_M",
                        is_active_soul=True,
                        tags=["ARCH_SPEC_AND_PLAN", "ORCHESTRATION_AND_QA"],
                        full_path=str(f),
                    )
                elif "qwen" in fname and "coder" in fname:
                    models_dict["qwen2.5-coder:7b"] = ModelMetadata(
                        id="qwen2.5-coder:7b",
                        filename=f.name,
                        role="TECHNICAL_CODE_SPECIALIST",
                        size_gb=size_gb,
                        quant="Q4_K_M",
                        tags=["NATIVE_SYSTEM_CODING", "REFACTOR_AND_TESTING"],
                        full_path=str(f),
                    )
                elif "qwen" in fname and ("vl" in fname or "72b" in fname) and "mmproj" not in fname:
                    models_dict["qwen2-vl-72b"] = ModelMetadata(
                        id="qwen2-vl-72b",
                        filename=f.name,
                        role="MULTIMODAL_KNOWLEDGE_POOL",
                        size_gb=size_gb,
                        quant="Q4_K_M",
                        status="DOWNLOADED_ON_DISK",
                        tags=["MULTIMODAL_IMAGE_REASONING", "DESKTOP_GUI_VISION"],
                        full_path=str(f),
                    )

        return ModelCatalog(
            orchestrator_core="gemma4-e4b",
            models=models_dict,
            task_archetype_mapping=mapping,
        )


# ---------------------------------------------------------------------------
# Task Classifier & Digest Generator
# ---------------------------------------------------------------------------


def classify_task_archetype(
    prompt: str, catalog: ModelCatalog | None = None
) -> tuple[TaskArchetype, str, str]:
    """Phân loại prompt vào một trong N task archetypes và chọn model tương ứng.

    Returns
    -------
    (archetype, recommended_model_id, explanation)
    """
    upper_prompt = prompt.upper()

    # 1. Quét tín hiệu tường minh (Explicit Signals)
    for archetype, signals in ARCHETYPE_SIGNALS.items():
        for sig in signals:
            if sig.startswith("[") and sig in upper_prompt:
                model = catalog.get_specialist_for_task(archetype) if catalog else "gemma4-e4b"
                return (archetype, model, f"Matched explicit signal {sig!r}")

    # 2. Quét thực thể giả tưởng / tri thức chưa biết (Unknown entities / Foraging)
    forage_indicators = ["GIẢ TƯỞNG", "ZORVAX", "UNKNOWN ENTITY", "THỰC THỂ LẠ", "CHƯA BIẾT", "FORAGE"]
    if any(ind in upper_prompt for ind in forage_indicators):
        model = catalog.get_specialist_for_task(TaskArchetype.KNOWLEDGE_FORAGING) if catalog else "gemma4-e4b"
        return (TaskArchetype.KNOWLEDGE_FORAGING, model, "Detected unknown entity requiring foraging")

    # 3. Quét tín hiệu Vision / Multimodal
    vision_indicators = [
        "HÌNH ẢNH", "IMAGE", "PHOTO", "PICTURE", "BIỂU ĐỒ", "CHART", "CANDLESTICK",
        "SCREENSHOT", "MÀN HÌNH", "MULTIMODAL", "ĐA PHƯƠNG THỨC", "VISION", "DESKTOP SCREEN"
    ]
    if any(ind in upper_prompt for ind in vision_indicators):
        model = catalog.get_specialist_for_task(TaskArchetype.MULTIMODAL_IMAGE_REASONING) if catalog else "qwen2-vl-72b"
        return (TaskArchetype.MULTIMODAL_IMAGE_REASONING, model, "Detected visual / multimodal task requiring vision model")

    # 4. Quét tín hiệu ngữ cảnh (Implicit Contextual Patterns)
    code_indicators = [
        "C-ABI", "CTYPES", "POINTER", "CON TRỎ", "MALLOC", "MAKEFILE",
        "VOID*", "STRUCT", ".DLL", ".SO", "ASSEMBLY", "KERNEL", "DRIVER", "C NATIVE", "MÃ NGUỒN C"
    ]
    code_hits = sum(1 for ind in code_indicators if ind in upper_prompt)
    if code_hits >= 1 and any(k in upper_prompt for k in ["C NATIVE", "MÃ NGUỒN C", "ASSEMBLY", "KERNEL", "CTYPES", "C-ABI", "CON TRỎ", "VOID*"]):
        model = catalog.get_specialist_for_task(TaskArchetype.NATIVE_SYSTEM_CODING) if catalog else "qwen2.5-coder-7b-instruct"
        return (TaskArchetype.NATIVE_SYSTEM_CODING, model, f"Detected low-level system indicator ({code_hits} hits)")
    if code_hits >= 2:
        model = catalog.get_specialist_for_task(TaskArchetype.NATIVE_SYSTEM_CODING) if catalog else "qwen2.5-coder-7b-instruct"
        return (TaskArchetype.NATIVE_SYSTEM_CODING, model, f"Detected {code_hits} low-level system indicators")

    # Kiểm tra refactor/testing
    if any(k in upper_prompt for k in ["PYTEST", "UNIT TEST", "TÁI CẤU TRÚC", "REFACTOR", "BUGFIX"]):
        model = catalog.get_specialist_for_task(TaskArchetype.REFACTOR_AND_TESTING) if catalog else "qwen2.5-coder-7b-instruct"
        return (TaskArchetype.REFACTOR_AND_TESTING, model, "Matched refactoring/testing indicators")

    # Kiểm tra QA / Chấm điểm
    if any(k in upper_prompt for k in ["CHẤM ĐIỂM", "RUBRIC", "SCORE GRAPH", "AUDIT", "THẨM ĐỊNH"]):
        model = catalog.get_specialist_for_task(TaskArchetype.DYNAMIC_ORCHESTRATION_QA) if catalog else "gemma4-e4b"
        return (TaskArchetype.DYNAMIC_ORCHESTRATION_QA, model, "Matched QA/Audit indicators")

    # Mặc định: Giao cho Lõi nhận thức ViVy (Gemma 4EB)
    return (
        TaskArchetype.ARCH_SPEC_AND_PLAN,
        catalog.orchestrator_core if catalog else "gemma4-e4b",
        "Default cognitive reasoning and planning",
    )


def build_catalog_digest(catalog: ModelCatalog) -> str:
    """Tạo bản tóm tắt năng lực mô hình nạp vào Cautreo Memory (~100 tokens)."""
    lines = ["### [VIVY LOCAL MODEL REPOSITORY & CAPABILITY MATRIX]"]
    lines.append(f"• COGNITIVE SOUL: {catalog.orchestrator_core} (Architecture, Planning, Orchestration)")

    for mid, meta in catalog.models.items():
        if mid == catalog.orchestrator_core:
            continue
        status_note = f" [{meta.status}]" if meta.status != "ACTIVE" else ""
        lines.append(f"• SPECIALIST: {meta.id}{status_note} ({meta.size_gb}GB) -> Role: {meta.role}")

    lines.append("• ROUTING RULE: ViVy decomposes tasks -> delegates specialist when needed -> supervises output.")
    return "\n".join(lines)

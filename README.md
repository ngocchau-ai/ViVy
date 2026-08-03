# Unitary Reasoner — Lõi suy luận & điều phối

## Kiến trúc tổng thể

```
┌─────────────────────────────────────────────────────┐
│              Open-Source LLM (frozen)                │
│  Xử lý NL ↔ cung cấp context ↔ sinh hypothesis      │
└────────────┬────────────────────────────┬────────────┘
             │ Input (logic form)         │ Output (NL)
             ▼                            ▲
┌─────────────────────────────────────────────────────┐
│              Unitary Reasoner Core                   │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ Unitary  │  │  Filter  │  │  Associative     │  │
│  │ Gates +  │◄─┤  Funnel  │◄─┤  Memory          │  │
│  │ MPS/TTN  │  │ (SVD +   │  │  (Hebbian +      │  │
│  │          │  │  Entropy) │  │  Quantum Hopfield)│  │
│  └──────────┘  └──────────┘  └──────────────────┘  │
│        ▲              ▲               ▲             │
│        └──────────────┴───────────────┘             │
│                     Orchestrator                    │
└─────────────────────────────────────────────────────┘
```

## Mục tiêu 3 ngày — ✅ HOÀN THÀNH

| Ngày | Agent 1 (Core) | Agent 2 (Memory+Funnel) | Agent 3 (LLM Bridge) |
|------|---------------|------------------------|---------------------|
| **1** | Unitary ...[truncated]
| **2** | Gate sequences + Evolution engine | Filter funnel + Associative memory | Orchestrator + Integration tests |
| **3** | Benchmark + Tối ưu | Integration + Bugfix | End-to-end test + Demo |

## Kết quả

- **242/242 tests PASSED** (e2e syllogism 3/3 PASSED)
- **44 file .py**, ~6,900 dòng code
- Kiến trúc: core (gates, MPS, evolution, SVD streams, entropy) → funnel → memory → orchestrator → llm_bridge
- 3 agent song song + tích hợp chéo hoàn tất trong 1 phiên làm việc

## Nguyên tắc

- **Experimentation first**: code chạy được → đo → cải tiến
- **Không chase efficiency ngay**: Python prototype, Rust/C++ port sau
- **Parallel development**: 3 agent độc lập, tích hợp cuối ngày 2
- **Test-driven**: mỗi module có test ngay khi viết

## Beta 1 — Gemma 4EB (Ollama)

- **Backend:** Ollama `http://localhost:11434/v1`
- **Model:** `gemma4:e4b` (9.6 GB)
- **Config:** `.env` (tự động load bởi `demo.py`)
- **Pipeline:** encode → evolve → evaluate → decode (e2e syllogism ✅)

```bash
python demo.py
```

## Phase 0 (đảo ngược) — ✅ HOÀN THÀNH

Xem [PLAN_PHASE0.md](./PLAN_PHASE0.md) — củng cố nền tảng, ADR, cổng chất lượng,
cứng hóa core, và release checklist.

### Đã triển khai (v0.2.0)

| Hạng mục | Trạng thái |
|----------|-----------|
| **ADR** | ✅ 7 ADR trong `docs/adr/` |
| **Môi trường** | ✅ `.gitignore`, `setup.sh`, `setup.ps1`, `Makefile`, dev extras |
| **Cổng chất lượng** | ✅ ruff (0 lỗi) + mypy (0 lỗi) + pytest (242/242) |
| **Cứng hóa core** | ✅ `evolve()` schedule optional; orchestrator dùng real thay stub |
| **Release** | ✅ CHANGELOG, version 0.2.0 |

```bash
make check   # lint + type + test
python demo.py
```
# Sync Manifest — Vivy Final ↔ vivyChatGPT (2026-09-25)

**Purpose:** Đồng bộ code + docs từ `vivyChatGPT/training/` vào `Vivy final/core/integration/` + `Vivy final/docs/plans/` để tránh nhầm lẫn khi lưu trữ, sao chép.

---

## Code synced → `core/integration/`

### Plan 1 — Live Evidence Spine (B→D)
| File | Role |
|---|---|
| `verify_receipt.py` | SHA256 receipt chain integrity |
| `sandbox_capture.py` | P3 safe-subset + sandbox capture |
| `check_known_limits.py` | KNOWN_LIMITATIONS consistency |
| `run_w2_live.py` | W2 orchestrator (6 checks) |
| `evidence_packet_template.md` | Markdown packet template |
| `receipt.py` | +validate_live_shape (D5) |
| `preflight.py` | +contract test list |

### Plan 2 — Contract-Native Close-out (A→C)
| File | Role |
|---|---|
| `native_parity_decision.py` | A-fix / A-retire decision |
| `learned_router.py` | Brier / ECE / permutation control |

### Wave 1 — Cautreo Memory (TD-3, TD-7)
| File | Role |
|---|---|
| `cautreo_weight_map.py` | Tree index, O(log n) lookup |
| `cautreo_session_log.py` | Append-only + replay |

### Wave 2 — Weight Pager + Cross-Model (TD-4, TD-5)
| File | Role |
|---|---|
| `weight_pager.py` | Partial load, stream, memory usage |
| `cross_model_adapter.py` | Couple, route, combine, callback weights |

### Wave 3 — Scored Mindmap DAG (TD-6)
| File | Role |
|---|---|
| `scored_mindmap_dag.py` | Plan, score, reroute, cycle detection |

### Wave 4 — Progressive Scaling (TD-8)
| File | Role |
|---|---|
| `model_upgrade_protocol.py` | Readiness gate, migrate, inherit weights |

### Tests
| File | Tests |
|---|---|
| `test_verify_receipt.py` | 9 |
| `test_sandbox_capture.py` | 11 |
| `test_check_known_limits.py` | 6 |
| `test_run_w2_live.py` | 12 |
| `test_receipt_shape.py` | 4 |
| `test_native_parity_decision.py` | 13 |
| `test_learned_router.py` | 27 |
| `test_cautreo_weight_map.py` | 22 |
| `test_cautreo_session_log.py` | 17 |
| `test_weight_pager.py` | 18 |
| `test_cross_model_adapter.py` | 23 |
| `test_scored_mindmap_dag.py` | 32 |
| `test_model_upgrade_protocol.py` | 28 |

---

## Docs synced → `docs/plans/`

| File | Content |
|---|---|
| `DISCUSSION_VIVY_ORCHESTRATION_2026-09-25.md` | Architecture + TD-1→TD-8 |
| `plan-tune-vivy-orchestration-2026-09-25.md` | Wave 1-4 plan |
| `BAO_CAO_KET_QUA.md` | Results report |
| `KNOWN_LIMITATIONS.md` | Known limitations |

---

## Updated files

| File | Change |
|---|---|
| `ARCHITECTURE_FINAL.md` | +Changelog v1.4.0 |
| `README.md` | +Changelog v1.4.0 |

---

## Source of truth

- **Primary:** `vivyChatGPT/training/` (107 files, test suite)
- **Mirror:** `Vivy final/core/integration/` (41 files, runtime)
- **Sync direction:** vivyChatGPT → Vivy final (one-way, manual)
- **Verification:** `filecmp.cmp(src, dst) == True` per CLAUDE.md constraint

---

## Architecture summary

```
vivyChatGPT/training/     ← Primary (tests, development)
    ↓ sync
Vivy final/core/integration/  ← Mirror (runtime, distribution)
    ↓
Vivy final/core/               ← Runtime core (engine, memory, orchestrator)
```

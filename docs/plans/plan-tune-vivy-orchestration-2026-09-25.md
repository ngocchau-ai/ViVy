# Plan-tune: Vivy Orchestration Architecture (TD-1 → TD-8)

**Source:** Thảo luận 2026-09-25 (DISCUSSION_VIVY_ORCHESTRATION_2026-09-25.md)
**Scope:** Orchestration core + Cautreo memory + Weight management
**Constraint:** Isolate-not-delete, Health Stack green, không sửa immutables

---

## Decision Ledger (from discussion)

| ID | Decision | Impact |
|---|---|---|
| TD-1 | Vivy = orchestrator, không distill model | Không train model copy |
| TD-2 | Xâm lấn + kế thừa meta-reasoning | Tích lũy decision quality |
| TD-3 | Cautreo memory (maps + logs) bắt buộc | Persistent knowledge |
| TD-4 | Weight pager partial load | Resource efficiency |
| TD-5 | Cross-model = adapter (ghép output) | Không share weights |
| TD-6 | Mindmap DAG = planning + QC | Không thay generator |
| TD-7 | Tree map + session tracing | Index + audit |
| TD-8 | Progressive scaling model core | HW-fit → upgrade |

---

## Wave 1: Cautreo Memory Foundation (TD-3, TD-7)

### 1A. Cautreo Weight Map — Tree Index

**File:** `training/cautreo_weight_map.py` (+test)

Tree structure cho hierarchical lookup:
```
WeightMap
├── tree_index: dict[str, WeightNode]
│   ├── node_id, parent_id, children
│   ├── model_alias, layer_range, capability_tags
│   └── score: float (0-1)
├── insert(node), lookup(query) -> list[WeightNode]
└── by_capability(task) -> list[WeightNode]
```

- O(log n) lookup qua tree
- `capability_map`: task → model → layer_range
- Score node theo effectiveness history

### 1B. Session Log — Append-only + Score

**File:** `training/cautreo_session_log.py` (+test)

```
SessionLog
├── entries: list[SessionEntry]
│   ├── session_id, timestamp
│   ├── decisions: list[{input, strategy, model, output, score}]
│   ├── state_delta: dict (weight_map changes)
│   └── aggregate_score: float
├── append(entry), query(filter) -> list[SessionEntry]
└── replay() -> experience summary
```

- Audit trail + self-improve data source
- `replay()` extract patterns → feed vào weight map scoring

---

## Wave 2: Weight Pager Integration (TD-4, TD-5)

### 2A. Weight Pager Interface

**File:** `training/weight_pager.py` (+test)

```
WeightPager
├── register_model(alias, path, format)
├── load_partial(alias, layer_range) -> WeightSlice
├── stream_weights(alias, callback)
└── memory_usage() -> dict
```

- Partial load Q4_K/Q6_K (từ C-ABI GGUF weight pager đã có)
- Stream weights không cần load toàn bộ
- Interface cho cross-model adapter (TD-5)

### 2B. Cross-Model Adapter

**File:** `training/cross_model_adapter.py` (+test)

```
CrossModelAdapter
├── couple(primary_alias, secondary_alias)
├── route(task, context) -> model_alias
├── combine_outputs(primary_out, secondary_out) -> final_out
└── callback_weights(old_alias, task) -> WeightSlice | None
```

- Vivy routing → model nào làm gì
- `callback_weights`: gọi ngược Gemma4 weights khi cần (weight inheritance)
- Không share weights — ghép output tầng orchestration

---

## Wave 3: Mindmap DAG Enhancement (TD-6)

### 3A. Scored Mindmap DAG

**File:** `training/scored_mindmap_dag.py` (+test)

```
MindmapDAG
├── nodes: list[DecisionNode]
│   ├── node_id, input_context, strategy
│   ├── model_target: alias
│   ├── score: float (confidence)
│   └── edges: list[-> child nodes]
├── plan(input) -> DAG path
├── score_path(path) -> float
└── reroute(node, new_score) -> new_path
```

- Scoring nodes → confidence check → re-route khi score thấp
- Plan structure trước → giảm mid-generation drift
- Trace được input → decision → output

---

## Wave 4: Progressive Scaling Protocol (TD-8)

### 4A. Model Upgrade Protocol

**File:** `training/model_upgrade_protocol.py` (+test)

```
UpgradeProtocol
├── readiness_check() -> dict
│   ├── memory_entries: int (threshold: ≥100)
│   ├── avg_decision_score: float (threshold: ≥0.7)
│   ├── task_complexity: str
│   └── hardware_available: bool
├── migrate(old_alias, new_alias) -> MigrationReceipt
└── inherit_weights(old_alias) -> dict (weight registry)
```

- Gate: experience đủ + HW cho phép → migrate
- Migration receipt (SHA256 chain) cho audit
- `inherit_weights`: đăng ký weight cũ để callback sau

---

## Integration Points (existing code)

| Component | Integrate với |
|---|---|
| `cautreo_weight_map.py` | `cautreo_scoring_journal.py` (REUSE) |
| `weight_pager.py` | `llama_cpp_bridge.py` (REUSE), weight-pager C-ABI |
| `cross_model_adapter.py` | `backend_registry.py` (REUSE) |
| `scored_mindmap_dag.py` | `parallel_context_pipeline.py` (REUSE) |
| `model_upgrade_protocol.py` | `preflight.py` (REUSE) |

---

## Test Strategy

| Wave | Positive | Negative |
|---|---|---|
| 1 | tree lookup, session replay | empty map, corrupt log |
| 2 | partial load, route+combine | model not registered, memory OOM |
| 3 | plan+score+reroute | cycle detection, score < threshold |
| 4 | readiness gate, migrate | not ready → refuse, ABI break |

---

## Success Criteria

| Wave | Done khi |
|---|---|
| 1 | Weight map tree lookup + session log replay PASS |
| 2 | Partial load + cross-model route PASS |
| 3 | DAG plan + scoring + reroute PASS |
| 4 | Upgrade protocol + weight inheritance PASS |
| All | ruff 0, mypy 0, pytest 100% (existing + new) |

---

## Constraints

1. Isolate-not-delete: cũ đánh dấu `[ISOLATED]`, không xóa
2. Không sửa `vivy_train_dataset.jsonl`, `gold_train.jsonl`
3. Gate 9: không PRODUCTION-READY, không 0%, không latency SLA
4. `production_ready = NOT_CLAIMED` until acceptance plan §6
5. Receipt chain: SHA256 prev + self, genesis rule
6. Sandbox capture ≠ EXECUTE_DIRECTLY

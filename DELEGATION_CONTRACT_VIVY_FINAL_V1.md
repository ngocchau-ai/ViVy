> [!IMPORTANT]
> **QUY ƯỚC BẮT BUỘC DÀNH CHO AGENT KẾ THỪA & CHỈNH SỬA TÀI LIỆU:**
> 1. **Ghi chú bắt buộc (Changelog):** Bất kỳ agent nào chỉnh sửa tài liệu này PHẢI bổ sung ghi chú tại mục Lịch Sử Thay Đổi.
> 2. **Chỉ cô lập, KHÔNG xóa bỏ:** TUYỆT ĐỐI KHÔNG xóa bỏ các nội dung cũ.
> 3. **Đồng bộ D:\2brain đầy đủ.**

# DELEGATION CONTRACT — VIVY FINAL V1.0
## HoH Control Plane | Antigravity IDE → Codex CLI + Claude Code

- **Contract ID:** `HOH-VIVY-FINAL-V1-2026-0919`
- **Issued by:** Antigravity IDE (Deputy 1 Coordinator — QA/QC & Completion Gate)
- **Date:** 19/09/2026 17:57 ICT
- **Baseline:** `330/330 tests passed` (pytest, 9.47s)
- **Architecture:** `ARCHITECTURE_V5.md` (V5.1.0-PROD-SPEC)
- **Plan:** `docs/plans/KE_HOACH_TRIEN_KHAI_VIVY_V5.md` (V1.1.0)
- **Criteria:** `docs/plans/BO_TIEU_CHI_DANH_GIA_VA_PHAN_BIEN_VIVY.md` (V1.1.0)

---

## PHÂN VAI HoH (Authority Hierarchy)

```
COORDINATOR (QA Gate — KHÔNG viết code thô):
  Antigravity IDE → Giám sát, nghiệm thu, phát Completion Gate

WORKER A — Codex CLI (codex exec -)
  Sprint 1: Engine Primitives + Elastic N-Core + MTP
  Thế mạnh: Thực thi mã nguồn cấu trúc cao, thuật toán phức tạp

WORKER B — Claude Code (claude -p)
  Sprint 1 Review: Rà soát độc lập output của Worker A
  Sprint 2: Cognitive State Graph + Hebbian Memory W=YX+
  Thế mạnh: Code review, bug logic, kiểm toán edge cases
```

---

## SCOPE BOUNDING — FILE ĐƯỢC PHÉP SỬA

```
ALLOWED MUTATIONS (Worker A & B):
  unitary-reasoner/engine/             ← Engine Primitives mới
  unitary-reasoner/orchestrator/       ← N-Core, MTP heads
  unitary-reasoner/memory/             ← Hebbian W=YX+ operator
  unitary-reasoner/forager/            ← Knowledge Artifact writer
  unitary-reasoner/tests/              ← Thêm test, KHÔNG sửa test cũ pass

FORBIDDEN (KHÔNG ĐƯỢC ĐỤNG):
  unitary-reasoner/core/               ← Unitary reasoner core — đã ổn định
  unitary-reasoner/funnel/             ← Filter pipeline — đã pass 330 tests
  unitary-reasoner/llm_bridge/         ← Bridge protocol — stable
  ARCHITECTURE_V5.md                   ← Chỉ Coordinator
  docs/plans/                          ← Chỉ Coordinator
```

---

## WORKER A: CODEX CLI — SPRINT 1

### Task ID: `W-A-SPRINT1-ENGINE-PRIMITIVES`

### Objective:
Triển khai 3 module mới để ViVy có thể:
1. Gọi 4 Engine Primitives trực tiếp (file I/O, exec, media slice, cache control)
2. Chạy Elastic N-Core Single-Pass evaluation (N=2 baseline, dynamic scaling)
3. Phát Directive Execution Tuple qua MTP heads (1 pass, zero autoregressive)

### Constraints:
- Chỉ dùng: numpy, stdlib Python ≥ 3.11
- KHÔNG import: LangChain, AutoGen, requests (thay bằng urllib.request nếu cần)
- KHÔNG sửa bất kỳ test nào đang pass
- KHÔNG xóa file nào

### Deliverables:
```
engine/primitives.py           ← 4 Engine Primitives: file_io, exec, media_slice, cache_control
engine/elastic_n_core.py       ← ElasticNCore(n_min=2, n_max=16), detect_hardware_budget()
engine/mtp_directive.py        ← MTP heads, phát DirectiveExecutionTuple trong 1 pass
tests/test_primitives.py       ← Unit tests engine/primitives.py
tests/test_elastic_n_core.py   ← Unit tests N=2 baseline + OOM guard + scaling logic
tests/test_mtp_directive.py    ← Unit tests MTP output format verification
```

### Acceptance Gate 1 (Coordinator verifies):
```
[ ] pytest tests/ -q → 330 + NEW_TESTS passed, 0 regressions
[ ] engine_file_io(), engine_exec(), engine_media_slice(), engine_cache_control() defined
[ ] ElasticNCore(n_min=2, n_max=16) với detect_hardware_budget() method
[ ] DirectiveMTPHead.forward() xuất DirectiveExecutionTuple trong 1 pass
[ ] KHÔNG có import LangChain/AutoGen
[ ] Benchmark mock test: directive generation ≤ 15ms
[ ] N=2 baseline không OOM trên hardware constraint mock
```

### Codex CLI Invocation (Paste vào terminal):
```bash
codex exec - <<'PROMPT'
Context: ViVy Final V1.0 — Sprint 1 implementation
CWD: unitary-reasoner/ (in "91s- Tai cau truc lan thu 4" workspace)
Baseline: 330 tests pass — DO NOT break them.

READ FIRST (do not skip):
1. ../ARCHITECTURE_V5.md Section 9.2 → 4 Engine Primitives exact signatures
2. ../ARCHITECTURE_V5.md Section 5.2 → Elastic N-Core, Hidden State h_L definition
3. DELEGATION_CONTRACT_VIVY_FINAL_V1.md → Scope boundaries and Gate 1 criteria

IMPLEMENT:
- engine/primitives.py: engine_file_io(action,path,content,offset,length), engine_exec(cmd,timeout,env), engine_media_slice(source,start_ms,end_ms), engine_cache_control(op,scope)
- engine/elastic_n_core.py: class ElasticNCore with detect_hardware_budget() → n_active; n in [2,16]; includes OOM guard returning n=2 minimum
- engine/mtp_directive.py: class DirectiveMTPHead; forward(hidden_state) → DirectiveExecutionTuple(target_id, opcode, payload_hash, signature)
- tests/test_primitives.py, tests/test_elastic_n_core.py, tests/test_mtp_directive.py

FORBIDDEN: Do not edit core/, funnel/, llm_bridge/ or any existing test files.
FORBIDDEN: No LangChain, AutoGen, requests imports.
REPORT: Output final test count and any concerns.
PROMPT
```

---

## WORKER B: CLAUDE CODE

### Task A: `W-B-REVIEW-SPRINT1` (sau khi Worker A hoàn tất)

**Objective:** Rà soát độc lập Sprint 1 output:
- Bug logic trong ElasticNCore (race condition khi N scale down đột ngột?)
- Edge cases: engine_exec() timeout, stderr capture, exit code ≠ 0
- DirectiveExecutionTuple format có khớp orchestrator/directive_contract.py?
- AI slop / dead code / redundant abstraction

**Deliverable:** `scratchpad/SPRINT1_REVIEW_REPORT.md`

**Format báo cáo:**
```markdown
# Sprint 1 Review Report
## CRITICAL (blocking)
## HIGH (should fix before Sprint 2)
## MEDIUM (can defer)
## VERDICT: APPROVED | NEEDS_REWORK
```

---

### Task B: `W-B-SPRINT2-COGNITIVE-GRAPH` (sau khi Review APPROVED)

### Objective:
Triển khai Cognitive State Graph với Hebbian Associative Memory ($W = YX^+$), độc lập hoàn toàn khỏi KV Cache, truy xuất $O(1)$.

### Constraints:
- Kế thừa `memory/associative.py` — KHÔNG rewrite từ đầu
- Graph storage KHÔNG store raw token sequences (no KV Cache coupling)
- KHÔNG sửa core/, funnel/

### Deliverables:
```
memory/cognitive_graph.py      ← CognitiveStateGraph: N_hypo, N_invariant, N_rca node types
memory/hebbian_recall.py       ← HebbianRecall: W=YX+, recall(x_t)→y_t, O(1) retrieval
orchestrator/graph_bridge.py   ← Bridge: CognitiveStateGraph ↔ ElasticNCore state vector
tests/test_cognitive_graph.py  ← add_node, add_edge_falsified, recall accuracy
tests/test_hebbian_recall.py   ← O(1) complexity proof: 10 vs 10,000 nodes same latency
tests/test_graph_bridge.py     ← Integration: N-Core state → Graph recall → dampened output
```

### Acceptance Gate 2 (Coordinator verifies):
```
[ ] pytest tests/ -q → ALL passed (330 + Sprint1 + Sprint2), 0 regressions
[ ] CognitiveStateGraph: 3 node types (HYPOTHESIS, INVARIANT, RCA_ROOT) + edge FALSIFIED
[ ] HebbianRecall.recall() O(1): test với 10 nodes và 10,000 nodes — latency diff < 5%
[ ] VM-11 PASS: error repeat rate ≤ 10% trên mock 100-task sequence với graph active
[ ] Graph KHÔNG OOM khi scale lên 10,000 nodes
[ ] graph_bridge.py wires ElasticNCore hidden state → Graph → dampened candidates
```

### Claude Code Invocation (Paste vào terminal):
```bash
claude -p "
Context: ViVy Final V1.0 — Sprint 2: Cognitive State Graph
CWD: unitary-reasoner/
Baseline: 330+ tests pass — DO NOT break them.

READ FIRST:
1. ../ARCHITECTURE_V5.md Section 6 → Cognitive State Graph, W=YX+ definition
2. memory/associative.py → Existing Moore-Penrose implementation to inherit from
3. DELEGATION_CONTRACT_VIVY_FINAL_V1.md → Gate 2 criteria

Task A (if not done): Review engine/ Sprint 1 output, write scratchpad/SPRINT1_REVIEW_REPORT.md

Task B: Implement Sprint 2:
- memory/cognitive_graph.py: CognitiveStateGraph with node types HYPOTHESIS/INVARIANT/RCA_ROOT, edge type FALSIFIED
- memory/hebbian_recall.py: HebbianRecall inheriting from memory/associative.py, O(1) recall via W=YX+ (Moore-Penrose pseudoinverse)
- orchestrator/graph_bridge.py: wire ElasticNCore hidden_state → CognitiveStateGraph recall → dampened action set
- All tests as specified in contract Gate 2

FORBIDDEN: Do not edit core/, funnel/, llm_bridge/ or any existing passing tests.
Report final test count and VM-11 mock result.
"
```

---

## COORDINATOR GATE — 7 CONDITIONS TO ISSUE `COMPLETE`

> Chỉ Antigravity IDE mới có thẩm quyền phát `COMPLETE` sau khi đủ 7 điều kiện:

```
[ ] 1. Delegation Contract này đã được Workers đọc và acknowledged
[ ] 2. Tất cả artifacts trong Deliverables đều hiện diện đúng đường dẫn
[ ] 3. pytest tests/ -q → 0 failures, 0 regressions so với baseline 330
[ ] 4. VM-10 PASS: ElasticNCore không OOM ở N=2; scale đúng theo VRAM budget
[ ] 5. VM-11 PASS: Error repeat rate ≤ 10% trên mock 100-task sequence
[ ] 6. Claude Code review report: 0 CRITICAL, 0 HIGH severity issues còn mở
[ ] 7. 0 wrapper imports (LangChain/AutoGen) trong toàn bộ engine/, orchestrator/, memory/
```

---

## HANDOFF SCHEMA (Worker báo cáo khi hoàn tất)

```json
{
  "worker": "codex-cli | claude-code",
  "task_id": "W-A-SPRINT1... | W-B-...",
  "state": "COMPLETE | NEEDS_REWORK | BLOCKED",
  "artifacts": ["engine/primitives.py", "..."],
  "evidence": {
    "test_count": 330,
    "new_tests": 42,
    "failures": 0,
    "regressions": 0
  },
  "remaining": "...",
  "risks": "..."
}
```

---

## LỊCH SỬ THAY ĐỔI

| Phiên Bản | Thời Gian | Agent | Nội Dung |
| :--- | :--- | :--- | :--- |
| **1.0.0** | 19/09/2026 17:57 | Antigravity IDE / Ngọc Châu | Khởi tạo Delegation Contract theo HoH Protocol. Baseline: 330/330 tests. |

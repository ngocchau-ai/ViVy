# NPS CORE — KIẾN TRÚC PRINCIPAL SCIENTIST MODEL
## Tài liệu kiến trúc V1.0 Final

**Tên kiến trúc:** N-Thought Principal Scientist Core  
**Tên viết tắt:** NPS Core  
**Trạng thái:** Architecture Baseline — V1.0 Final  
**Ngày:** 23/07/2026  
**Ngôn ngữ tài liệu:** Tiếng Việt  
**Mục đích:** Là tài liệu gốc để con người, Codex Cowork và các model local hiểu nhanh toàn bộ định hướng, nguyên tắc và lộ trình phát triển dự án.

---

# 0. TUYÊN BỐ DỰ ÁN

NPS Core là một dự án xây dựng **model có bản sắc nhận thức riêng**, không phải một bản sao nhỏ hơn của LLM hiện có.

Model được định vị như một **nhà khoa học trưởng**:

- Không cố tự làm toàn bộ công việc.
- Không tư duy theo một chuỗi duy nhất.
- Không mặc định câu trả lời đầu tiên là đúng.
- Không tích lũy tri thức thô vô giới hạn trong tham số.
- Không thay executor thực hiện các công việc chuyên sâu.
- Không sử dụng multi-agent chỉ để tạo nhiều câu trả lời tương tự.

Cô ấy có nhiệm vụ:

1. Phân tích vấn đề.
2. Khởi tạo một quần thể gồm `N` tư duy hoặc giả thuyết.
3. Duy trì trạng thái, độ tin cậy và quan hệ giữa các giả thuyết.
4. Thiết kế các phép kiểm chứng có giá trị thông tin cao.
5. Giao nhiệm vụ cho các executor phù hợp.
6. Thu nhận và đánh giá bằng chứng.
7. Cập nhật đồng thời toàn bộ không gian giả thuyết.
8. Loại bỏ, hợp nhất hoặc phân nhánh các tư duy.
9. Hội tụ về một kết luận có thể kiểm tra và giải thích.

> **Định nghĩa một câu:**  
> NPS Core là lõi trí tuệ duy trì quần thể giả thuyết thích nghi, thiết kế phép kiểm chứng có giá trị thông tin cao và điều phối các executor độc lập để hội tụ về kết luận có thể kiểm chứng.

---

# 1. VỊ TRÍ CỦA BA TÀI LIỆU NGUỒN

Ba tài liệu ban đầu được coi là **dữ liệu tư duy thô**, không phải đặc tả kỹ thuật cuối cùng.

## 1.1. Tài liệu Gemini

Đóng góp chính:

- Không gian nghiệm đa diện.
- Ràng buộc `A·x ≤ b`.
- Cutting plane để loại bỏ vùng vô nghiệm.
- Soft-qubit như phép ẩn dụ cho việc duy trì nhiều trạng thái.
- DataContract cho giao tiếp với sub-model.
- Core orchestrator điều phối model chuyên môn.

Điểm được giữ:

- Constraint-based reasoning.
- Hypothesis pruning.
- Formal verification.
- DataContract.
- Orchestrator.

Điểm chưa coi là chân lý:

- Mọi bài toán đều có thể chuyển trực tiếp thành hệ bất phương trình tuyến tính.
- Soft-qubit tạo ra ưu thế tính toán tương đương lượng tử.
- SIMD xử lý bốn trạng thái đồng nghĩa với suy luận đa luồng cấp nhận thức.
- Formal verifier có thể loại sạch toàn bộ ảo giác.

## 1.2. Tài liệu DeepSeek

Đóng góp chính:

- Tư duy được biểu diễn như tiến hóa trạng thái.
- Không gian ý niệm.
- Tensor network và biến đổi unita.
- Tầng chiếu và điều phối.
- Model không trực tiếp làm mọi việc mà gọi các lõi chuyên môn.
- Tư duy đa luồng là thuộc tính của trạng thái, không phải nhiều thread hội thoại.

Điểm được giữ:

- State-space reasoning.
- Structured transformation.
- Projection into executable tasks.
- Feedback injection.
- Separation between reasoning core and language interface.

Điểm chưa coi là chân lý:

- Không cần học thống kê.
- Mọi quy tắc logic có thể được mã hóa hiệu quả bằng ma trận unita.
- Một mạng tensor nhỏ có thể vượt mô hình lớn trong mọi miền suy luận.
- Tiến hóa unita là cơ chế tối ưu cho tư duy tổng quát.

## 1.3. Tài liệu Grok

Đóng góp chính:

- Cố gắng hợp nhất polyhedral, unitary, soft-qubit và multi-agent.
- Nhấn mạnh self-verification.
- Đề xuất teacher funnel.
- Đề xuất model gọn làm core orchestrator.

Điểm được giữ:

- Kiến trúc lai.
- Multi-teacher distillation có kiểm chứng.
- Matrix planning.
- Self-learning có kiểm soát.

Điểm cần tái cấu trúc:

- Không dùng “multi-agent dialectic” như trung tâm.
- Không đồng nhất N tư duy với N agent.
- Không coi teacher là nguồn hình thành bản sắc model.
- Không dùng tên gọi lượng tử để thay thế cho đặc tả thuật toán.

---

# 2. BẢN SẮC NHẬN THỨC CỦA MODEL

Bản sắc của NPS Core không nằm ở tên model nền, số tham số hay một thuật ngữ lượng tử.

Bản sắc nằm trong sáu cơ chế bắt buộc:

## 2.1. Population Reasoning

Model duy trì một quần thể tư duy thay vì một chuỗi suy luận duy nhất.

Mỗi tư duy là một đối tượng trạng thái có cấu trúc, không phải một đoạn văn tự do.

## 2.2. Delegated Cognition

Model biết phân biệt:

- Việc cần tự suy nghĩ.
- Việc cần lập kế hoạch.
- Việc cần giao model local.
- Việc cần solver.
- Việc cần simulator.
- Việc cần search/research.
- Việc cần con người xác nhận.

## 2.3. Experimental Intelligence

Model không chỉ tìm câu trả lời.

Model tìm:

> Phép kiểm chứng rẻ nhất, nhanh nhất và có khả năng làm giảm bất định nhiều nhất.

## 2.4. Evidence Economy

Executor không trả về “ý kiến”.

Executor trả về các evidence packet chuẩn hóa, có:

- claim;
- phương pháp;
- dữ liệu;
- độ tin cậy;
- giới hạn;
- khả năng tái lập;
- giả thuyết bị ảnh hưởng.

## 2.5. Epistemic Identity

Model phải luôn phân biệt:

- fact;
- assumption;
- hypothesis;
- inference;
- external report;
- verified result;
- disputed result;
- unresolved uncertainty.

## 2.6. Runtime Identity

Bản sắc model phải tồn tại trong runtime architecture.

Khi thay model ngôn ngữ nền, hệ thống vẫn phải giữ:

- adaptive N;
- thought population;
- evidence graph;
- experiment design;
- delegation policy;
- verification tribunal;
- memory governance.

---

# 3. ĐƠN VỊ CƠ BẢN: THOUGHT STATE

```yaml
thought_state:
  thought_id: string
  parent_ids: []
  created_at: timestamp

  interpretation:
    summary: string
    scope: string
    excluded_scope: []

  hypothesis:
    claim: string
    predicted_observations: []
    falsification_conditions: []

  assumptions:
    - assumption_id: string
      statement: string
      confidence: float
      source: string

  evidence:
    supporting: []
    opposing: []
    unresolved: []

  metrics:
    confidence: float
    novelty: float
    diversity: float
    expected_value: float
    information_need: float
    risk_if_wrong: float
    execution_cost: float

  verification_plan:
    questions: []
    required_experiments: []
    acceptable_evidence: []
    rejection_threshold: float

  executor_profile:
    skills: []
    tool_requirements: []
    preferred_model_class: string
    independence_requirements: []

  graph:
    dependencies: []
    contradictions: []
    overlaps: []

  status:
    state: active
    allowed_values:
      - active
      - queued
      - testing
      - partially_verified
      - verified
      - rejected
      - merged
      - dormant
```

---

# 4. BA GIÁ TRỊ N TÁCH BIỆT

Không dùng một biến `N` duy nhất cho toàn bộ hệ thống.

```text
N_h = số giả thuyết hoặc tư duy nội bộ
N_v = số nhu cầu kiểm chứng
N_e = số executor thực sự được gọi
```

Quan hệ mục tiêu:

```text
N_h >= N_v >= N_e
```

Ví dụ:

- 16 giả thuyết đang hoạt động.
- 7 điểm bất định cần kiểm chứng.
- 4 experiment có thể phân biệt các giả thuyết.
- 3 executor đủ để thực hiện 4 experiment.

Không mặc định:

```text
1 thought = 1 executor
```

---

# 5. ADAPTIVE N CONTROLLER

## 5.1. Mục tiêu

Adaptive N Controller quyết định:

- Khi nào tạo thêm tư duy.
- Khi nào dừng phân nhánh.
- Khi nào gộp tư duy.
- Khi nào tạm đóng băng tư duy.
- Khi nào cần thêm executor.
- Khi nào ngân sách không cho phép mở rộng.

## 5.2. Công thức bootstrap

```text
N_target =
clip(
    N_min
    + α * complexity
    + β * uncertainty
    + γ * diversity_need
    + δ * risk_if_wrong
    - ε * resource_pressure,
    N_min,
    N_max
)
```

Đây chỉ là công thức ban đầu để prototype.

## 5.3. Cơ chế mục tiêu dài hạn

Một tư duy mới chỉ được tạo khi thỏa ít nhất một điều kiện:

- Bao phủ vùng giả thuyết chưa có đại diện.
- Tạo dự đoán khác biệt có thể kiểm chứng.
- Phá vỡ một giả định nền đang bị dùng chung.
- Giải thích được bằng chứng mà các tư duy hiện tại không giải thích được.
- Có expected information gain vượt ngưỡng.

## 5.4. Điều kiện prune

Một ThoughtState bị prune khi:

- Trùng lặp ngữ nghĩa vượt ngưỡng.
- Không tạo ra dự đoán phân biệt.
- Chi phí kiểm chứng quá cao so với giá trị.
- Bị formal constraint bác bỏ.
- Bị evidence mạnh bác bỏ.
- Không còn ảnh hưởng đến quyết định cuối.

## 5.5. Điều kiện merge

Hai tư duy được merge khi:

- Cùng giả thuyết cốt lõi.
- Khác nhau chủ yếu ở cách diễn đạt.
- Chia sẻ phần lớn assumption.
- Có verification plan tương đương.
- Không tạo ra kết quả dự báo khác biệt đáng kể.

---

# 6. KIẾN TRÚC HỆ THỐNG

```text
┌─────────────────────────────────────────────────────────┐
│                    USER / EXTERNAL TASK                 │
└────────────────────────────┬────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────┐
│ 1. PROBLEM COMPILER                                  │
│ - Chuẩn hóa mục tiêu                                  │
│ - Tách constraint                                     │
│ - Xác định unknowns                                   │
│ - Sinh ProblemGraph                                   │
└────────────────────────────┬────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────┐
│ 2. HYPOTHESIS POPULATION ENGINE                      │
│ - Sinh N_h tư duy                                     │
│ - Đo diversity                                        │
│ - Branch / merge / prune                              │
└────────────────────────────┬────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────┐
│ 3. THOUGHT ECOLOGY GRAPH                             │
│ - Dependency                                          │
│ - Contradiction                                       │
│ - Shared assumptions                                  │
│ - Evidence impact                                     │
└────────────────────────────┬────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────┐
│ 4. EXPERIMENT DESIGNER                               │
│ - Xếp hạng điểm bất định                              │
│ - Expected information gain                          │
│ - Gom verification tasks                              │
│ - Tạo N_v                                            │
└────────────────────────────┬────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────┐
│ 5. CONTRACT GENERATOR                                │
│ - Input contract                                      │
│ - Output schema                                       │
│ - Acceptance criteria                                 │
│ - Resource budget                                     │
│ - Failure protocol                                    │
└────────────────────────────┬────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────┐
│ 6. EXECUTOR ROUTER                                   │
│ - Local coder model                                   │
│ - Local tester model                                  │
│ - Local reviewer model                                │
│ - Solver / simulator                                  │
│ - Research connector                                  │
│ - Human reviewer                                      │
└────────────────────────────┬────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────┐
│ 7. EVIDENCE ASSIMILATOR                              │
│ - Validate schema                                     │
│ - Normalize evidence                                  │
│ - Track provenance                                    │
│ - Detect dependence                                   │
└────────────────────────────┬────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────┐
│ 8. VERIFICATION TRIBUNAL                             │
│ - Cross-check                                         │
│ - Reproduction                                        │
│ - Formal check                                        │
│ - Calibration                                         │
└────────────────────────────┬────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────┐
│ 9. STATE UPDATE ENGINE                               │
│ - Cập nhật đồng thời các ThoughtState                  │
│ - Apply cuts                                          │
│ - Reweight                                            │
│ - Merge / prune / branch                              │
└────────────────────────────┬────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────┐
│ 10. PRINCIPAL SCIENTIST DECISION                     │
│ - Tiếp tục nghiên cứu                                 │
│ - Gọi thêm executor                                   │
│ - Báo thiếu bằng chứng                                │
│ - Kết luận                                            │
└─────────────────────────────────────────────────────────┘
```

---

# 7. VAI TRÒ CODEX VÀ MODEL LOCAL

## 7.1. Nguyên tắc bắt buộc

**Codex không trực tiếp viết code sản phẩm.**

Codex chỉ đảm nhiệm:

- đọc kiến trúc;
- phân rã mục tiêu;
- tạo task;
- lập thứ tự phụ thuộc;
- chọn local executor;
- kiểm tra trạng thái;
- yêu cầu test/review;
- tổng hợp báo cáo;
- cập nhật documentation index;
- cập nhật codegraph;
- phát hiện project drift;
- dừng pipeline khi vi phạm contract.

Toàn bộ code phải được thực hiện bởi model local.

## 7.2. Vai trò Codex Cowork

```yaml
codex_cowork:
  role: orchestration_only

  allowed:
    - inspect_repository
    - read_architecture
    - create_task_contract
    - assign_local_executor
    - request_local_review
    - run_or_request_tests
    - compare_result_with_contract
    - update_task_status
    - update_architecture_index
    - trigger_codegraph_refresh
    - report_risk
    - propose_next_tasks

  forbidden:
    - implement_feature_code
    - edit_production_source_directly
    - bypass_local_executor
    - approve_own_implementation
    - merge_unverified_code
    - alter_architecture_without_decision_record
```

## 7.3. Local Software Department

```text
Local Architect
    ├── Local Coder
    ├── Local Test Engineer
    ├── Local Code Reviewer
    ├── Local Security Reviewer
    ├── Local Performance Analyst
    └── Local Documentation Builder
```

Một model có thể kiêm nhiều vai trò ở giai đoạn đầu, nhưng mỗi lần chạy phải mang một role contract riêng.

## 7.4. Quy trình code

```text
Codex tạo TaskContract
→ Local Architect lập implementation plan
→ Local Coder viết patch
→ Local Tester tạo/chạy test
→ Local Reviewer kiểm tra patch
→ Local Security/Performance review khi cần
→ Codex kiểm tra contract và evidence
→ Codegraph được cập nhật
→ Memory được cập nhật
→ Task đóng
```

## 7.5. Quy tắc độc lập

Model viết code không được là model duy nhất xác nhận code.

Tối thiểu:

```text
Coder != Reviewer perspective
Coder output must include tests
Reviewer must inspect diff
Codex does not count as code reviewer
```

---

# 8. TASK CONTRACT CHO PHÁT TRIỂN CODE

```yaml
task_contract:
  task_id: TASK-XXXX
  title: string

  objective:
    problem: string
    expected_outcome: string
    non_goals: []

  context:
    architecture_refs: []
    codegraph_nodes: []
    relevant_files: []
    prior_decisions: []

  constraints:
    language: string
    dependencies_allowed: []
    dependencies_forbidden: []
    performance_budget: {}
    security_requirements: []
    compatibility_requirements: []

  implementation:
    assigned_role: local_coder
    allowed_files: []
    forbidden_files: []
    expected_artifacts: []

  validation:
    acceptance_criteria: []
    required_tests: []
    regression_checks: []
    evidence_schema: string

  token_budget:
    max_context_tokens: integer
    max_output_tokens: integer
    required_summary_mode: string

  completion:
    status: open
    reviewer: local_reviewer
    codegraph_refresh_required: true
    memory_update_required: true
```

---

# 9. MEMORY ARCHITECTURE

Memory phải được phân tầng. Không đưa toàn bộ repository hoặc lịch sử chat vào mọi phiên.

## 9.1. Memory Map tổng thể

```text
memory/
├── 00-identity/
│   ├── project-charter.md
│   ├── model-identity.md
│   ├── non-negotiables.md
│   └── glossary.md
│
├── 01-architecture/
│   ├── system-overview.md
│   ├── module-map.md
│   ├── data-contracts.md
│   ├── runtime-loop.md
│   ├── adaptive-n.md
│   └── executor-architecture.md
│
├── 02-decisions/
│   ├── index.md
│   └── ADR-XXXX-*.md
│
├── 03-codegraph/
│   ├── codegraph.json
│   ├── codegraph-summary.md
│   ├── module-dependencies.md
│   ├── symbol-index.json
│   └── change-impact.md
│
├── 04-tasks/
│   ├── active/
│   ├── queued/
│   ├── completed/
│   └── failed/
│
├── 05-evidence/
│   ├── experiments/
│   ├── benchmarks/
│   ├── test-results/
│   └── rejected-hypotheses/
│
├── 06-learning/
│   ├── reusable-patterns.md
│   ├── failure-patterns.md
│   ├── executor-performance.md
│   └── distilled-lessons.md
│
├── 07-sessions/
│   ├── current-session.md
│   ├── handoff.md
│   └── archive/
│
└── index.md
```

## 9.2. Memory lớp 0 — Identity Memory

Luôn được đọc.

Chứa:

- mục tiêu;
- bản sắc model;
- nguyên tắc bất biến;
- Codex orchestration-only;
- local-only coding;
- định nghĩa các thuật ngữ.

Dung lượng mục tiêu: dưới 2.000 token.

## 9.3. Memory lớp 1 — Architecture Memory

Đọc theo module liên quan.

Chứa:

- sơ đồ module;
- interface;
- data schema;
- invariant;
- phụ thuộc cấp cao.

Không chứa toàn bộ source code.

## 9.4. Memory lớp 2 — Decision Memory

Mỗi quyết định dùng ADR.

```md
# ADR-XXXX: Tên quyết định

## Status
Proposed / Accepted / Superseded / Rejected

## Context

## Decision

## Alternatives

## Consequences

## Validation

## Related modules
```

Không được thay đổi kiến trúc quan trọng chỉ bằng commit message.

## 9.5. Memory lớp 3 — Codegraph Memory

Là bản đồ cấu trúc mã nguồn, không phải bản sao source code.

Chứa:

- module;
- file;
- class;
- function;
- imports;
- calls;
- interface;
- tests;
- owner;
- change frequency;
- risk score.

## 9.6. Memory lớp 4 — Task Memory

Mỗi task chỉ chứa context cần thiết cho task.

Không tự động nạp:

- toàn bộ chat;
- toàn bộ codebase;
- task cũ không liên quan;
- tài liệu nghiên cứu không liên quan.

## 9.7. Memory lớp 5 — Evidence Memory

Lưu:

- benchmark;
- kết quả test;
- experiment;
- falsified hypothesis;
- reproduction log.

Không biến kết quả một lần thành tri thức vĩnh viễn.

## 9.8. Memory lớp 6 — Learning Memory

Chỉ ghi bài học đã được xác minh hoặc xuất hiện lặp lại.

Ví dụ:

- pattern gây lỗi;
- module thường bị regression;
- local model nào phù hợp task nào;
- loại prompt nào gây hallucination;
- chiến lược context nào tiết kiệm token.

---

# 10. CODEGRAPH

## 10.1. Mục tiêu

Codegraph giúp:

- Codex hiểu codebase mà không đọc toàn bộ repository.
- Local model chỉ nhận các file và symbol liên quan.
- Phân tích impact trước khi sửa.
- Tránh sửa sai module.
- Giảm context input.
- Giảm độ trễ khi repository lớn.
- Phát hiện kiến trúc drift.

## 10.2. Node types

```text
Repository
Module
Package
File
Class
Function
Method
Schema
API
CLI
Test
Configuration
DatabaseEntity
ExternalDependency
ADR
Task
```

## 10.3. Edge types

```text
CONTAINS
IMPORTS
CALLS
IMPLEMENTS
EXTENDS
READS
WRITES
VALIDATES
TESTED_BY
CONFIGURED_BY
DEPENDS_ON
DECIDED_BY
MODIFIED_BY
GENERATES
```

## 10.4. Metadata

```json
{
  "node_id": "function:src/core/adaptive_n.py:calculate_target_n",
  "type": "Function",
  "path": "src/core/adaptive_n.py",
  "signature": "calculate_target_n(metrics, budget) -> int",
  "summary": "Tính số ThoughtState mục tiêu.",
  "dependencies": [],
  "dependents": [],
  "tests": [],
  "risk_score": 0.0,
  "last_changed_commit": "",
  "last_indexed_at": ""
}
```

## 10.5. Quy tắc cập nhật

Codegraph phải được cập nhật:

- sau mỗi patch được chấp nhận;
- sau rename/move;
- sau thay đổi interface;
- sau thay đổi dependency;
- sau thêm/xóa test;
- trước khi đóng task.

Không cần build lại toàn bộ graph sau mọi thay đổi.

Ưu tiên incremental update:

```text
git diff
→ xác định file thay đổi
→ parse symbol thay đổi
→ cập nhật node/edge bị ảnh hưởng
→ chạy dependency impact
→ ghi change-impact.md
```

## 10.6. Freshness invariant

```text
codegraph_commit == repository_HEAD
```

Nếu không bằng nhau:

```text
PROJECT_STATE = STALE_CODEGRAPH
```

Khi `STALE_CODEGRAPH`:

- Không mở task kiến trúc mới.
- Không cho Codex phân rã task sâu.
- Chỉ cho phép refresh graph hoặc task khẩn cấp có explicit override.

## 10.7. Codegraph summary

`codegraph-summary.md` phải trả lời nhanh:

- Dự án có những module nào?
- Module nào là core?
- Entry point ở đâu?
- Data flow chính là gì?
- Module nào có rủi ro cao?
- File nào thay đổi gần đây?
- Test coverage theo module?
- Có dependency cycle không?
- Kiến trúc thực tế có lệch tài liệu không?

---

# 11. GIẢI PHÁP TIẾT KIỆM TOKEN

## 11.1. Nguyên tắc

Không tối ưu token bằng cách làm model thiếu context.

Tối ưu bằng cách:

- chọn đúng context;
- cấu trúc context;
- nén context;
- tái sử dụng artifact;
- đọc theo graph;
- chỉ mở rộng khi cần.

## 11.2. Context Pyramid

```text
L0 — Identity capsule
L1 — Task contract
L2 — Relevant architecture nodes
L3 — Codegraph neighborhood
L4 — Selected source files
L5 — Exact code spans
L6 — Historical evidence on demand
```

Model chỉ bắt đầu với L0–L3.

L4–L6 chỉ được truy xuất khi cần.

## 11.3. Session Bootstrap Capsule

Mỗi phiên Codex/local model nhận một capsule ngắn:

```yaml
session_capsule:
  project: NPS Core
  role: local_coder
  task_id: TASK-XXXX
  objective: string
  invariants:
    - Codex orchestration-only
    - Production code by local model
    - Tests required
    - Codegraph must be fresh
  relevant_modules: []
  relevant_decisions: []
  allowed_files: []
  acceptance_criteria: []
```

Mục tiêu: dưới 1.500 token.

## 11.4. Symbol-level retrieval

Không gửi toàn bộ file nếu task chỉ liên quan một function.

Context gồm:

- signature;
- docstring;
- body;
- direct callers;
- direct callees;
- tests;
- interface constraints.

## 11.5. Graph-neighborhood retrieval

Mặc định lấy:

```text
target node
+ parent module
+ direct dependencies
+ direct dependents
+ relevant tests
+ related ADR
```

Không lấy toàn bộ repository.

## 11.6. Progressive disclosure

Quy trình:

```text
summary
→ symbol
→ surrounding file section
→ full file
→ adjacent module
```

Chỉ tăng context khi model báo thiếu thông tin có lý do.

## 11.7. Immutable artifact references

Không lặp lại nội dung dài của:

- architecture;
- schema;
- ADR;
- task contract;
- benchmark.

Thay bằng ID và digest:

```text
ARCH-NPS-V1
ADR-0012
SCHEMA-EVIDENCE-V2
TASK-0048
```

Model có thể yêu cầu mở rộng artifact cụ thể.

## 11.8. Diff-first workflow

Mỗi review chỉ nhận:

- task contract;
- relevant architecture;
- diff;
- surrounding symbols;
- tests;
- codegraph impact.

Không đọc lại toàn bộ codebase.

## 11.9. Handoff compression

Cuối mỗi phiên tạo `handoff.md`:

```md
# Session Handoff

## Completed

## Changed files

## Decisions made

## Open risks

## Failed attempts

## Next exact action

## Required context for next session
```

Dung lượng mục tiêu: 500–1.200 token.

## 11.10. Evidence deduplication

Mỗi evidence có content hash.

Nếu evidence mới trùng:

- không lưu bản sao;
- tăng reference count;
- ghi thêm provenance.

## 11.11. Semantic cache

Cache các truy vấn:

- module summary;
- symbol explanation;
- dependency neighborhood;
- test failure explanation;
- architecture lookup.

Cache invalidated theo commit hash.

## 11.12. Token budget theo vai trò

```yaml
token_policy:
  codex_orchestrator:
    input: low
    output: low
    focus: task routing and state

  local_architect:
    input: medium
    output: medium
    focus: implementation plan

  local_coder:
    input: targeted
    output: patch_only

  local_tester:
    input: targeted
    output: tests_and_results

  local_reviewer:
    input: diff_first
    output: findings_only

  documentation_builder:
    input: changed_artifacts
    output: incremental_docs
```

## 11.13. Không dùng chain-of-thought dài làm memory

Không lưu suy luận tự do dài.

Chỉ lưu:

- decision;
- evidence;
- assumptions;
- rejected alternatives;
- next action;
- confidence.

---

# 12. REPOSITORY ĐỀ XUẤT

```text
nps-core/
├── README.md
├── ARCHITECTURE.md
├── CONTRIBUTING.md
├── pyproject.toml
│
├── memory/
│   └── ...
│
├── schemas/
│   ├── thought_state.schema.json
│   ├── evidence_packet.schema.json
│   ├── task_contract.schema.json
│   └── experiment.schema.json
│
├── src/
│   └── nps_core/
│       ├── problem_compiler/
│       ├── hypothesis_population/
│       ├── thought_ecology/
│       ├── adaptive_n/
│       ├── experiment_designer/
│       ├── contract_generator/
│       ├── executor_router/
│       ├── evidence_assimilator/
│       ├── verification_tribunal/
│       ├── state_update/
│       ├── memory/
│       ├── codegraph/
│       └── interfaces/
│
├── local_department/
│   ├── roles/
│   ├── prompts/
│   ├── model_profiles/
│   └── routing/
│
├── orchestration/
│   ├── codex/
│   ├── workflows/
│   └── policies/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── architecture/
│   ├── adversarial/
│   └── benchmark/
│
├── experiments/
│   ├── hypothesis_branching/
│   ├── adaptive_n/
│   ├── information_gain/
│   ├── executor_diversity/
│   └── token_efficiency/
│
├── benchmarks/
├── scripts/
└── docs/
```

---

# 13. CÁC DATA CONTRACT CHÍNH

## 13.1. Evidence Packet

```json
{
  "evidence_id": "EV-XXXX",
  "task_id": "TASK-XXXX",
  "executor_id": "LOCAL-CODER-01",
  "claim": "",
  "result": "",
  "method": "",
  "artifacts": [],
  "confidence": 0.0,
  "limitations": [],
  "failure_modes": [],
  "reproducibility": {
    "command": "",
    "environment": "",
    "seed": null
  },
  "affected_hypotheses": [],
  "provenance": [],
  "content_hash": ""
}
```

## 13.2. Experiment Contract

```yaml
experiment:
  experiment_id: EXP-XXXX
  objective: string
  hypotheses_tested: []
  discriminating_outcomes: {}
  method: string
  executor_requirements: []
  cost_budget: {}
  stop_conditions: []
  expected_information_gain: float
  acceptance_schema: string
```

## 13.3. Executor Result

```yaml
executor_result:
  executor_id: string
  task_id: string
  status: success
  outputs: []
  evidence_packets: []
  tests: []
  uncertainties: []
  assumptions_added: []
  recommended_followups: []
```

---

# 14. VERIFICATION TRIBUNAL

Verification Tribunal không phải một agent duy nhất.

Nó là pipeline gồm:

1. Schema validation.
2. Provenance validation.
3. Consistency check.
4. Cross-executor comparison.
5. Reproduction check.
6. Formal validation khi phù hợp.
7. Statistical validation khi phù hợp.
8. Calibration update.
9. Conflict report.

## 14.1. Independence score

Hai executor không được tính là độc lập hoàn toàn nếu:

- cùng model nền;
- cùng prompt;
- cùng dữ liệu;
- cùng tool output;
- cùng implementation;
- cùng nguồn tham khảo.

## 14.2. Confidence update

Không dùng trung bình đơn giản.

Confidence phải xét:

- evidence quality;
- independence;
- reproducibility;
- method suitability;
- source reliability;
- contradiction severity;
- risk of shared failure.

---

# 15. PHƯƠNG ÁN CHƯNG CẤT

Chưng cất được sử dụng nhưng không tạo bản sắc cốt lõi.

## 15.1. Những gì có thể chưng cất

- Khả năng hiểu ngôn ngữ.
- Khởi tạo giả thuyết.
- Phân rã vấn đề.
- Thiết kế experiment.
- Chọn executor.
- Tạo contract.
- Đánh giá bằng chứng.
- Viết kết luận khoa học.

## 15.2. Những gì không được phụ thuộc hoàn toàn vào teacher

- Adaptive N.
- Thought graph.
- Branch/merge/prune.
- Evidence lifecycle.
- Verification policy.
- Memory governance.
- Runtime identity.
- Executor independence.
- Code orchestration policy.

## 15.3. Dataset ưu tiên

Không lưu chain-of-thought thô làm mục tiêu chính.

Mỗi mẫu nên gồm:

```text
problem
→ structured hypotheses
→ uncertainty map
→ experiment candidates
→ selected experiment
→ executor contracts
→ evidence packets
→ state updates
→ final decision
```

## 15.4. Teacher diversity

Teacher có thể gồm nhiều model, solver và con người.

Mục tiêu không phải lấy “câu trả lời hay nhất”, mà lấy:

- cách tạo giả thuyết;
- cách phản chứng;
- cách thiết kế phép đo;
- cách nhận biết thiếu dữ liệu;
- cách hiệu chỉnh độ tin cậy.

---

# 16. KẾ HOẠCH PHÁT TRIỂN

# Giai đoạn 0 — Foundation Freeze

## Mục tiêu

- Chốt charter.
- Chốt thuật ngữ.
- Chốt memory map.
- Chốt Codex/local boundary.
- Chốt repository skeleton.
- Chốt schema V1.

## Deliverables

- `ARCHITECTURE.md`
- `memory/index.md`
- 4 JSON schema
- Codex orchestration policy
- Local role contracts
- ADR template
- codegraph specification

## Exit criteria

- Không còn mâu thuẫn về vai trò Codex.
- Tất cả module có owner và interface sơ bộ.
- Codegraph freshness rule được định nghĩa.

---

# Giai đoạn 1 — Deterministic Runtime Prototype

## Mục tiêu

Xây runtime không cần model mới.

Dùng rule-based hoặc model local nhỏ để:

- tạo ThoughtState;
- branch;
- merge;
- prune;
- tạo experiment contract;
- ingest evidence;
- cập nhật graph.

## Không làm

- Train model.
- Soft-qubit simulator phức tạp.
- Tensor network lớn.
- Full autonomous system.

## Benchmark

- Logic puzzles.
- Root cause analysis nhỏ.
- Software debugging task có ground truth.
- Scientific hypothesis selection đơn giản.

## Exit criteria

- ThoughtState lifecycle chạy end-to-end.
- Evidence update ảnh hưởng nhiều hypothesis.
- N_h, N_v, N_e được tách đúng.
- Có test deterministic.

---

# Giai đoạn 2 — Local Software Department

## Mục tiêu

Xây pipeline code hoàn toàn bằng local model.

## Thành phần

- Local Architect.
- Local Coder.
- Local Tester.
- Local Reviewer.
- Local Docs Builder.
- Codex orchestration-only.

## Exit criteria

- Codex không ghi production code.
- Mọi patch có local author artifact.
- Mọi patch có test.
- Mọi task cập nhật codegraph.
- Handoff được sinh tự động.

---

# Giai đoạn 3 — Codegraph + Token-Efficient Context

## Mục tiêu

Giúp dự án không lag khi repository lớn.

## Thành phần

- AST parser.
- Symbol graph.
- Dependency graph.
- Incremental git-diff indexing.
- Graph neighborhood retrieval.
- Commit-bound cache.
- Context capsule generator.

## Benchmarks

- Token input/task.
- Time to first valid patch.
- Files read/task.
- Regression rate.
- Stale context incidents.

## Exit criteria

- Codegraph cập nhật incremental.
- Graph commit khớp HEAD.
- Context giảm đáng kể so với full repo.
- Không giảm tỷ lệ hoàn thành task.

---

# Giai đoạn 4 — Adaptive N + Experiment Designer

## Mục tiêu

Biến multi-hypothesis thành cơ chế có kiểm soát.

## Thành phần

- Complexity estimator.
- Uncertainty estimator.
- Diversity score.
- Thought deduplication.
- Information gain ranker.
- Experiment bundling.
- Budget controller.

## Exit criteria

- N thay đổi theo bài toán.
- Tư duy trùng được merge.
- Số executor thấp hơn số hypothesis.
- Experiment được chọn có khả năng phân biệt.

---

# Giai đoạn 5 — Verification Tribunal

## Mục tiêu

Không tin executor một cách mù quáng.

## Thành phần

- Cross-check.
- Reproduction.
- Independence score.
- Evidence conflict graph.
- Confidence calibration.
- Formal tools adapter.

## Exit criteria

- Phát hiện được correlated errors.
- Có conflict report.
- Có reproduction log.
- Confidence không tăng chỉ vì nhiều câu trả lời giống nhau.

---

# Giai đoạn 6 — Distillation Dataset

## Mục tiêu

Tạo dữ liệu huấn luyện theo cấu trúc NPS.

## Pipeline

```text
Task generation
→ Multi-teacher proposal
→ Structured extraction
→ Verification
→ Runtime replay
→ Quality filtering
→ Dataset versioning
```

## Exit criteria

- Dataset chứa state transition.
- Không chỉ chứa answer.
- Có rejected hypotheses.
- Có executor selection rationale.
- Có evidence provenance.
- Có benchmark split chống contamination.

---

# Giai đoạn 7 — Train NPS Student Model

## Mục tiêu

Train model ngôn ngữ nhỏ hỗ trợ NPS runtime.

## Model không phải toàn bộ NPS Core

Model chịu trách nhiệm:

- compile problem;
- propose hypothesis;
- propose experiment;
- generate contract;
- summarize evidence;
- propose state update.

Runtime chịu trách nhiệm:

- lifecycle;
- graph;
- constraints;
- budgets;
- routing;
- verification;
- memory.

## Exit criteria

- Thay teacher bằng student mà runtime vẫn hoạt động.
- Model local đáp ứng latency mục tiêu.
- Không mất bản sắc khi đổi backbone.
- Benchmark vượt single-chain baseline.

---

# Giai đoạn 8 — Scientific Principal Model

## Mục tiêu

Thử nghiệm ở các miền:

- software engineering;
- system design;
- scientific literature synthesis;
- engineering optimization;
- research planning;
- root cause investigation.

## Tiêu chí

- Không chỉ trả lời đúng.
- Biết khi nào chưa đủ bằng chứng.
- Chọn đúng executor.
- Thiết kế test hữu ích.
- Giảm chi phí tìm lời giải.
- Có audit trail.

---

# 17. BENCHMARK CỐT LÕI

## 17.1. Baselines

So sánh với:

- single LLM chain;
- self-consistency;
- tree-of-thought;
- debate agents;
- fixed multi-agent;
- planner-executor;
- NPS adaptive population.

## 17.2. Metrics

```text
Answer correctness
Calibration error
Hypothesis diversity
Hypothesis redundancy
Information gain per executor call
Executor calls per solved task
Token cost
Wall-clock time
Reproducibility
Evidence trace completeness
Regression rate
Architecture drift
```

## 17.3. Benchmark token efficiency

```text
useful_output_tokens / total_input_tokens
```

Thêm:

```text
correct_tasks / million_input_tokens
```

---

# 18. RỦI RO

## 18.1. Bùng nổ hypothesis

Giải pháp:

- diversity threshold;
- hard budget;
- merge;
- dormant state;
- information gain gate.

## 18.2. N agent nhưng cùng sai

Giải pháp:

- independence score;
- model diversity;
- method diversity;
- source diversity;
- reproduction.

## 18.3. Codex vượt quyền

Giải pháp:

- policy file;
- write protection;
- audit log;
- local author metadata;
- CI rule.

## 18.4. Local model thiếu năng lực

Giải pháp:

- chia task nhỏ;
- role-specific prompt;
- retrieval đúng symbol;
- tool-assisted testing;
- local model routing;
- escalation contract.

## 18.5. Codegraph stale

Giải pháp:

- commit invariant;
- CI check;
- incremental index;
- block task closure.

## 18.6. Memory phình to

Giải pháp:

- layered memory;
- TTL cho session;
- summarize then archive;
- hash deduplication;
- load on demand.

## 18.7. “Lượng tử hóa” ngôn ngữ nhưng không có thuật toán

Giải pháp:

- mọi khái niệm phải có:
  - data structure;
  - algorithm;
  - invariant;
  - benchmark;
  - failure case.

---

# 19. NGUYÊN TẮC BẤT BIẾN

```text
INV-01: Codex chỉ điều phối.
INV-02: Production code do model local thực hiện.
INV-03: Mọi patch phải có test hoặc lý do miễn test.
INV-04: Codegraph phải khớp repository HEAD.
INV-05: Không đồng nhất N hypothesis với N executor.
INV-06: Không lưu chain-of-thought dài làm memory.
INV-07: Mọi evidence phải có provenance.
INV-08: Nhiều executor giống nhau không được coi là độc lập.
INV-09: Chưng cất không thay thế runtime identity.
INV-10: Mọi thay đổi kiến trúc phải có ADR.
INV-11: Model phải được phép kết luận “chưa đủ bằng chứng”.
INV-12: Context phải được truy xuất theo task và codegraph.
```

---

# 20. WORKFLOW CHUẨN CHO MỖI TASK CODE

```text
1. Codex đọc Identity Capsule.
2. Codex kiểm tra codegraph freshness.
3. Codex truy xuất neighborhood liên quan.
4. Codex tạo TaskContract.
5. Local Architect lập plan.
6. Local Coder tạo patch.
7. Local Tester tạo và chạy test.
8. Local Reviewer review diff.
9. Local executor sửa lỗi nếu có.
10. Codex đối chiếu acceptance criteria.
11. Cập nhật codegraph incremental.
12. Cập nhật ADR/memory nếu cần.
13. Tạo handoff.
14. Đóng task.
```

---

# 21. WORKFLOW CHUẨN CHO MỖI TASK NGHIÊN CỨU

```text
1. Compile ProblemGraph.
2. Sinh N_h hypothesis.
3. Đo diversity và deduplicate.
4. Xây contradiction/dependency graph.
5. Xác định uncertainty frontier.
6. Sinh experiment candidates.
7. Xếp hạng information gain/cost.
8. Gom task và tạo N_v.
9. Chọn N_e executor.
10. Thu evidence packet.
11. Kiểm tra independence.
12. Verification Tribunal.
13. Cập nhật toàn bộ ThoughtState liên quan.
14. Prune/merge/branch.
15. Kết luận hoặc lặp.
```

---

# 22. FILE ĐỌC ĐẦU TIÊN CHO CODEX

Codex phải đọc theo thứ tự:

```text
1. memory/00-identity/project-charter.md
2. memory/00-identity/non-negotiables.md
3. memory/07-sessions/handoff.md
4. memory/03-codegraph/codegraph-summary.md
5. task contract hiện tại
6. ADR liên quan
7. symbol/file được codegraph chỉ định
```

Codex không được mặc định đọc toàn bộ repository.

---

# 23. FILE ĐỌC ĐẦU TIÊN CHO LOCAL CODER

```text
1. Role contract
2. Task contract
3. Relevant architecture excerpt
4. Relevant codegraph neighborhood
5. Target symbols
6. Direct tests
7. Acceptance criteria
```

---

# 24. DEFINITION OF DONE

Một task chỉ hoàn tất khi:

- Code được tạo bởi local model.
- Acceptance criteria đạt.
- Test pass.
- Review hoàn tất.
- Không có unresolved critical finding.
- Codegraph đã cập nhật.
- Memory/handoff đã cập nhật.
- Architecture drift được kiểm tra.
- Evidence artifact tồn tại.
- Commit hoặc patch có thể tái lập.

---

# 25. ƯU TIÊN TRIỂN KHAI NGAY

## Priority 0

- Tạo repository skeleton.
- Tạo memory tree.
- Tạo invariants.
- Tạo Codex policy.
- Tạo TaskContract schema.
- Tạo ThoughtState schema.
- Tạo EvidencePacket schema.

## Priority 1

- Xây codegraph indexer tối thiểu.
- Xây graph summary.
- Xây incremental refresh.
- Xây context capsule generator.

## Priority 2

- Xây deterministic ThoughtState runtime.
- Branch/merge/prune.
- Evidence update.
- Experiment contract.

## Priority 3

- Tích hợp local software department.
- Codex orchestration workflow.
- Local coder/tester/reviewer prompts.
- End-to-end code task thử nghiệm.

## Priority 4

- Adaptive N.
- Information gain.
- Executor diversity.
- Verification Tribunal.

## Priority 5

- Dataset và distillation.
- Student model.
- Benchmark với baseline.

---

# 26. KẾT LUẬN KIẾN TRÚC V1

NPS Core không cố xây một LLM biết mọi thứ.

Nó xây một nhà khoa học trưởng có khả năng:

- nghĩ theo quần thể giả thuyết;
- nhận biết điều chưa biết;
- thiết kế phép kiểm chứng;
- giao đúng người làm;
- kiểm tra bằng chứng;
- cập nhật nhiều tư duy cùng lúc;
- hội tụ một cách có kiểm soát.

Các khái niệm polyhedral, unitary, tensor hay soft-qubit được giữ như nguồn cảm hứng và các hướng nghiên cứu có thể thử nghiệm. Chúng không được phép trở thành tuyên bố kỹ thuật nếu chưa có data structure, thuật toán và benchmark chứng minh.

Trong phát triển phần mềm:

- Codex là người điều phối.
- Model local là đội thực thi.
- Codegraph là bản đồ sống.
- Memory được phân tầng.
- Context được truy xuất theo graph.
- Token được dùng cho phần liên quan nhất.
- Mọi thay đổi đều có evidence và audit trail.

Đây là baseline chính thức cho giai đoạn phát triển đầu tiên của dự án.

---

# PHỤ LỤC A — PROJECT CHARTER RÚT GỌN

```yaml
project:
  name: NPS Core
  mission: >
    Xây dựng Principal Scientist Model duy trì quần thể giả thuyết thích nghi,
    thiết kế phép kiểm chứng và điều phối executor độc lập.

  identity:
    - population_reasoning
    - delegated_cognition
    - experimental_intelligence
    - evidence_economy
    - epistemic_identity
    - runtime_identity

  software_policy:
    codex: orchestration_only
    implementation: local_models_only
    verification: independent_local_roles
    codegraph: mandatory_and_fresh

  optimization:
    - layered_memory
    - graph_retrieval
    - progressive_context
    - diff_first_review
    - incremental_indexing
    - artifact_references
```

# PHỤ LỤC B — CHECKLIST KIỂM TRA DRIFT

```text
[ ] Codex có viết production code không?
[ ] Code có phải do local model tạo không?
[ ] Có task contract không?
[ ] Có test không?
[ ] Có reviewer độc lập không?
[ ] Codegraph có khớp HEAD không?
[ ] Có ADR cho thay đổi kiến trúc không?
[ ] Memory có bị nhồi toàn bộ lịch sử không?
[ ] Có gửi file không liên quan vào context không?
[ ] N hypothesis có bị biến thành N agent giống nhau không?
[ ] Evidence có provenance không?
[ ] Confidence có xét independence không?
[ ] Có benchmark chống lại single-chain baseline không?
```

# PHỤ LỤC C — TRẠNG THÁI TÀI LIỆU

```yaml
document:
  id: ARCH-NPS-V1
  version: 1.0.0
  status: final_baseline
  supersedes:
    - Gemini raw specification
    - DeepSeek Unitary Reasoner draft
    - Grok hybrid synthesis
  next_review_trigger:
    - deterministic runtime completed
    - codegraph prototype completed
    - first end-to-end local coding pipeline completed
```

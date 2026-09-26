# Tài Liệu Định Hướng Kỹ Thuật (Technical Direction)

> [!IMPORTANT]
> **QUY ƯỚC BẮT BUỘC DÀNH CHO AGENT KẾ THỪA & CHỈNH SỬA TÀI LIỆU:**
> 1. **Ghi chú bắt buộc (Changelog):** Bất kỳ agent nào chỉnh sửa tài liệu này PHẢI bổ sung ghi chú tại mục Lịch Sử Thay Đổi (Tên/ID Agent, thời gian, lý do thay đổi).
> 2. **Chỉ cô lập, KHÔNG xóa bỏ:** TUYỆT ĐỐI KHÔNG xóa bỏ các nội dung/kiến trúc cũ. Toàn bộ nội dung muốn thay đổi phải được đóng khung cô lập và đánh dấu `[ISOLATED / DEPRECATED / REPLACED]`.
> 3. **Đồng bộ D:\2brain đầy đủ:** Đồng bộ và cập nhật đầy đủ mọi thay đổi, quyết định và bài học vào kho tri thức trung tâm `D:\2brain`.

---

> **Vai trò trong bộ 5 tài liệu chuẩn (26/09/2026):** **#2 — Định hướng kỹ thuật.** Gom các bản phân tích, chiến lược và kế hoạch kỹ thuật: NPS Core, giới thiệu, nỗi đau/giải pháp, context strategy, knowledge map, test chain, MoE, orchestration. Hết `PLAN_3DAY` / `PLAN_PHASE0` / bản V5 rải rác.

> Bộ 5 doc thay cho nạn tài liệu thô / tài liệu sửa đổi / v1-v2-v3 rải rác. Xem [→ `docs/TREE_MAP_AND_CHANGELOG.md`](TREE_MAP_AND_CHANGELOG.md) để biết tài liệu nào gom về đâu.

---

## Mục lục

- [Nguồn & trạng thái](#nguồn--trạng-thái)
- [Phần 1 — NPS Core: Kiến trúc Principal Scientist Model](#phần-1-nps-core-kiến-trúc-principal-scientist-model)
- [Phần 2 — Giới thiệu ViVy: AI That You Own](#phần-2-giới-thiệu-vivy-ai-that-you-own)
- [Phần 3 — Nỗi đau, giải pháp & kiến trúc](#phần-3-nỗi-đau-giải-pháp-kiến-trúc)
- [Phần 4 — Context Strategy](#phần-4-context-strategy)
- [Phần 5 — System Knowledge Map (bản đồ tri thức 91sViVy)](#phần-5-system-knowledge-map-bản-đồ-tri-thức-91svivy)
- [Phần 6 — Chuỗi test & thực nghiệm (TEST_CHAIN_PLAN)](#phần-6-chuỗi-test-thực-nghiệm-test_chain_plan)
- [Phần 7 — Phân tích kiến trúc Mixture-of-Experts](#phần-7-phân-tích-kiến-trúc-mixture-of-experts)
- [Phần 8 — Phương án đào tạo ViVy 40B Sparse MoE](#phần-8-phương-án-đào-tạo-vivy-40b-sparse-moe)
- [Phần 9 — Thảo luận kiến trúc Orchestration & Coupling](#phần-9-thảo-luận-kiến-trúc-orchestration-coupling)
- [Phần 10 — Plan-tune Orchestration (TD-1 → TD-8)](#phần-10-plan-tune-orchestration-td-1-td-8)

---

## Nguồn & trạng thái

| # | File nguồn | Trạng thái | Mục trong tài liệu này |
|:--|:--|:--|:--|
| 1 | `Vivy_final/docs/ARCHITECTURE.md` | [ISOLATED 26/09/2026] | Phần 1 — NPS Core: Kiến trúc Principal Scientist Model |
| 2 | `old-docs/11-consolidated-source-2026-09-26/INTRODUCTION.md` | [ISOLATED 26/09/2026] | Phần 2 — Giới thiệu ViVy: AI That You Own |
| 3 | `old-docs/11-consolidated-source-2026-09-26/PAIN_POINTS_AND_SOLUTIONS.md` | [ISOLATED 26/09/2026] | Phần 3 — Nỗi đau, giải pháp & kiến trúc |
| 4 | `old-docs/11-consolidated-source-2026-09-26/CONTEXT_STRATEGY.md` | [ISOLATED 26/09/2026] | Phần 4 — Context Strategy |
| 5 | `old-docs/11-consolidated-source-2026-09-26/SYSTEM_KNOWLEDGE_MAP.md` | [ISOLATED 26/09/2026] | Phần 5 — System Knowledge Map (bản đồ tri thức 91sViVy) |
| 6 | `old-docs/11-consolidated-source-2026-09-26/TEST_CHAIN_PLAN.md` | [ISOLATED 26/09/2026] | Phần 6 — Chuỗi test & thực nghiệm (TEST_CHAIN_PLAN) |
| 7 | `old-docs/11-consolidated-source-2026-09-26/VIVY_MOE_ARCHITECTURE_ANALYSIS.md` | [ISOLATED 26/09/2026] | Phần 7 — Phân tích kiến trúc Mixture-of-Experts |
| 8 | `old-docs/11-consolidated-source-2026-09-26/VIVY_MOE_40B_TRAINING_PLAN.md` | [ISOLATED 26/09/2026] | Phần 8 — Phương án đào tạo ViVy 40B Sparse MoE |
| 9 | `old-docs/11-consolidated-source-2026-09-26/plans/DISCUSSION_VIVY_ORCHESTRATION_2026-09-25.md` | [ISOLATED 26/09/2026] | Phần 9 — Thảo luận kiến trúc Orchestration & Coupling |
| 10 | `old-docs/11-consolidated-source-2026-09-26/plans/plan-tune-vivy-orchestration-2026-09-25.md` | [ISOLATED 26/09/2026] | Phần 10 — Plan-tune Orchestration (TD-1 → TD-8) |

> **Trạng thái:** `[ISOLATED 26/09/2026]` = bản gốc đã cô lập, nội dung đã gom vào đây. `[ISOLATED → PHỤ LỤC]` = chỉ ghi chú cô lập, bản đầy đủ vẫn nằm ở file nguồn.
>
> **Vị trí bản gốc:** đường dẫn `old-docs/11-consolidated-source-2026-09-26/` là nơi bản gốc được di về sau khi gom (26/09/2026) — trước đó nằm ở `Vivy_final/docs/`. Các đường dẫn `old-docs/01…10-*` là kho lưu trữ có sẵn từ trước, file vẫn nằm nguyên tại đó (chỉ thêm banner `[ISOLATED]`). **Không có nội dung nào bị xóa** (Quy tắc 4).

---

## Phần 1 — NPS Core: Kiến trúc Principal Scientist Model

> **Nguồn:** `Vivy_final/docs/ARCHITECTURE.md` — `[ISOLATED 26/09/2026]`

### NPS CORE — KIẾN TRÚC PRINCIPAL SCIENTIST MODEL
#### Tài liệu kiến trúc V1.0 Final

**Tên kiến trúc:** N-Thought Principal Scientist Core  
**Tên viết tắt:** NPS Core  
**Trạng thái:** Architecture Baseline — V1.0 Final  
**Ngày:** 23/07/2026  
**Ngôn ngữ tài liệu:** Tiếng Việt  
**Mục đích:** Là tài liệu gốc để con người, Codex Cowork và các model local hiểu nhanh toàn bộ định hướng, nguyên tắc và lộ trình phát triển dự án.

---

### 0. TUYÊN BỐ DỰ ÁN

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

### 1. VỊ TRÍ CỦA BA TÀI LIỆU NGUỒN

Ba tài liệu ban đầu được coi là **dữ liệu tư duy thô**, không phải đặc tả kỹ thuật cuối cùng.

#### 1.1. Tài liệu Gemini

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

#### 1.2. Tài liệu DeepSeek

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

#### 1.3. Tài liệu Grok

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

### 2. BẢN SẮC NHẬN THỨC CỦA MODEL

Bản sắc của NPS Core không nằm ở tên model nền, số tham số hay một thuật ngữ lượng tử.

Bản sắc nằm trong sáu cơ chế bắt buộc:

#### 2.1. Population Reasoning

Model duy trì một quần thể tư duy thay vì một chuỗi suy luận duy nhất.

Mỗi tư duy là một đối tượng trạng thái có cấu trúc, không phải một đoạn văn tự do.

#### 2.2. Delegated Cognition

Model biết phân biệt:

- Việc cần tự suy nghĩ.
- Việc cần lập kế hoạch.
- Việc cần giao model local.
- Việc cần solver.
- Việc cần simulator.
- Việc cần search/research.
- Việc cần con người xác nhận.

#### 2.3. Experimental Intelligence

Model không chỉ tìm câu trả lời.

Model tìm:

> Phép kiểm chứng rẻ nhất, nhanh nhất và có khả năng làm giảm bất định nhiều nhất.

#### 2.4. Evidence Economy

Executor không trả về “ý kiến”.

Executor trả về các evidence packet chuẩn hóa, có:

- claim;
- phương pháp;
- dữ liệu;
- độ tin cậy;
- giới hạn;
- khả năng tái lập;
- giả thuyết bị ảnh hưởng.

#### 2.5. Epistemic Identity

Model phải luôn phân biệt:

- fact;
- assumption;
- hypothesis;
- inference;
- external report;
- verified result;
- disputed result;
- unresolved uncertainty.

#### 2.6. Runtime Identity

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

### 3. ĐƠN VỊ CƠ BẢN: THOUGHT STATE

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

### 4. BA GIÁ TRỊ N TÁCH BIỆT

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

### 5. ADAPTIVE N CONTROLLER

#### 5.1. Mục tiêu

Adaptive N Controller quyết định:

- Khi nào tạo thêm tư duy.
- Khi nào dừng phân nhánh.
- Khi nào gộp tư duy.
- Khi nào tạm đóng băng tư duy.
- Khi nào cần thêm executor.
- Khi nào ngân sách không cho phép mở rộng.

#### 5.2. Công thức bootstrap

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

#### 5.3. Cơ chế mục tiêu dài hạn

Một tư duy mới chỉ được tạo khi thỏa ít nhất một điều kiện:

- Bao phủ vùng giả thuyết chưa có đại diện.
- Tạo dự đoán khác biệt có thể kiểm chứng.
- Phá vỡ một giả định nền đang bị dùng chung.
- Giải thích được bằng chứng mà các tư duy hiện tại không giải thích được.
- Có expected information gain vượt ngưỡng.

#### 5.4. Điều kiện prune

Một ThoughtState bị prune khi:

- Trùng lặp ngữ nghĩa vượt ngưỡng.
- Không tạo ra dự đoán phân biệt.
- Chi phí kiểm chứng quá cao so với giá trị.
- Bị formal constraint bác bỏ.
- Bị evidence mạnh bác bỏ.
- Không còn ảnh hưởng đến quyết định cuối.

#### 5.5. Điều kiện merge

Hai tư duy được merge khi:

- Cùng giả thuyết cốt lõi.
- Khác nhau chủ yếu ở cách diễn đạt.
- Chia sẻ phần lớn assumption.
- Có verification plan tương đương.
- Không tạo ra kết quả dự báo khác biệt đáng kể.

---

### 6. KIẾN TRÚC HỆ THỐNG

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

### 7. VAI TRÒ CODEX VÀ MODEL LOCAL

#### 7.1. Nguyên tắc bắt buộc

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

#### 7.2. Vai trò Codex Cowork

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

#### 7.3. Local Software Department

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

#### 7.4. Quy trình code

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

#### 7.5. Quy tắc độc lập

Model viết code không được là model duy nhất xác nhận code.

Tối thiểu:

```text
Coder != Reviewer perspective
Coder output must include tests
Reviewer must inspect diff
Codex does not count as code reviewer
```

---

### 8. TASK CONTRACT CHO PHÁT TRIỂN CODE

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

### 9. MEMORY ARCHITECTURE

Memory phải được phân tầng. Không đưa toàn bộ repository hoặc lịch sử chat vào mọi phiên.

#### 9.1. Memory Map tổng thể

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

#### 9.2. Memory lớp 0 — Identity Memory

Luôn được đọc.

Chứa:

- mục tiêu;
- bản sắc model;
- nguyên tắc bất biến;
- Codex orchestration-only;
- local-only coding;
- định nghĩa các thuật ngữ.

Dung lượng mục tiêu: dưới 2.000 token.

#### 9.3. Memory lớp 1 — Architecture Memory

Đọc theo module liên quan.

Chứa:

- sơ đồ module;
- interface;
- data schema;
- invariant;
- phụ thuộc cấp cao.

Không chứa toàn bộ source code.

#### 9.4. Memory lớp 2 — Decision Memory

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

#### 9.5. Memory lớp 3 — Codegraph Memory

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

#### 9.6. Memory lớp 4 — Task Memory

Mỗi task chỉ chứa context cần thiết cho task.

Không tự động nạp:

- toàn bộ chat;
- toàn bộ codebase;
- task cũ không liên quan;
- tài liệu nghiên cứu không liên quan.

#### 9.7. Memory lớp 5 — Evidence Memory

Lưu:

- benchmark;
- kết quả test;
- experiment;
- falsified hypothesis;
- reproduction log.

Không biến kết quả một lần thành tri thức vĩnh viễn.

#### 9.8. Memory lớp 6 — Learning Memory

Chỉ ghi bài học đã được xác minh hoặc xuất hiện lặp lại.

Ví dụ:

- pattern gây lỗi;
- module thường bị regression;
- local model nào phù hợp task nào;
- loại prompt nào gây hallucination;
- chiến lược context nào tiết kiệm token.

---

### 10. CODEGRAPH

#### 10.1. Mục tiêu

Codegraph giúp:

- Codex hiểu codebase mà không đọc toàn bộ repository.
- Local model chỉ nhận các file và symbol liên quan.
- Phân tích impact trước khi sửa.
- Tránh sửa sai module.
- Giảm context input.
- Giảm độ trễ khi repository lớn.
- Phát hiện kiến trúc drift.

#### 10.2. Node types

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

#### 10.3. Edge types

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

#### 10.4. Metadata

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

#### 10.5. Quy tắc cập nhật

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

#### 10.6. Freshness invariant

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

#### 10.7. Codegraph summary

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

### 11. GIẢI PHÁP TIẾT KIỆM TOKEN

#### 11.1. Nguyên tắc

Không tối ưu token bằng cách làm model thiếu context.

Tối ưu bằng cách:

- chọn đúng context;
- cấu trúc context;
- nén context;
- tái sử dụng artifact;
- đọc theo graph;
- chỉ mở rộng khi cần.

#### 11.2. Context Pyramid

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

#### 11.3. Session Bootstrap Capsule

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

#### 11.4. Symbol-level retrieval

Không gửi toàn bộ file nếu task chỉ liên quan một function.

Context gồm:

- signature;
- docstring;
- body;
- direct callers;
- direct callees;
- tests;
- interface constraints.

#### 11.5. Graph-neighborhood retrieval

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

#### 11.6. Progressive disclosure

Quy trình:

```text
summary
→ symbol
→ surrounding file section
→ full file
→ adjacent module
```

Chỉ tăng context khi model báo thiếu thông tin có lý do.

#### 11.7. Immutable artifact references

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

#### 11.8. Diff-first workflow

Mỗi review chỉ nhận:

- task contract;
- relevant architecture;
- diff;
- surrounding symbols;
- tests;
- codegraph impact.

Không đọc lại toàn bộ codebase.

#### 11.9. Handoff compression

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

#### 11.10. Evidence deduplication

Mỗi evidence có content hash.

Nếu evidence mới trùng:

- không lưu bản sao;
- tăng reference count;
- ghi thêm provenance.

#### 11.11. Semantic cache

Cache các truy vấn:

- module summary;
- symbol explanation;
- dependency neighborhood;
- test failure explanation;
- architecture lookup.

Cache invalidated theo commit hash.

#### 11.12. Token budget theo vai trò

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

#### 11.13. Không dùng chain-of-thought dài làm memory

Không lưu suy luận tự do dài.

Chỉ lưu:

- decision;
- evidence;
- assumptions;
- rejected alternatives;
- next action;
- confidence.

---

### 12. REPOSITORY ĐỀ XUẤT

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

### 13. CÁC DATA CONTRACT CHÍNH

#### 13.1. Evidence Packet

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

#### 13.2. Experiment Contract

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

#### 13.3. Executor Result

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

### 14. VERIFICATION TRIBUNAL

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

#### 14.1. Independence score

Hai executor không được tính là độc lập hoàn toàn nếu:

- cùng model nền;
- cùng prompt;
- cùng dữ liệu;
- cùng tool output;
- cùng implementation;
- cùng nguồn tham khảo.

#### 14.2. Confidence update

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

### 15. PHƯƠNG ÁN CHƯNG CẤT

Chưng cất được sử dụng nhưng không tạo bản sắc cốt lõi.

#### 15.1. Những gì có thể chưng cất

- Khả năng hiểu ngôn ngữ.
- Khởi tạo giả thuyết.
- Phân rã vấn đề.
- Thiết kế experiment.
- Chọn executor.
- Tạo contract.
- Đánh giá bằng chứng.
- Viết kết luận khoa học.

#### 15.2. Những gì không được phụ thuộc hoàn toàn vào teacher

- Adaptive N.
- Thought graph.
- Branch/merge/prune.
- Evidence lifecycle.
- Verification policy.
- Memory governance.
- Runtime identity.
- Executor independence.
- Code orchestration policy.

#### 15.3. Dataset ưu tiên

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

#### 15.4. Teacher diversity

Teacher có thể gồm nhiều model, solver và con người.

Mục tiêu không phải lấy “câu trả lời hay nhất”, mà lấy:

- cách tạo giả thuyết;
- cách phản chứng;
- cách thiết kế phép đo;
- cách nhận biết thiếu dữ liệu;
- cách hiệu chỉnh độ tin cậy.

---

### 16. KẾ HOẠCH PHÁT TRIỂN

### Giai đoạn 0 — Foundation Freeze

#### Mục tiêu

- Chốt charter.
- Chốt thuật ngữ.
- Chốt memory map.
- Chốt Codex/local boundary.
- Chốt repository skeleton.
- Chốt schema V1.

#### Deliverables

- `ARCHITECTURE.md`
- `memory/index.md`
- 4 JSON schema
- Codex orchestration policy
- Local role contracts
- ADR template
- codegraph specification

#### Exit criteria

- Không còn mâu thuẫn về vai trò Codex.
- Tất cả module có owner và interface sơ bộ.
- Codegraph freshness rule được định nghĩa.

---

### Giai đoạn 1 — Deterministic Runtime Prototype

#### Mục tiêu

Xây runtime không cần model mới.

Dùng rule-based hoặc model local nhỏ để:

- tạo ThoughtState;
- branch;
- merge;
- prune;
- tạo experiment contract;
- ingest evidence;
- cập nhật graph.

#### Không làm

- Train model.
- Soft-qubit simulator phức tạp.
- Tensor network lớn.
- Full autonomous system.

#### Benchmark

- Logic puzzles.
- Root cause analysis nhỏ.
- Software debugging task có ground truth.
- Scientific hypothesis selection đơn giản.

#### Exit criteria

- ThoughtState lifecycle chạy end-to-end.
- Evidence update ảnh hưởng nhiều hypothesis.
- N_h, N_v, N_e được tách đúng.
- Có test deterministic.

---

### Giai đoạn 2 — Local Software Department

#### Mục tiêu

Xây pipeline code hoàn toàn bằng local model.

#### Thành phần

- Local Architect.
- Local Coder.
- Local Tester.
- Local Reviewer.
- Local Docs Builder.
- Codex orchestration-only.

#### Exit criteria

- Codex không ghi production code.
- Mọi patch có local author artifact.
- Mọi patch có test.
- Mọi task cập nhật codegraph.
- Handoff được sinh tự động.

---

### Giai đoạn 3 — Codegraph + Token-Efficient Context

#### Mục tiêu

Giúp dự án không lag khi repository lớn.

#### Thành phần

- AST parser.
- Symbol graph.
- Dependency graph.
- Incremental git-diff indexing.
- Graph neighborhood retrieval.
- Commit-bound cache.
- Context capsule generator.

#### Benchmarks

- Token input/task.
- Time to first valid patch.
- Files read/task.
- Regression rate.
- Stale context incidents.

#### Exit criteria

- Codegraph cập nhật incremental.
- Graph commit khớp HEAD.
- Context giảm đáng kể so với full repo.
- Không giảm tỷ lệ hoàn thành task.

---

### Giai đoạn 4 — Adaptive N + Experiment Designer

#### Mục tiêu

Biến multi-hypothesis thành cơ chế có kiểm soát.

#### Thành phần

- Complexity estimator.
- Uncertainty estimator.
- Diversity score.
- Thought deduplication.
- Information gain ranker.
- Experiment bundling.
- Budget controller.

#### Exit criteria

- N thay đổi theo bài toán.
- Tư duy trùng được merge.
- Số executor thấp hơn số hypothesis.
- Experiment được chọn có khả năng phân biệt.

---

### Giai đoạn 5 — Verification Tribunal

#### Mục tiêu

Không tin executor một cách mù quáng.

#### Thành phần

- Cross-check.
- Reproduction.
- Independence score.
- Evidence conflict graph.
- Confidence calibration.
- Formal tools adapter.

#### Exit criteria

- Phát hiện được correlated errors.
- Có conflict report.
- Có reproduction log.
- Confidence không tăng chỉ vì nhiều câu trả lời giống nhau.

---

### Giai đoạn 6 — Distillation Dataset

#### Mục tiêu

Tạo dữ liệu huấn luyện theo cấu trúc NPS.

#### Pipeline

```text
Task generation
→ Multi-teacher proposal
→ Structured extraction
→ Verification
→ Runtime replay
→ Quality filtering
→ Dataset versioning
```

#### Exit criteria

- Dataset chứa state transition.
- Không chỉ chứa answer.
- Có rejected hypotheses.
- Có executor selection rationale.
- Có evidence provenance.
- Có benchmark split chống contamination.

---

### Giai đoạn 7 — Train NPS Student Model

#### Mục tiêu

Train model ngôn ngữ nhỏ hỗ trợ NPS runtime.

#### Model không phải toàn bộ NPS Core

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

#### Exit criteria

- Thay teacher bằng student mà runtime vẫn hoạt động.
- Model local đáp ứng latency mục tiêu.
- Không mất bản sắc khi đổi backbone.
- Benchmark vượt single-chain baseline.

---

### Giai đoạn 8 — Scientific Principal Model

#### Mục tiêu

Thử nghiệm ở các miền:

- software engineering;
- system design;
- scientific literature synthesis;
- engineering optimization;
- research planning;
- root cause investigation.

#### Tiêu chí

- Không chỉ trả lời đúng.
- Biết khi nào chưa đủ bằng chứng.
- Chọn đúng executor.
- Thiết kế test hữu ích.
- Giảm chi phí tìm lời giải.
- Có audit trail.

---

### 17. BENCHMARK CỐT LÕI

#### 17.1. Baselines

So sánh với:

- single LLM chain;
- self-consistency;
- tree-of-thought;
- debate agents;
- fixed multi-agent;
- planner-executor;
- NPS adaptive population.

#### 17.2. Metrics

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

#### 17.3. Benchmark token efficiency

```text
useful_output_tokens / total_input_tokens
```

Thêm:

```text
correct_tasks / million_input_tokens
```

---

### 18. RỦI RO

#### 18.1. Bùng nổ hypothesis

Giải pháp:

- diversity threshold;
- hard budget;
- merge;
- dormant state;
- information gain gate.

#### 18.2. N agent nhưng cùng sai

Giải pháp:

- independence score;
- model diversity;
- method diversity;
- source diversity;
- reproduction.

#### 18.3. Codex vượt quyền

Giải pháp:

- policy file;
- write protection;
- audit log;
- local author metadata;
- CI rule.

#### 18.4. Local model thiếu năng lực

Giải pháp:

- chia task nhỏ;
- role-specific prompt;
- retrieval đúng symbol;
- tool-assisted testing;
- local model routing;
- escalation contract.

#### 18.5. Codegraph stale

Giải pháp:

- commit invariant;
- CI check;
- incremental index;
- block task closure.

#### 18.6. Memory phình to

Giải pháp:

- layered memory;
- TTL cho session;
- summarize then archive;
- hash deduplication;
- load on demand.

#### 18.7. “Lượng tử hóa” ngôn ngữ nhưng không có thuật toán

Giải pháp:

- mọi khái niệm phải có:
  - data structure;
  - algorithm;
  - invariant;
  - benchmark;
  - failure case.

---

### 19. NGUYÊN TẮC BẤT BIẾN

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

### 20. WORKFLOW CHUẨN CHO MỖI TASK CODE

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

### 21. WORKFLOW CHUẨN CHO MỖI TASK NGHIÊN CỨU

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

### 22. FILE ĐỌC ĐẦU TIÊN CHO CODEX

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

### 23. FILE ĐỌC ĐẦU TIÊN CHO LOCAL CODER

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

### 24. DEFINITION OF DONE

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

### 25. ƯU TIÊN TRIỂN KHAI NGAY

#### Priority 0

- Tạo repository skeleton.
- Tạo memory tree.
- Tạo invariants.
- Tạo Codex policy.
- Tạo TaskContract schema.
- Tạo ThoughtState schema.
- Tạo EvidencePacket schema.

#### Priority 1

- Xây codegraph indexer tối thiểu.
- Xây graph summary.
- Xây incremental refresh.
- Xây context capsule generator.

#### Priority 2

- Xây deterministic ThoughtState runtime.
- Branch/merge/prune.
- Evidence update.
- Experiment contract.

#### Priority 3

- Tích hợp local software department.
- Codex orchestration workflow.
- Local coder/tester/reviewer prompts.
- End-to-end code task thử nghiệm.

#### Priority 4

- Adaptive N.
- Information gain.
- Executor diversity.
- Verification Tribunal.

#### Priority 5

- Dataset và distillation.
- Student model.
- Benchmark với baseline.

---

### 26. KẾT LUẬN KIẾN TRÚC V1

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

### PHỤ LỤC A — PROJECT CHARTER RÚT GỌN

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

### PHỤ LỤC B — CHECKLIST KIỂM TRA DRIFT

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

### PHỤ LỤC C — TRẠNG THÁI TÀI LIỆU

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

---

## Phần 2 — Giới thiệu ViVy: AI That You Own

> **Nguồn:** `old-docs/11-consolidated-source-2026-09-26/INTRODUCTION.md` — `[ISOLATED 26/09/2026]`

### Introducing ViVy — AI That You Own

#### The Problem: You Don't Own Your AI

Every time you use ChatGPT, Claude, or Gemini, you are renting intelligence.

- **Your prompts** go to their servers.
- **Your context** is processed on their hardware.
- **Your usage** trains their next model.
- **Their pricing** can change tomorrow.
- **Their API** can go down during your critical task.
- **Their model updates** can break workflows you built around their behavior.

This is the reality of cloud AI in 2025. And most "local AI" tools are just wrappers that forward your requests to the same cloud, or run a model file without giving you any actual architectural advantage.

**ViVy is different.**

---

#### ViVy Gives You What Jev Has

##### What is Jev?

Jev is the name for a class of AI model architecture — inspired by Jamba's mixture-of-experts routing — where the model **evaluates multiple hypotheses in parallel** rather than generating sequentially.

The key insight: instead of thinking "what should I do?" one step at a time, Jev-style models score *N candidate actions simultaneously* in a single matrix multiply, then route to the winner.

This makes Jev-class models fundamentally different from standard autoregressive LLMs:

| | Standard LLM | Jev-class model |
|:---|:---|:---|
| **Action selection** | Sequential token generation | Parallel hypothesis scoring |
| **Compute pattern** | Memory-bandwidth bound | Compute-bound (GPU efficient) |
| **Efficiency at scale** | Degrades | Improves |
| **Pre-commitment** | None (generates as it thinks) | Directive emitted before output |

##### ViVy's ElasticNCore = Jev for everyone

ViVy packages the Jev architectural insight into a module anyone can run locally:

```python
# N=2 to 16 parallel hypothesis cores
n_core = ElasticNCore(n_min=2, n_max=4, hidden_dim=64)

# All N candidates scored in ONE pass
result = n_core.forward(n_override=2)
# → winner: the best action, selected before any generation
```

You don't need to train a 70B parameter Jamba model to get this benefit. ViVy gives you Jev's parallel evaluation *on top of* any local model you already have.

---

#### What Makes ViVy Special

##### 1. You Own the Weights

When you install ViVy with Gemma 4 E4B, the model weights are stored on your disk. They are yours:

- No API key required after setup
- Works fully offline, on a plane, on a ship, anywhere
- No token costs, no rate limits, no monthly bills
- The model never "updates" without your consent — you freeze the version you trust

```bash
# This is all you need, forever, after setup
ollama serve
python scripts/run_vivy.py --mode agentic
```

##### 2. ViVy Thinks, Not Just Talks

Most local AI gives you a chat interface. ViVy gives you an **agent that can act**:

```
You:   "Analyze my codebase and find all functions with no error handling"

ViVy:  <vivy_thought>
       [EPISTEMIC_ASSESSMENT]
       Confidence: HIGH
       Epistemic_Decision: EXECUTE_DIRECTLY
       </vivy_thought>
       
       [Calls engine_exec: find . -name "*.py" | xargs grep ...]
       [Calls engine_file_io: read each matching file...]
       [Analyzes patterns in CognitiveStateGraph...]
       
       Found 7 functions missing error handling:
       1. auth.py:login() — no try/except around DB call
       2. api.py:process_request() — ...
```

This is not a chatbot. This is an agent with tools, memory, and a cognitive state that persists across the session.

##### 3. ViVy Never Makes the Same Mistake Twice

**The VM-11 Invariant** is what separates ViVy from every other local AI implementation.

When ViVy takes an action that fails, the **CognitiveStateGraph** records it:

```
Node (action: "read_file /nonexistent.txt"):
  state: HYPOTHESIS
  falsified_count: 1
  dampen_factor: 0.5¹ = 0.50   ← 50% suppressed
  
  If ViVy considers this action again:
  effective_score = raw_score × 0.50
  → It will almost always choose something else
```

If the same action fails twice: `dampen_factor = 0.5² = 0.25`
Three times: `0.125`

The result: error repeats are **dampened** (measured rate: see Gate-10 receipt). ViVy is architecturally resistant to getting stuck in a retry loop on the same broken action. <!-- [ISOLATED 24/09/2026] prior: "0% error repeat rate" — Gate 9: no 0% claim without receipt. -->

##### 4. ViVy Knows What It Doesn't Know

Every ViVy response begins with an **Epistemic Assessment**:

```xml
<vivy_thought>
[EPISTEMIC_ASSESSMENT]
Objective:        What am I trying to accomplish?
Confidence:       HIGH | MEDIUM | LOW
Unknown_Entities: What do I not know yet?
Required_Modalities: Do I need vision/audio/data?
Epistemic_Decision: EXECUTE_DIRECTLY | NEED_KNOWLEDGE_FORAGING | DELEGATE_MODEL

[EXECUTION_DIRECTIVE]
Target:           What/who to act on
Action:           Specific action
Expected_Evidence: How I'll verify success
</vivy_thought>
```

This is not just a prompt trick. It's the output of the DirectiveMTPHead — emitted before the main generation pass. ViVy commits to its epistemic state before generating output, making its reasoning transparent and verifiable.

##### 5. Multimodal — Text + Vision + Audio

With Gemma 4 E4B as the base model, ViVy processes:

- **Text**: code, documents, structured data
- **Images**: diagrams, screenshots, charts, photos
- **Audio**: speech, audio events (when using audio-capable adapters)

All locally. All without sending anything to a cloud.

---

#### Architecture Summary

```
Your input (any modality)
         ↓
MultimodalAdapter ── Encodes text/image/audio to unified tensors
         ↓
ElasticNCore ──────── N parallel candidates, 1 GEMM pass (Jev-style)
         ↓
DirectiveMTPHead ──── Opcode committed before generation
         ↓
Gemma 4 E4B ────────── Base model: text generation + tool calling
         ↓
ToolDispatcher ─────── Maps tool_call to engine primitive
         ↓
GraphBridge ────────── Evaluates result, updates CognitiveStateGraph
         ↓
CognitiveStateGraph ── Thought Ecology: every action leaves a trace
HebbianRecall ────────  W = Y·X⁺, fast associative memory
         ↓
Output + learned state
```

**The complete loop takes ~30–60 seconds on CPU (first token ~5–10s warm).
With GPU: ~5–8 seconds total.**

---

#### Swap Your Model Anytime

ViVy is built on the principle that **the architecture outlasts any specific model weights**.

When a better model comes out, you swap one line:

```
# Modelfile.vivy — change only this line
FROM gemma4:e4b              # Current: Apache 2.0, 9.6GB, CPU-capable
# FROM nemotron-nano-omni    # Upgrade: NVIDIA, Video modality
# FROM qwen3.8-omni-flash    # Future: Full omni, strong tool calling
```

```bash
ollama create vivy-final:v1 -f Modelfile.vivy
```

Everything else — your tools, your memory graph, your sessions, your workflows — stays exactly the same.

---

#### Who Is ViVy For?

##### Developers who want an AI coding partner
ViVy can read your codebase, run tests, analyze errors, and suggest fixes — entirely locally.

##### Researchers who need privacy
Your research data, proprietary datasets, and unpublished results never leave your machine.

##### Power users who want control
Set the exact model version. Freeze it. Never worry about the vendor changing behavior overnight.

##### Anyone tired of token bills
After hardware setup, every ViVy inference is free.

---

#### The Promise

> **ViVy gives you a model that thinks like Jev, runs on your hardware, and answers to no one but you.**

This is what AI ownership means in practice:
- No subscriptions
- No data harvesting
- No vendor lock-in
- No surprise model updates
- No API downtime
- No rate limits
- 100% your data, 100% your compute, 100% your AI

---

*ViVy Final Core V1.0 · Built by [Ngọc Châu](https://github.com/ngocchau-ai) · Made in Vietnam 🇻🇳*

---

## Phần 3 — Nỗi đau, giải pháp & kiến trúc

> **Nguồn:** `old-docs/11-consolidated-source-2026-09-26/PAIN_POINTS_AND_SOLUTIONS.md` — `[ISOLATED 26/09/2026]`

### Tài liệu Phân tích Nỗi đau, Giải pháp & Kiến trúc ViVy AI Framework

#### 1. Nỗi đau Sản phẩm (Pain Points)

1. **Thiếu Local AI Engine thực sự:**
   - Trước đây, sản phẩm chỉ sử dụng wrapper prompt đơn giản dựa vào Ollama (`FROM llama3.2:3b`) hoặc mô phỏng lý thuyết trong `nps_core`.
   - Không có khả năng trực tiếp nạp và suy luận weights local (`.gguf`, `.safetensors`, `.bin`), thiếu pipeline fine-tuning LoRA riêng cho miền dữ liệu tài chính/trading.

2. **Xung đột Kiến trúc Mắt - Tay (Programmatic Gatekeeping):**
   - Sự hiện diện của các bộ lọc cản logic cứng (hardcoded R:R ratio check, netting filter, velocity guard) bằng mã Python đã can thiệp vào quyết định độc lập của AI.
   - Vi phạm nguyên tắc cốt lõi: ViVy phải là **Não trung tâm** duy nhất ra quyết định và tự quản trị rủi ro thông qua weights & static lessons.

3. **Thiếu Hệ thống Quản trị & Login 1-Chạm Bảo mật:**
   - Chưa có giải pháp phân quyền User, mã hóa mật khẩu Argon2id, JWT Token và WebAuthn (Passkey) login 1-chạm bằng sinh trắc học/hardware key cho dashboard điều khiển.

---

#### 2. Giải pháp Sản phẩm (ViVy Solution Stack)

1. **Local Model Core (`src/vivy/core`):**
   - Hỗ trợ nạp model weights trực tiếp từ file `.gguf` (qua `llama-cpp-python`), PyTorch/Safetensors (`transformers`), hoặc kết nối linh hoạt tới Ollama / vLLM local API.
   - Engine suy luận sinh JSON cấu trúc (`Structured Reasoning JSON Output`) đảm bảo câu trả lời nhất quán, giải thích được (explainable reasoning).

2. **Kiến trúc Mắt - Tay Chuẩn (`src/vivy/eyes` & `src/vivy/hands`):**
   - **Mắt (Eyes):** Thu thập dữ liệu nến OHLC, RSI, EMA, ATR, rổ lệnh MT5, và tin tức kinh tế vĩ mô.
   - **Tay (Hands):** Chuyển tiếp và gửi lệnh thô (`BUY`, `SELL`, `MODIFY`, `CLOSE`, `CANCEL`) trực tiếp tới MT5 Terminal. CẤM tuyệt đối bộ lọc cản hay gác cổng lập trình cứng trong Python.

3. **Bộ nhớ & Tự Hoàn Thiện (`src/vivy/memory` & `src/vivy/self_improvement`):**
   - **Associative Vector Memory:** SQLite/FAISS vector store lưu giữ các mẫu giao dịch và bài học kinh nghiệm past trades.
   - **Feedback Loop:** Tự động ghi nhận PnL, lý do thắng/thua để làm bài học tĩnh (static lessons) nạp lại vào prompt cho ViVy tự học.

4. **Quản trị User & Login 1-Chạm (`src/vivy/auth`):**
   - Hỗ trợ mã hóa mật khẩu Argon2id + JWT Access/Refresh Tokens + WebAuthn/Passkey sinh trắc học 1-chạm.

---

#### 3. Luồng Xử Lý Dữ Liệu (Data Flow Architecture)

```
[ MT5 Terminal / News Feeds ]
           │
           ▼
    [ Eyes Module ]  (mt5_collector & news_bridge)
           │
           │ (Nạp giá, chỉ báo, tin tức & rổ lệnh)
           ▼
  [ Vector Memory ]  (Lấy bài học quá khứ thành công/thất bại)
           │
           │ (Ghép Context & Static Lessons)
           ▼
[ Central Brain ViVy ] (core/model_loader & inference)
           │
           │ (Sinh Structured JSON Decision: Thought + Action)
           ▼
   [ Hands Module ]  (mt5_executor - Không có gác cổng logic)
           │
           │ (Gửi Lệnh Thô)
           ▼
    [ MT5 Terminal ]
           │
           ▼
[ Self-Improvement ] (Ghi log PnL & Cập nhật bài học quá khứ vào Memory)
```

---

#### 4. Giải Pháp Quản Trị User & Login 1-Chạm

- **Hệ thống Authentication:**
  - Standard Login: Username + Password (Argon2id hashing algorithm).
  - 1-Touch Passkey Login: WebAuthn FIDO2 / Passkey API (TouchID / FaceID / YubiKey).
  - Token Management: Bearer JWT Token với thời hạn hết hạn 60 phút và refresh token 7 ngày.

---

## Phần 4 — Context Strategy

> **Nguồn:** `old-docs/11-consolidated-source-2026-09-26/CONTEXT_STRATEGY.md` — `[ISOLATED 26/09/2026]`

### Context Strategy

Mặc định chỉ nạp:

1. Identity capsule.
2. TaskContract.
3. Architecture refs liên quan.
4. Codegraph neighborhood.
5. Target symbol và tests.

Mở rộng theo progressive disclosure:

```text
summary → symbol → file section → full file → adjacent module
```

Không nạp raw files hoặc toàn bộ lịch sử chat nếu không có yêu cầu truy nguyên.

---

## Phần 5 — System Knowledge Map (bản đồ tri thức 91sViVy)

> **Nguồn:** `old-docs/11-consolidated-source-2026-09-26/SYSTEM_KNOWLEDGE_MAP.md` — `[ISOLATED 26/09/2026]`

### Bản Đồ Tri Thức Toàn Hệ Thống 91sViVy (System Knowledge Map)

---

#### 🗺️ 1. Tổng Quan Kiến Trúc (Architectural Blueprint)

Sản phẩm **91sViVy** được thiết kế dựa trên triết lý **Mắt - Tay Architecture** với **Não trung tâm là Local AI Engine (ViVy)**.

```
                  ┌────────────────────────────────────────┐
                  │          SYSTEM KNOWLEDGE MAP          │
                  └──────────────────┬─────────────────────┘
                                     │
         ┌───────────────────────────┼───────────────────────────┐
         ▼                           ▼                           ▼
 ┌───────────────┐           ┌───────────────┐           ┌───────────────┐
 │  MẮT (EYES)   │           │ CENTRAL BRAIN │           │ TAY (HANDS)   │
 │ Market/News   │──────────►│ ViVy Local AI │──────────►│ MT5 Executor  │
 │  Perception   │           │    Engine     │           │ No Gatekeeper │
 └───────────────┘           └───────┬───────┘           └───────────────┘
                                     │
         ┌───────────────────────────┼───────────────────────────┐
         ▼                           ▼                           ▼
 ┌───────────────┐           ┌───────────────┐           ┌───────────────┐
 │ MEMORY STORE  │           │ AUTH & PASSKEY│           │ SELF-LEARNING │
 │ Vector/SQLite │           │ Argon2id/JWT  │           │ Feedback PnL  │
 └───────────────┘           └───────────────┘           └───────────────┘
```

---

#### 🧩 2. Danh Mục Các Module & Thành Phần Hệ Thống

| Module | Đường dẫn File | Mô tả Chức năng | Nguyên tắc/Quy tắc |
| :--- | :--- | :--- | :--- |
| **Isolated Prompts** | [prompts.py](file:///d:/91sViVy-Aider/src/vivy/core/prompts.py) | Quản lý toàn bộ System Prompt cho 91sViVy (`VIVY_TRADING_SYSTEM_PROMPT`, `VIVY_REASONING_SYSTEM_PROMPT`). | Cô lập 100% khỏi các dự án bên ngoài. |
| **Model Loader** | [model_loader.py](file:///d:/91sViVy-Aider/src/vivy/core/model_loader.py) | Engine nạp model weights local (`.gguf` via `llama-cpp-python`, PyTorch/Safetensors via `transformers`, Ollama API, hoặc Mock). | Open Source First. |
| **Inference Engine** | [inference.py](file:///d:/91sViVy-Aider/src/vivy/core/inference.py) | Engine suy luận sinh ra Transparent Reasoning & Structured JSON decision. | Sinh JSON chuẩn định dạng `thought`, `action`, `symbol`, `volume`, `stop_loss`, `take_profit`. |
| **Mắt (Data Collector)** | [mt5_collector.py](file:///d:/91sViVy-Aider/src/vivy/eyes/mt5_collector.py) | Thu thập giá nến OHLC, rổ lệnh hiện tại, chỉ báo RSI, EMA 20/50, ATR 14. | Không chứa logic quyết định. |
| **Mắt (News Bridge)** | [news_bridge.py](file:///d:/91sViVy-Aider/src/vivy/eyes/news_bridge.py) | Cầu nối thu thập dữ liệu vĩ mô và tin tức kinh tế. | Cung cấp thông tin vĩ mô cho AI. |
| **Tay (MT5 Executor)** | [mt5_executor.py](file:///d:/91sViVy-Aider/src/vivy/hands/mt5_executor.py) | Chuyển tiếp và gửi lệnh thô (`BUY`, `SELL`, `MODIFY`, `CLOSE`) trực tiếp tới MT5 Terminal. | **CẤM tuyệt đối bộ lọc cản hay gác cổng lập trình cứng (No Programmatic Gatekeepers)**. |
| **Vector Memory** | [vector_store.py](file:///d:/91sViVy-Aider/src/vivy/memory/vector_store.py) | Bộ nhớ lưu vết trade lessons và thu hồi 1-touch intuition context. | SQLite/Vector local storage. |
| **Auth & Passkey** | [user_manager.py](file:///d:/91sViVy-Aider/src/vivy/auth/user_manager.py)<br>[webauthn_passkey.py](file:///d:/91sViVy-Aider/src/vivy/auth/webauthn_passkey.py) | Mã hóa Argon2id/SHA256, JWT Token generation/verification, Session invalidation, và WebAuthn 1-touch passkey login. | Vô hiệu hóa session tức thì khi có lệnh revocation. |
| **API Server** | [router.py](file:///d:/91sViVy-Aider/src/vivy/api/router.py) | Điều phối REST API, WebSockets và chạy chu kỳ trade cycle tự động. | FastAPI lightweight open source. |
| **Continuous Learning** | [feedback_logger.py](file:///d:/91sViVy-Aider/src/vivy/self_improvement/feedback_logger.py) | Ghi nhận kết quả PnL, trích xuất bài học và nạp lại vào memory cho ViVy tự học. | Self-improvement loop. |
| **Fine-Tuning Scripts** | [train_lora.py](file:///d:/91sViVy-Aider/scripts/train_lora.py)<br>[export_gguf.py](file:///d:/91sViVy-Aider/scripts/export_gguf.py) | Pipeline fine-tune LoRA/PEFT và script nén/quantize weights GGUF. | Hỗ trợ huấn luyện local. |

---

#### 🔒 3. Bảo Mật & Quản Trị Session Tức Thì

Hệ thống quản trị phiên làm việc (Session Management) hỗ trợ **Vô hiệu hóa toàn bộ session trước đây** (Global Session Revocation):
- Phương thức `revoke_all_sessions()` lưu mốc thời gian `_min_valid_timestamp`.
- Mọi JWT token được phát hành trước mốc thời gian này sẽ lập tức bị từ chối (`verify_jwt_token` trả về `None`).
- Cho phép quản trị viên hủy toàn bộ quyền truy cập tức thì khi cần bảo mật cao.

---

#### ⚡ 4. Quy Trình Vận Hành Thực Tế (Execution Workflow)

```
1. Client Authenticate (Login 1-touch Passkey / JWT)
   │
2. Trigger Autonomous Trade Cycle (`handle_trade_cycle`)
   │
   ├─► [Eyes] MT5DataCollector & NewsBridge thu thập dữ liệu real-time.
   │
   ├─► [Memory] ViVyVectorMemory truy vấn bài học quá khứ (Recall Intuition).
   │
   ├─► [Brain] ViVyInferenceEngine xử lý context, ra quyết định JSON.
   │
   ├─► [Hands] MT5Executor gửi lệnh trực tiếp lên MT5 (Không có gác cổng cứng).
   │
   └─► [Self-Improvement] FeedbackLogger lưu kết quả PnL vào Memory.
```

---

#### 🧪 5. Kiểm Thử Hệ Thống (Testing & Evidence)

Tất cả các thành phần được kiểm thử tự động với suite `pytest`:
- **Chạy duy nhất lệnh:** `python -m pytest --basetemp=.pytest_basetemp`
- **Kết quả:** 671 tests passed 100%.

---

## Phần 6 — Chuỗi test & thực nghiệm (TEST_CHAIN_PLAN)

> **Nguồn:** `old-docs/11-consolidated-source-2026-09-26/TEST_CHAIN_PLAN.md` — `[ISOLATED 26/09/2026]`

### Chuỗi Test & Thực nghiệm — Unitary Reasoner

Sau phase 0 (củng cố nền tảng), mở rộng test suite và thực nghiệm
toán/vật lý kinh điển.

---

#### 1. Thuật toán tương ứng, dị hình, phi đối xứng

##### 1.1 Graph Non-Isomorphism (Dị hình đồ thị)

**Bài toán:** Cho 2 đồ thị G₁, G₂ — có tồn tại song ánh bảo toàn cạnh?

**Cách tiếp cận với unitary-reasoner:**
- Mã hóa ma trận kề → quantum state
- Dùng SVD streams để trích đặc trưng phổ đồ thị
- So sánh phổ eigenvalues (bất biến Weisfeiler-Lehman)
- Phát hiện dị hình khi phổ khác nhau

**Test cases:**
- G₁ = K₃ (tam giác), G₂ = C₃ (chu trình 3 đỉnh) → isomorphic
- G₁ = K₃, G₂ = path₃ (đường 3 đỉnh) → non-isomorphic
- G₁ = 4-cycle + chord, G₂ = 4-cycle → non-isomorphic
- G₁ = Petersen graph, G₂ = same → isomorphic

##### 1.2 Symmetry Detection & Breaking (Phát hiện/Breaking đối xứng)

**Bài toán:** Phát hiện nhóm đối xứng của cấu trúc logic/toán học.

**Cách tiếp cận:**
- Mã hóa công thức boolean dưới dạng tensor
- Dùng unitary gates để kiểm tra tính bất biến dưới phép hoán vị
- SVD streams phát hiện cấu trúc lặp

**Test cases:**
- `(x ∧ y) ∨ (¬x ∧ ¬y)` — đối xứng qua swap(x,y)
- `(x ∧ y) ∨ (x ∧ z)` — không đối xứng
- Latin square 3×3 — đối xứng nhóm S₃

##### 1.3 Non-Abelian Hidden Subgroup (Nhóm con ẩn phi Abelian)

**Bài toán:** Tổng quát hóa Shor's algorithm, liên quan graph isomorphism.

**Test cases:**
- Nhóm S₃ — tìm nhóm con ẩn
- Nhóm D₄ (dihedral) — tìm nhóm con cyclic
- So sánh với trường hợp Abelian (Zₙ)

##### 1.4 Asymmetric Cryptography Primitives

**Bài toán:** Mã hóa bất đối xứng — tính một chiều.

**Test cases:**
- RSA: mã hóa (public key) vs giải mã (private key) — asymmetry
- Diffie-Hellman: tính g^a mod p (dễ) vs tìm a (khó)
- Elliptic curve: point addition (dễ) vs discrete log (khó)

##### 1.5 Constraint Satisfaction with Symmetry Breaking

**Bài toán:** Sudoku, N-Queens, graph coloring.

**Test cases:**
- Sudoku 4×4 — detect symmetry (hoán vị hàng/cột)
- N-Queens — symmetry under dihedral group D₄
- Graph 3-coloring — color permutation symmetry

---

#### 2. Bài toán / phương trình chưa có lời giải

Không yêu cầu hệ thống *giải* được — mà kiểm tra khả năng suy luận
về *cấu trúc* của bài toán.

##### 2.1 Collatz Conjecture (Giả thuyết Collatz)

**Bài toán:** f(n) = n/2 nếu chẵn, 3n+1 nếu lẻ. Mọi n → 1?

**Dạng test:**
- Mã hóa quy tắc Collatz dưới dạng unitary gate
- Mô phỏng quỹ đạo cho n nhỏ (n=1..27)
- Phát hiện chu kỳ (1→4→2→1)
- Suy luận về tính dừng

##### 2.2 Goldbach's Conjecture (Giả thuyết Goldbach)

**Bài toán:** Mọi số chẵn > 2 là tổng 2 số nguyên tố.

**Dạng test:**
- Kiểm tra cho n chẵn ≤ 100
- Phân bố cặp Goldbach
- Suy luận về cấu trúc số nguyên tố

##### 2.3 Twin Prime Conjecture

**Bài toán:** Vô hạn cặp số nguyên tố sinh đôi (p, p+2).

**Dạng test:**
- Thống kê phân bố twin primes trong [1, 1000]
- So sánh với mật độ số nguyên tố

##### 2.4 Odd Perfect Numbers

**Bài toán:** Tồn tại số hoàn hảo lẻ?

**Dạng test:**
- Định nghĩa số hoàn hảo: σ(n) = 2n
- Kiểm tra n lẻ ≤ 10⁶
- Ràng buộc: n > 10¹⁵⁰⁰ nếu tồn tại

##### 2.5 Riemann Hypothesis (cấp độ suy luận)

**Bài toán:** Mọi zero không tầm thường của ζ(s) có Re(s) = 1/2.

**Dạng test:**
- Mã hóa ζ(s) dưới dạng chuỗi Dirichlet
- Tính zero trên critical strip
- So sánh phân bố zero với mô hình GUE (random matrix)

##### 2.6 P vs NP (cấp độ suy luận)

**Bài toán:** Có thuật toán thời gian đa thức cho NP-đầy đủ?

**Dạng test:**
- Mã hóa SAT dưới dạng unitary evolution
- So sánh độ phức tạp giữa 2-SAT (P) và 3-SAT (NP-complete)
- Phát hiện phase transition trong random SAT

---

#### 3. Thực nghiệm toán học

##### 3.1 Số nguyên tố & Phân tích thừa số

| Bài toán | Mô tả | Phương pháp |
|----------|-------|-------------|
| Kiểm tra nguyên tố | n ∈ [2, 1000] | Miller-Rabin dạng unitary |
| Phân tích thừa số | n = pq (p,q nguyên tố) | Shor-style period finding |
| Định lý số nguyên tố | π(x) ~ x/ln(x) | Thống kê + fitting |
| Định lý Fermat nhỏ | a^p ≡ a (mod p) | Kiểm tra unitary |

##### 3.2 Dãy số & Cấu trúc

| Bài toán | Mô tả | Phương pháp |
|----------|-------|-------------|
| Fibonacci | Fₙ dạng đóng | MPS compression |
| Catalan | Cₙ = (2n)!/(n+1)!n! | SVD stream extraction |
| Partition | p(n) — số cách phân hoạch | Associative memory |
| Mersenne | Mₙ = 2ⁿ − 1 | Kiểm tra nguyên tố |

##### 3.3 Hình học & Đại số

| Bài toán | Mô tả | Phương pháp |
|----------|-------|-------------|
| Pythagorean triples | a² + b² = c² | Unitary search |
| Elliptic curves | y² = x³ + ax + b | Point addition |
| Finite fields | GF(p^k) arithmetic | Gate composition |
| Polynomial factoring | over GF(p) | Berlekamp unitary |

---

#### 4. Thực nghiệm vật lý kinh điển

##### 4.1 Cơ học lượng tử (phù hợp nhất với unitary core)

| Bài toán | Mô tả | Phương pháp |
|----------|-------|-------------|
| Harmonic oscillator | H = p²/2m + mω²x²/2 | Time evolution unitary |
| Particle in a box | Infinite square well | Energy eigenstates |
| Double-slit interference | Superposition + measurement | QuantumState + collapse |
| Spin-1/2 system | Pauli matrices | Gate composition |
| Quantum tunneling | Barrier penetration | Evolution with potential |
| Bell inequality | CHSH game | Entanglement + measurement |

##### 4.2 Cơ học cổ điển

| Bài toán | Mô tả | Phương pháp |
|----------|-------|-------------|
| Simple pendulum | θ'' + (g/L)sin(θ) = 0 | Small-angle approximation |
| Double pendulum | Chaotic dynamics | Numerical integration |
| Kepler's laws | Orbital mechanics | Gravitational simulation |
| Spring-mass system | Hooke's law + damping | Harmonic oscillator |
| Projectile motion | Parabolic trajectory | Kinematic equations |

##### 4.3 Nhiệt động lực học & Thống kê

| Bài toán | Mô tả | Phương pháp |
|----------|-------|-------------|
| Ising model 1D | Spin chain | MPS representation |
| Blackbody radiation | Planck's law | Spectral distribution |
| Maxwell-Boltzmann | Velocity distribution | Statistical sampling |
| Heat equation | ∂T/∂t = α∇²T | PDE discretization |
| Random walk | Diffusion process | Quantum walk analogue |

##### 4.4 Điện từ & Sóng

| Bài toán | Mô tả | Phương pháp |
|----------|-------|-------------|
| Wave equation | ∂²u/∂t² = c²∇²u | Unitary evolution |
| Maxwell's equations | ∇·E = ρ/ε₀, ∇×B = μ₀J + ... | Tensor representation |
| LC circuit | q'' + ω²q = 0 | Harmonic oscillator analogue |
| Interference pattern | Double-slit | Superposition principle |

---

#### 5. Kế hoạch triển khai

##### Phase 1 — Chuỗi test cốt lõi (ưu tiên cao nhất)

1. **Graph Non-Isomorphism** — test suite với 10 cặp đồ thị
2. **Symmetry Detection** — 5 bài toán boolean
3. **Collatz Conjecture** — quỹ đạo + chu kỳ
4. **Goldbach** — kiểm tra n ≤ 1000
5. **Harmonic Oscillator** — time evolution unitary

##### Phase 2 — Mở rộng

6. **Constraint Satisfaction** — Sudoku 4×4, N-Queens
7. **Ising Model 1D** — MPS representation
8. **Riemann zeros** — thống kê phân bố
9. **SAT phase transition** — 2-SAT vs 3-SAT
10. **Bell inequality** — CHSH game

##### Phase 3 — Thực nghiệm sâu

11. **Navier-Stokes** — 1D Burgers equation
12. **Yang-Mills** — lattice gauge theory toy model
13. **Quantum walk** — trên đồ thị
14. **P vs NP** — structural reasoning
15. **Odd perfect numbers** — search bounds

---

#### 6. Tiêu chí đánh giá

| Mức | Ý nghĩa |
|-----|---------|
| ✅ PASS | Kết quả đúng, confidence ≥ 0.7 |
| ⚠️ LOW | Kết quả đúng, confidence < 0.7 |
| ❌ FAIL | Kết quả sai |
| 🔄 PROBE | Hệ thống không thể kết luận (control = "measure") |

Mục tiêu: ≥ 80% PASS + LOW trên phase 1 trước khi chuyển phase 2.

---

## Phần 7 — Phân tích kiến trúc Mixture-of-Experts

> **Nguồn:** `old-docs/11-consolidated-source-2026-09-26/VIVY_MOE_ARCHITECTURE_ANALYSIS.md` — `[ISOLATED 26/09/2026]`

### 🏛️ PHÂN TÍCH CHUYÊN SÂU: KIẾN TRÚC MIXTURE-OF-EXPERTS (MoE 40B TOTAL / 7B ACTIVE) CHO VIVY

**Tác giả:** Ngọc Châu Digital Product Development  
**Đối tượng:** Mô hình AI ViVy — NPS Core Architecture  

---

#### 1. ĐÁNH GIÁ TÍNH PHÙ HỢP (SUITABILITY VERDICT)

👉 **KẾT LUẬN: RẤT PHÙ HỢP VÀ LÀ HƯỚNG ĐI LÝ TƯỞNG CỰC KỲ MẠNH MẼ CHO VIVY.**

Giải pháp "Model 40B, chỉ kích hoạt 7B khi chạy" chính là **Kiến trúc MoE (Mixture-of-Experts - Hỗn hợp các Chuyên gia)**. Mô hình này giúp ViVy đạt được **sức mạnh trí tuệ của model 40B** nhưng giữ được **tốc độ phản hồi cực nhanh và chi phí tính toán FLOPs của model 7B**.

---

#### 2. NGUYÊN LÝ HOẠT ĐỘNG CỦA VIVY MoE 40B/7B

```
                         ┌──────────────────────────────────┐
                         │   Input Token / Visual Payload   │
                         └──────────────────────────────────┘
                                          │
                                          ▼
                         ┌──────────────────────────────────┐
                         │    MoE Top-K Router Network      │
                         │    (Gated Expert Selection)      │
                         └──────────────────────────────────┘
                                   │              │
                   Select Top-2    │              │ (Only 2 of 8 experts activated)
                   Experts (~7B)   ▼              ▼
                         ┌──────────────────┐   ┌──────────────────┐
                         │ Expert 1: Vision │   │ Expert 3: CoT    │
                         │ & Multimodal     │   │ Reasoning & Logic│
                         └──────────────────┘   └──────────────────┘
                                   │              │
                                   └───────┬──────┘
                                           ▼
                         ┌──────────────────────────────────┐
                         │  Combined Expert Output (~7B)    │
                         └──────────────────────────────────┘
```

##### 2.1. Phân bổ các Chuyên gia (Experts Assignment for ViVy):
Hệ thống 40B tham số được chia thành 8 Chuyên gia độc lập (Mỗi chuyên gia ~5B-7B params), Bộ định tuyến Router chọn Top-2 Chuyên gia active cho mỗi token:

1. **Expert 1 — Multimodal Vision:** Chuyên gia xử lý hình ảnh, biểu đồ, đặc trưng thị giác.
2. **Expert 2 — Bilingual NLP (EN/VI):** Chuyên gia ngôn ngữ ngữ pháp tiếng Việt và tiếng Anh.
3. **Expert 3 — Chain-of-Thought Logic:** Chuyên gia tư duy logic và kiểm chứng giả thuyết (Stage 1..5).
4. **Expert 4 — Code & AST Analysis:** Chuyên gia đọc hiểu mã nguồn, codegraph và refactoring.
5. **Expert 5 — Quantitative & Time-Series:** Chuyên gia phân tích số liệu và chuỗi thời gian.
6. **Expert 6 — Distillation & Memory Curation:** Chuyên gia quản lý bài học kinh nghiệm và memory.
7. **Expert 7 — Verification Tribunal:** Chuyên gia kiểm toán mâu thuẫn bằng chứng.
8. **Expert 8 — General Synthesis:** Chuyên gia tổng hợp tri thức chung.

---

#### 3. BẢNG SO SÁNH: MOE 40B/7B VS DENSE MODEL 40B VS DENSE MODEL 7B

| Tiêu Chí | Model Dense 7B | Model Dense 40B | **ViVy MoE 40B (7B Active)** |
|---|---|---|---|
| **Dung lượng Tri thức (Knowledge)** | Khá (Trung bình) | Rất rộng (Rất thông minh) | **Rất rộng (Tương đương 40B)** |
| **Số tham số Active/Token** | 7 Billion | 40 Billion | **~7 Billion (Giảm 82.5% FLOPs)** |
| **Độ trễ Phản hồi (Latency)** | Cực nhanh (< 100ms) | Chậm (500ms - 2000ms) | **Cực nhanh (< 150ms - Đạt SLA ViVy)** |
| **Dung lượng VRAM Nạp** | ~6 GB (Q4) | ~26 GB (Q4) | **~24 GB (Q4_K_M)** |
| **Khả năng chuyên môn hóa** | Đơn luồng chung | Đơn luồng chung | **Đa chuyên gia chuyên biệt (Top-2 Router)** |

---

#### 4. ĐỀ XUẤT KIẾN TRÚC MÃ NGUỒN TRONG NPS CORE

Chúng ta triển khai bộ cấu hình `MoEConfig` và `MoERouter` trong `src/nps_core/model_training/moe.py`:
- `num_total_experts = 8`
- `num_active_experts = 2`
- `total_parameters = 40,000,000,000` (40B)
- `active_parameters = 7,000,000,000` (7B)
- **FLOPs Efficiency Gain:** **Giảm 82.5% chi phí tính toán per token!**

---

## Phần 8 — Phương án đào tạo ViVy 40B Sparse MoE

> **Nguồn:** `old-docs/11-consolidated-source-2026-09-26/VIVY_MOE_40B_TRAINING_PLAN.md` — `[ISOLATED 26/09/2026]`

### 🏛️ PHƯƠNG ÁN ĐÀO TẠO MÔ HÌNH VIVY 40B SPARSE MOE (TUÂN THỦ KIẾN TRÚC TƯ DUY NPS CORE)

**Thương hiệu & Tác giả:** Ngọc Châu Digital Product Development  
**Mô hình Target:** ViVy 40B Sparse MoE (40 tỷ tham số tổng / 7 tỷ tham số active per token)  
**Kiến trúc Nền tảng:** NPS Core V1 Specification ([ARCHITECTURE.md](file:///d:/91sViVy-Aider/ARCHITECTURE.md))  

---

#### 1. NGUYÊN TẮC CỐT LÕI & TUÂN THỦ TƯ DUY GỐC

Phương án đào tạo cho ViVy 40B tuân thủ tuyệt đối quy trình 8 Stage tư duy và logic gốc quy định trong `ARCHITECTURE.md`:
1. **Dữ liệu huấn luyện xuất phát từ Vòng đời Giả thuyết & Tập dữ liệu chắt lọc (Stage 6):**
   - Bộ dữ liệu `ReplayManifest` và `DatasetBuilder` trích xuất các chuyển dịch trạng thái `ThoughtState`, giả thuyết bị loại bỏ, lý do điều hướng và nguồn gốc provenance.
   - Phân chia tập dữ liệu contamination-safe train/val/test bằng thuật toán hash SHA-256 (`DatasetSplitter`).
2. **Lọc chất lượng qua phễu Funnel (Stage 7):**
   - Loại bỏ dữ liệu nhiễu, điểm tin cậy thấp (`confidence < 0.3`) hoặc thiếu bằng chứng xác minh.
3. **Phân bổ Chuyên gia định hướng MoERouter:**
   - Điều hướng các ví dụ huấn luyện cho 8 Chuyên gia MoE độc lập dựa trên loại tác vụ (Thị giác, Ngôn ngữ Anh/Việt, Logic tư duy, Mã nguồn AST, Số liệu).

---

#### 2. THÔNG SỐ KIẾN TRÚC MÔ HÌNH VIVY 40B MOE (`MODEL_MOE_40B`)

```
┌────────────────────────────────────────────────────────────────────────┐
│                      VIVY 40B MOE ARCHITECTURE                         │
│  - Total Parameters: 40,000,000,000 (40 Billion)                       │
│  - Active Parameters: 7,000,000,000 (7 Billion per token)              │
│  - Geometry: 32 layers, hidden_size=4096, 32 heads, 8 kv_heads         │
│  - Experts: 8 Total Experts, Top-2 Gated Active Experts                │
│  - Compute FLOPs Reduction: 82.5% vs Dense 40B                         │
└────────────────────────────────────────────────────────────────────────┘
```

| Thông Số Kiến Trúc | Giá Trị Cấu Hình | Diễn Giải |
|---|---|---|
| `vocab_size` | 32,000 | Bộ từ vựng song ngữ chuẩn Anh/Việt |
| `num_layers` | 32 | Số lớp Transformer |
| `hidden_size` | 4,096 | Kích thước ẩn ẩn |
| `num_attention_heads` | 32 | Số đầu chú ý Multi-Head Attention |
| `num_kv_heads` | 8 | Grouped-Query Attention (GQA 4:1) |
| `intermediate_size` | 11,008 | SwiGLU FFN dimension |
| `num_total_experts` | 8 | Total Experts |
| `num_active_experts` | 2 | Top-2 Gated Active Experts (~7B active) |

---

#### 3. QUY TRÌNH 5 BƯỚC THỰC THI ĐÀO TẠO (TRAINING PIPELINE)

```
 ┌────────────────┐     ┌──────────────────┐     ┌─────────────────┐
 │ Population     │ ──► │ ReplayManifest   │ ──► │ TrainingExample │
 │ Snapshot       │     │ (Stage 6 Split)  │     │ Bridge (Stage 7)│
 └────────────────┘     └──────────────────┘     └─────────────────┘
                                                          │
                                                          ▼
 ┌────────────────┐     ┌──────────────────┐     ┌─────────────────┐
 │ Save Checkpoint│ ◄── │ MoE TrainingStep │ ◄── │ Quality Funnel  │
 │ & SLA Audit    │     │ (Top-2 Experts)  │     │ Curation        │
 └────────────────┘     └──────────────────┘     └─────────────────┘
```

1. **Bước 1: Trích xuất ReplayManifest (Stage 6):** Gom các `PopulationSnapshot` lịch sử, tạo `DatasetRecord`s và phân chia train/val/test.
2. **Bước 2: Bridge & Curation (Stage 7):** Chuyển đổi thành `TrainingExample`s, lọc qua phễu `funnel()` giữ lại ví dụ đạt chuẩn chất lượng.
3. **Bước 3: Phân bổ Router:** `MoERouter.route_task()` định hướng từng ví dụ về đúng Chuyên gia đảm nhận.
4. **Bước 4: Huấn luyện Gradient:** Khởi tạo `TrainingState`, áp dụng Cosine Warmup Learning Rate Schedule (`learning_rate=3e-4`), tính loss và cập nhật metrics.
5. **Bước 5: Xuất Checkpoint & Kiểm định SLA:** Xuất `vivy_moe_40b_checkpoint.json` và kiểm định độ trễ đề xuất `< 200ms`.

---

#### 4. KỊCH BẢN THỰC THI

Kịch bản thực thi được cài đặt tại [scripts/train_vivy_moe_40b.py](file:///d:/91sViVy-Aider/scripts/train_vivy_moe_40b.py):
```powershell
.venv\Scripts\python scripts/train_vivy_moe_40b.py
```

---

## Phần 9 — Thảo luận kiến trúc Orchestration & Coupling

> **Nguồn:** `old-docs/11-consolidated-source-2026-09-26/plans/DISCUSSION_VIVY_ORCHESTRATION_2026-09-25.md` — `[ISOLATED 26/09/2026]`

### Thảo luận Kiến trúc Vivy — Orchestration, Coupling & Cautreo Memory

**Ngày:** 2026-09-25
**Phạm vi:** Xác minh kiến trúc, chiến lược coupling, mindmap DAG, Cautreo weight map
**Trạng thái:** DISCUSSION RECORD — không thực thi

---

#### 1. Xác minh kiến trúc: Model ghép nối

**Kết luận:** Gemma4 là core LLM (brain), Vivy là orchestration layer.

```
┌─────────────────────────────────────┐
│           VIVY (orchestrator)        │
│  decision · skill routing · self-improve│
├──────────┬──────────┬───────────────┤
│ Gemma4   │ Qwen     │ Model khác... │
│ :8080    │ :xxxx    │  qua coupling │
└──────────┴──────────┴───────────────┘
```

- **Gemma4** sinh text, suy luận qua llama-server :8080
- **Vivy** điều phối: system prompt steering, context pipeline, tool dispatch, inference loop
- **Cautreo** native component: memory (put/get/delete), forward parity (L-40 FAIL)

#### 2. Chiến lược: Ghép nối, xâm lấn, chiếm đoạt, sở hữu

Vivy **không học toàn bộ Gemma4**. Vivy học **cách dùng** model core:

| Distillation (sai hướng) | Xâm lấn (đúng hướng) |
|---|---|
| Học output → model copy | Học cách dùng → controller |
| Ceiling = Gemma4 | Ceiling = orchestration experience |
| 1 model, 1 năng lực | 1 orchestrator, nhiều model |
| Copy reasoning | Absorb meta-reasoning |

**Cơ chế "chạy càng nhiều → càng thông minh":**
- Context pattern → strategy nào hiệu quả
- Model core nào mạnh ở task nào (skill routing)
- Khi nào abstain / escalate / tự sửa
- Tích lũy → decision quality tăng → tự cải thiện không cần retrain model core

#### 3. Memory + Weight Management

Vivy cần **bộ nhớ (Cautreo)** + **weight pager**:

| Thành phần | Vai trò |
|---|---|
| **Cautreo memory** | Maps + logs + experience replay |
| **Weight pager** | Partial load, Q4_K/Q6_K streaming, không load toàn bộ |
| **Model coupling** | Swap model core khi HW cho phép |
| **Weight inheritance** | Gọi ngược trọng số cũ sau khi chuyển model |

**Progressive scaling:**
```
Hiện tại:  Vivy ──couple──→ Gemma4 (hardware-fit)
                │
                ▼ (tích lũy + task lớn + HW cho phép)
Tương lai: Vivy ──couple──→ Model lớn hơn
                │
                └──call-back──→ Gemma4 weights (special cases)
```

#### 4. Câu hỏi kỹ thuật đã thảo luận

##### Q1: Gemma4 dùng trọng số/kích hoạt Qwen 2-70B?

**Trực tiếp share weights: KHÔNG khả thi** — khác tokenizer, hidden dim, attention architecture.

**Giải pháp — Vivy làm adapter:**
```
Input → Vivy (routing)
          ├──→ Gemma4 (general, fast)
          └──→ Qwen-70B (specific, via weight pager, partial load)
                    └── ghép output
```

##### Q2: Mindmap DAG tối ưu token coupling lớn?

| Vấn đề | Mindmap DAG giúp? |
|---|---|
| Output bị đứt | ⚠️ Gián tiếp (plan structure trước) |
| Sai sót token lớn | ✅ Scoring nodes → re-route |
| Input/output coupling | ✅ DAG trace được |
| Generator coherence | ❌ Không — vẫn cần model core mạnh |

##### Q3: Tree map vs Session tracing cho Cautreo?

**Dùng cả hai — bổ trợ nhau:**

```
Cautreo Weight Map
├── tree_index (hierarchical, O(log n) lookup)
│   ├── model_weights/
│   │   ├── gemma4/
│   │   └── qwen-70b/ (partial)
│   └── capability_map/
│       └── task → model → layer_range
└── session_log (append-only, scored)
    ├── session-001: decisions + scores + state_delta
    └── session-002: ...
```

- **Tree map** = cấu trúc truy vấn (tốc độ)
- **Session log** = dữ liệu thời gian (audit + self-improve)

---

#### 5. Quyết định kỹ thuật (Decision Ledger)

| ID | Quyết định | Trạng thái | Ghi chú |
|---|---|---|---|
| TD-1 | Vivy = orchestrator, không phải model | **CONFIRMED** | Không distill Gemma4 |
| TD-2 | Chiến lược xâm lấn + kế thừa | **CONFIRMED** | Meta-learning tầng orchestration |
| TD-3 | Cautreo memory bắt buộc (maps + logs) | **CONFIRMED** | Persistent orchestration knowledge |
| TD-4 | Weight pager cho partial weight access | **CONFIRMED** | Q4_K/Q6_K streaming |
| TD-5 | Cross-model = adapter, không share weights | **CONFIRMED** | Vivy ghép output từ nhiều model |
| TD-6 | Mindmap DAG = planning + QC, không thay generator | **CONFIRMED** | |
| TD-7 | Tree map + session tracing (cả hai) | **CONFIRMED** | Index + audit |
| TD-8 | Progressive scaling model core | **CONFIRMED** | HW-fit → upgrade khi sẵn sàng |

---

## Phần 10 — Plan-tune Orchestration (TD-1 → TD-8)

> **Nguồn:** `old-docs/11-consolidated-source-2026-09-26/plans/plan-tune-vivy-orchestration-2026-09-25.md` — `[ISOLATED 26/09/2026]`

### Plan-tune: Vivy Orchestration Architecture (TD-1 → TD-8)

**Source:** Thảo luận 2026-09-25 (DISCUSSION_VIVY_ORCHESTRATION_2026-09-25.md)
**Scope:** Orchestration core + Cautreo memory + Weight management
**Constraint:** Isolate-not-delete, Health Stack green, không sửa immutables

---

#### Decision Ledger (from discussion)

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

#### Wave 1: Cautreo Memory Foundation (TD-3, TD-7)

##### 1A. Cautreo Weight Map — Tree Index

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

##### 1B. Session Log — Append-only + Score

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

#### Wave 2: Weight Pager Integration (TD-4, TD-5)

##### 2A. Weight Pager Interface

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

##### 2B. Cross-Model Adapter

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

#### Wave 3: Mindmap DAG Enhancement (TD-6)

##### 3A. Scored Mindmap DAG

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

#### Wave 4: Progressive Scaling Protocol (TD-8)

##### 4A. Model Upgrade Protocol

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

#### Integration Points (existing code)

| Component | Integrate với |
|---|---|
| `cautreo_weight_map.py` | `cautreo_scoring_journal.py` (REUSE) |
| `weight_pager.py` | `llama_cpp_bridge.py` (REUSE), weight-pager C-ABI |
| `cross_model_adapter.py` | `backend_registry.py` (REUSE) |
| `scored_mindmap_dag.py` | `parallel_context_pipeline.py` (REUSE) |
| `model_upgrade_protocol.py` | `preflight.py` (REUSE) |

---

#### Test Strategy

| Wave | Positive | Negative |
|---|---|---|
| 1 | tree lookup, session replay | empty map, corrupt log |
| 2 | partial load, route+combine | model not registered, memory OOM |
| 3 | plan+score+reroute | cycle detection, score < threshold |
| 4 | readiness gate, migrate | not ready → refuse, ABI break |

---

#### Success Criteria

| Wave | Done khi |
|---|---|
| 1 | Weight map tree lookup + session log replay PASS |
| 2 | Partial load + cross-model route PASS |
| 3 | DAG plan + scoring + reroute PASS |
| 4 | Upgrade protocol + weight inheritance PASS |
| All | ruff 0, mypy 0, pytest 100% (existing + new) |

---

#### Constraints

1. Isolate-not-delete: cũ đánh dấu `[ISOLATED]`, không xóa
2. Không sửa `vivy_train_dataset.jsonl`, `gold_train.jsonl`
3. Gate 9: không PRODUCTION-READY, không 0%, không latency SLA
4. `production_ready = NOT_CLAIMED` until acceptance plan §6
5. Receipt chain: SHA256 prev + self, genesis rule
6. Sandbox capture ≠ EXECUTE_DIRECTLY

---


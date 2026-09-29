# REVIEW VIVY — Thẩm định kỹ thuật toàn hệ thống (Review 3)

> [!IMPORTANT]
> **QUY ƯỚC BẮT BUỘC DÀNH CHO AGENT KẾ THỪA & CHỈNH SỬA TÀI LIỆU:**
> 1. **Ghi chú bắt buộc (Changelog):** Bất kỳ agent nào chỉnh sửa tài liệu này PHẢI bổ sung ghi chú tại mục Lịch Sử Thay Đổi (Tên/ID Agent, thời gian, lý do thay đổi).
> 2. **Chỉ cô lập, KHÔNG xóa bỏ:** TUYỆT ĐỐI KHÔNG xóa bỏ các nội dung/kiến trúc cũ. Toàn bộ nội dung muốn thay đổi phải được đóng khung cô lập và đánh dấu `[ISOLATED / DEPRECATED / REPLACED]`.
> 3. **Đồng bộ D:\2brain đầy đủ:** Đồng bộ và cập nhật đầy đủ mọi thay đổi, quyết định và bài học vào kho tri thức trung tâm `D:\2brain`.

| Mục | Giá trị |
|:--|:--|
| Ngày | 29/09/2026 |
| Tác giả | Claude (phiên review theo yêu cầu của chủ dự án) |
| Trạng thái | **DRAFT — chờ chủ dự án duyệt** |
| Nơi lưu đề xuất | Theo quy ước "5 tài liệu chuẩn": gộp vào `docs/REVIEWS.md` làm **Review 3**. File này để rời chỉ nhằm tiện đọc một lần. |
| Tài liệu đi kèm | `AGENT_BUILD_PLAN_VIVY.md` (chỉ dẫn thiết kế kỹ thuật cho agent) |

---

## 0. Cách đọc tài liệu này

**Nhãn bằng chứng** (mỗi phát hiện đều gắn một nhãn, đúng tinh thần Gate 9 "không tuyên bố nếu không có receipt"):

| Nhãn | Ý nghĩa |
|:--|:--|
| `[RUN]` | Người review đã chạy mã (bản sao trong sandbox Linux) hoặc mô phỏng và quan sát kết quả. Cách tái lập ở Phụ lục A. |
| `[LOG]` | Suy ra trực tiếp từ `_vivy_activity.jsonl` (465 sự kiện, 26–27/09/2026). |
| `[READ]` | Đọc mã/tài liệu; hành vi suy ra từ mã, chưa chạy. |
| `[INFER]` | Suy luận từ nhiều bằng chứng; cần kiểm chứng trước khi coi là sự thật. |
| `[USER]` | Chủ dự án xác nhận. |

**Mức độ:** `S1` chặn tính đúng đắn hoặc an toàn · `S2` làm sai lệch đo lường/kết luận · `S3` nợ kỹ thuật · `S4` lưu ý.

**Giới hạn phạm vi (đọc trước khi tin các kết luận):**

- *Đã đọc đầy đủ mã:* `funnel/`, `core/{state,svd_streams,evolution}`, `llm_bridge/`, `memory/{associative,hebbian_recall,query}`, `orchestrator/{engine,epistemic_gate,decision_controller,model_router,directive_contract,graph_bridge}`, `integration/{vivy_inference_loop,llama_cpp_bridge,cautreo_cartographer,activity_log,cautreo_weight_map,cautreo_session_log,cross_model_adapter}`, `nps_core/*` (evidence_assimilator, state_update, hypothesis_population [trừ `thought_state.py`], thought_ecology, experiment_designer, adaptive_n, verification_tribunal, filter_funnel, codegraph, multimodal_clairvoyance, vivy_interface, vivy_ollama), `vivy/core/{vivy_brain,moe_brain,model_loader,inference,prompts,associative_memory}`, `training/{dataset_extractor,dataset_audit,confirm_gold,check_known_limits,decision_contract}`, notebook Colab.
- *Chỉ đọc cấu trúc/mục lục:* `TECHNICAL_DIRECTION.md` (đọc kỹ §0, §4, §17, §19, §24), `RAW_CONSOLIDATED.md`, `ARCHITECTURE_FINAL.md`, `DESIGN_GAME_CRITERIA_LAYER.md`, `thought_state.py`, `cognitive_graph.py`, `REVIEWS.md` (Review 1 & 2).
- *Chưa đọc:* `TREE_MAP_AND_CHANGELOG.md` (bị nhận là nhị phân), mã native Cautreo (C/DLL), mã thực thi lệnh MetaTrader 5, phần lớn `training/*` và `integration/*` còn lại, `PreflightSteering`, `LoadGovernor`, `WeightPager`, `ThoughtState`, thư mục `tests/` đầy đủ, `scripts/verify_all.ps1`.
- *Môi trường:* các phép chạy thực hiện trên Linux. Những điểm phụ thuộc Windows (định dạng đường dẫn) được đánh dấu là chưa tái hiện.
- *Kết quả thực nghiệm cũ* (`experiment_results_1..4.json`) **không tái lập được** bằng mã hiện tại (xem F-A03); mọi diễn giải về chúng là `[INFER]`.

---

## 1. Tóm tắt điều hành

**Kết luận chung:** ViVy hiện là một tập hợp thành phần chất lượng không đều. Phần **hợp đồng dữ liệu và kỷ luật bằng chứng** (`nps_core`, `decision_controller`, `EvidenceClass`/`LessonStore`, `ActivityLog`, `dataset_audit`, `confirm_gold`, `check_known_limits`) đạt chất lượng tốt và nên giữ. Phần **"trí tuệ"** (phễu lọc lượng tử, N-Core, bộ nhớ liên kết, MoE, tri giác đa phương thức, tribunal, thiết kế thí nghiệm) hoặc là mô phỏng, hoặc đo cấu trúc toán học không gắn với nghĩa của lập luận, hoặc điền hằng số. **Chưa có đường chạy nào thực thi đúng ý tưởng gốc từ đầu đến cuối.**

Tám điểm quyết định:

1. **Pipeline `Orchestrator` chạy trên dữ liệu giả.** Trạng thái là `dict`, `evolve` là đồng nhất, cổng nhận lỗi rồi trả confidence 0.0, KnowledgeInjector không tồn tại nên luồng là placeholder; kết quả luôn `measure / 0.5 / "thought stream 0"`. `[RUN][LOG][USER]` (F-A01…A04)
2. **Mọi confidence hiện có đều không đo tính đúng.** Có ≥6 định nghĩa; riêng bộ nhớ unitary trả confidence **1.000 cho mọi truy vấn** kể cả không liên quan. `[RUN]` (F-C05, F-D02)
3. **Vòng lặp sản phẩm (`VivyInferenceLoop`) không dừng sớm.** Mọi yêu cầu không dùng tool chạy đủ 10 vòng (15/15 lần trong log); CHAT/BATCH luôn báo `DELEGATE`. `[READ][LOG]` (F-B01, F-B02)
4. **Hai phễu lọc cho tín hiệu gần như tùy ý.** Phễu ViVy: `continue` không thể xảy ra khi ≥3 luồng, `delegate` không thể xảy ra. Phễu `nps_core`: 75% trạng thái ngẫu nhiên bị `DELEGATE_EXTERNAL`, và đổi dấu Bell⁺→Bell⁻ đổi tín hiệu. `[RUN]` (F-C01…C03)
5. **Dữ liệu huấn luyện đang dạy mô hình khẳng định "đã kiểm chứng" mà không kiểm chứng.** `dataset_extractor` gắn cứng `AST_VALID_AND_TEST_PASS`, `COGNITIVE_CONSENSUS_VERIFIED`… `[READ]` (F-H01) — **S1**.
6. **Đường giao dịch (trading) không có cổng rủi ro trong mã và có fallback Mock im lặng trả `BUY GOLD 0.92`.** `[READ]` (F-G01, F-G02) — **S1 an toàn**.
7. **Nhiều module mô phỏng đưa ra tuyên bố năng lực sai** (vd. "ViVy đã nhận diện được hình ảnh" trong khi ảnh không bao giờ được đọc; "MoE 70B, 1B active" trong khi mỗi expert ~4 MB). `[READ][INFER]` (F-F01…F-F07)
8. **Vòng lặp NPS chưa khép kín.** Thiếu bộ sinh giả thuyết, executor, và nơi ghi confidence trở lại `ThoughtState`; tribunal đặt `reproduced = (result == "PASSED")` mà không chạy lại gì. `[READ]` (F-E03, F-E09)

**Khuyến nghị chiến lược (chi tiết ở §7):** giữ lớp hợp đồng/sổ bằng chứng của `nps_core` làm xương sống; dùng Gemma qua một backend duy nhất làm bộ suy luận/thực thi; `decision_controller` là thẩm quyền duy nhất điều khiển luồng; chuyển các module "lượng tử" sang nhánh nghiên cứu, chỉ nhận vào sản phẩm khi vượt ngưỡng kiểm chứng ở §8 (T2, T3). Ưu tiên tuần đầu: **wiring test + fail-fast + bộ đo (harness) có baseline**.

---

## 2. Mục tiêu gốc → tiêu chí đo được

Nguồn: `TECHNICAL_DIRECTION.md` §0, §4, §17, §19, §24; `REVIEWS.md` Review 1–2; ADR-001…007. Bảng biến các mục tiêu thành thước đo để "có thể đúng/sai".

| # | Mục tiêu của ý tưởng gốc | Thước đo (kiểm chứng được) | Hiện trạng |
|:--|:--|:--|:--|
| G1 | Quần thể N giả thuyết, ba giá trị tách biệt N_h ≥ N_v ≥ N_e | Log ba con số trên mỗi tác vụ; ràng buộc bất biến được kiểm tự động | Chỉ N_h (chỉ tăng); `n_v` = số nhu cầu; N_e chưa có (F-E05, F-E07) |
| G2 | Thí nghiệm có giá trị thông tin cao | EIG thật tính từ hậu nghiệm; thông tin thu được / lần gọi executor | Hằng số 0.85 (F-E05) |
| G3 | Bằng chứng độc lập và tái lập (INV-07) | Tỷ lệ gói bằng chứng được **chạy lại độc lập** cho cùng kết quả | `reproduced = (result=="PASSED")`, không chạy lại (F-E03) |
| G4 | Cho phép "chưa đủ bằng chứng" (INV-11) | Tỷ lệ trả lời `insufficient_evidence` đúng khi bằng chứng thiếu | Chưa đo; mặc định fail-open (F-B03) |
| G5 | Chính xác (Gate 10) | Accuracy trên bộ held-out so với **baseline Gemma thuần** | Chưa có baseline; kết quả cũ không tái lập (F-A03) |
| G6 | Hiệu chuẩn | ECE, AUROC của confidence dự đoán đúng/sai | Chưa đo; ≥6 định nghĩa (F-C05) |
| G7 | Chi phí/độ trễ | Token, số lần gọi executor, p50/p95 độ trễ | 36–118 s/câu (CPU); AGENTIC 10 vòng (F-B01) |
| G8 | Học an toàn (không thăng cấp thứ chưa kiểm chứng) | Số bài học được lưu / số bài học VERIFIED | 0 lưu (đường chết) (F-B05) |
| G9 | Tái lập | Chạy lại cùng đầu vào → cùng đầu ra và cùng receipt | `id(question)`, RNG toàn cục, stub (F-A08) |
| G10 | Trung thực năng lực (Gate 9) | Số tuyên bố có receipt / tổng tuyên bố | Nhiều tuyên bố không receipt (F-F07) |
| G11 | Tiết kiệm token (codegraph) | Token trung bình/ tác vụ so với đưa nguyên file | Chưa có phép đo (F-E10) |

Bộ chỉ số so sánh ở §17.2 của `TECHNICAL_DIRECTION.md` (baseline: single-LLM chain, self-consistency, tree-of-thought, debate, planner-executor; calibration error; information gain per executor call; executor calls per solved task; token cost; reproducibility) được dùng nguyên văn làm khung ở §8.

---

## 3. Kiến trúc thực tế (as-is)

Hiện có **bốn dòng mã** cùng mang tên ViVy, không có nguồn sự thật duy nhất (SSOT):

```
(A) Orchestrator  [unitary-reasoner: orchestrator/engine.py]   — đường của demo.py và các thực nghiệm JSON
    NL ─LLMClient(60s)→ encode(LLM) → LogicForm → to_dict() (dict, KHÔNG phải QuantumState)
      → evolve(lịch rỗng = đồng nhất) → EpistemicGate(norm() lỗi → 0.0 → DELEGATE_MODEL)
      → ModelRouter (thiếu consent → ESCALATED tức thì) → luồng giả (KnowledgeInjector = stub [])
      → FilterFunnel (measure, 0.5) → decode(LLM; không nhận câu hỏi gốc)

(B) VivyInferenceLoop [integration/vivy_inference_loop.py]     — đường của quickstart / run_vivy.py
    task → SHA-256 → "hidden" → ElasticNCore(2 nhãn cố định) → DirectiveMTPHead → LlamaCppBridge(180s)
      → parse <vivy_thought> → decision_controller.resolve() → (lặp tối đa 10 vòng) → GraphBridge
      → EvidenceClass (independently_verified=False cứng) → LessonStore (không nhận gì)

(C) nps_core      [stdlib, xác định]                            — hợp đồng NPS: ThoughtState, EvidencePacket, ExperimentContract,
    PopulationSnapshot, AssimilationPlan, apply_evidence, tribunal, codegraph … (chưa có runner end-to-end)

(D) vivy/core     [numpy]                                        — ViVyQuantumCore (phễu 4 tầng), MoE 70 expert, inference trading
    ModelBackend: NATIVE_PYTORCH | GGUF_LOCAL | OLLAMA_API | MOCK
```

Ngoài ra: 3 phễu lọc, 3 bản bộ nhớ liên kết, 2 bản SVD, 2 client LLM, ≥2 kiểu `EvidencePacket` (Phụ lục B).

---

## 4. Bảng phát hiện

### Nhóm A — Đường Orchestrator (unitary-reasoner)

| ID | Phát hiện | Bằng chứng | Mức |
|:--|:--|:--|:--|
| F-A01 | `_logic_form_to_state` trả `dict`; `UnitaryEvolution.evolve(state, n_steps=3)` với `schedule=None` dùng lịch rỗng ⇒ không bao giờ gọi `_apply_one`, kết quả là 3 tham chiếu tới cùng dict. Orchestrator cũng không bao giờ truyền cổng nào. | `[READ]` engine.py, evolution.py | S1 |
| F-A02 | `EpistemicGate._compute_confidence` gọi `state.norm()` trên dict → `AttributeError` bị `except Exception: return 0.0` nuốt; `unknown_entities` gán cứng `[]` ⇒ quyết định hầu như luôn `DELEGATE_MODEL`; `NEED_KNOWLEDGE_FORAGING` không thể xảy ra. Router chặn vì thiếu `vivy_consent_id`: **120/120** dispatch của phiên `vivy-task-*` bị `model_route_blocked`. | `[READ]` + `[LOG]` | S1 |
| F-A03 | `core.knowledge_injector` không tồn tại; `try/except ImportError` thay bằng stub `inject()→[]`. Không cảnh báo. Mẫu "import lỗi → stub im lặng" xuất hiện ở 4 chỗ (`core.evolution`, `core.knowledge_injector`, `funnel.filter`, `memory.associative`). Hệ quả: các kết quả 0.85–0.95/`continue` trong 4 file thực nghiệm chỉ tái tạo được với một phiên bản có injector thật; **kết quả cũ không tái lập**. | `[USER][READ]` | S1 |
| F-A04 | Luồng giả `1/(i+1)` cho `FilterFunnel` → `measure`, confidence 0.5, kept = `["thought stream 0"]` (đã chạy). Đây chính là mẫu `answer: "thought stream 0"`, `confidence 0.5` trong thực nghiệm. | `[RUN]` | S1 |
| F-A05 | Decoder chỉ nhận `propositions/relations/query/conclusion/confidence/signal` — **không nhận câu hỏi gốc**; system prompt yêu cầu "nếu confidence thấp thì nói rõ và qualify" ⇒ hedging và từ chối (vd. "tổng 1..100"). | `[READ]` | S2 |
| F-A06 | `self.memory` và `max_iterations` không được dùng; `backtrack/delegate` chỉ ghi log "triggering feedback". Tín hiệu chỉ ảnh hưởng giọng văn Decoder. | `[READ]` | S2 |
| F-A07 | `_evaluate` bắt mọi ngoại lệ và trả `("continue", 0.9)` — thất bại của funnel báo cáo như thành công. `_make_funnel/_make_memory/_make_knowledge` vẫn dùng `__mro__[1]()` (tạo `object()`), trái ADR-005. | `[READ]` | S1 |
| F-A08 | `task_id = f"vivy-task-{id(question)}"` (không tái lập); ở chế độ MPS `apply_gate` sửa tại chỗ nên `history` là n tham chiếu tới một MPS. | `[READ]` | S3 |
| F-A09 | Timeout `LLMClient` 60 s khớp đúng các lỗi `Request timed out after 60.0s`; trên CPU (~14 tok/s) đó là lỗi cấu hình, không phải lỗi suy luận; báo cáo cần tách riêng timeout. | `[READ][INFER]` | S2 |

### Nhóm B — Đường `VivyInferenceLoop` (sản phẩm)

| ID | Phát hiện | Bằng chứng | Mức |
|:--|:--|:--|:--|
| F-B01 | Vòng AGENTIC tiếp tục nếu quyết định thuộc {FORAGE, DELEGATE, CONTINUE, BACKTRACK} và `rounds < max_rounds`. `resolve()` không nhận `tool_failed/repeated_failure/evidence_verified` và bảng ánh xạ không có `HALT` ⇒ quyết định luôn thuộc tập đó ⇒ **mọi phản hồi không có tool call chạy đủ 10 vòng**, mỗi vòng thêm tin nhắn "Provide the next bounded action…". Log: 15/15 `inference_end` có `rounds: 10`, `decision: DELEGATE` (phiên mock). Trên CPU thật: hàng chục giây × 10. | `[READ][LOG]` | S1 |
| F-B02 | Ở CHAT/BATCH `max_rounds = 1` ⇒ `rounds >= max_rounds` ngay vòng 1 ⇒ luôn `DELEGATE`; `run_vivy.py` hiển thị `[DELEGATE | …]` cho mọi câu trả lời CHAT. | `[READ]` | S2 |
| F-B03 | `_parse_epistemic_decision` mặc định `EXECUTE_DIRECTLY` khi thiếu trường (fail-open); nhánh `.get(requested, Decision.DELEGATE)` là mã chết. | `[READ]` | S2 |
| F-B04 | "hidden state" của N-Core = SHA-256 của văn bản nhiệm vụ; hai nhãn giả thuyết cố định ("execute_or_gather_evidence", "delegate_or_forage"); `action_vector`/directive MTP là hàm băm, không mang nghĩa. Trái tuyên bố "Directive-First" của `architecture.md`. `n_core.forward` gọi 2 lần cùng đầu vào. | `[READ]` | S2 |
| F-B05 | `evaluate_multi_stream(independently_verified=False)` cứng và không có `evidence_packet` ⇒ không bao giờ `VERIFIED_RESULT` ⇒ `LessonStore` không nhận bài học nào (0/15 trong log đều `FAST_SIGNAL`). Thiết kế an toàn đúng nhưng không có đường tạo bằng chứng kiểm chứng. | `[READ][LOG]` | S2 |
| F-B06 | Hai client LLM cấu hình mâu thuẫn: `LLMClient` (URL 8000/v1, 60 s, `gpt-4o-mini`, fallback 17 model cloud) vs `LlamaCppBridge` (8080, 180 s, `gemma4-e4b`, `num_ctx 32768`); ADR-007 nói Ollama 11434 + `gemma4:e4b`; manifest nói cửa sổ mục tiêu 2048. Fallback 17 model có thể chuyển model im lặng, làm mất tính tái lập. Thông báo lỗi `run_vivy.py` nói "Ollama" nhưng mặc định cổng 8080 (Cautreo). | `[READ]` | S2 |
| F-B07 | Nhật ký hoạt động trộn sự kiện mock (`t-*`, `test_session`) với sự kiện thật, không có thẻ môi trường; sự kiện `qwen2.5-coder:7b` "PASS" đến từ mock trong khi trọng số không tồn tại. Có nguy cơ bị đọc nhầm/khai thác làm dữ liệu huấn luyện (F-H01). | `[LOG]` | S2 |

### Nhóm C — Phễu lọc, tín hiệu, confidence

| ID | Phát hiện | Bằng chứng | Mức |
|:--|:--|:--|:--|
| F-C01 | Phễu ViVy (`funnel/filter.py`): `confidence ≤ brevity(n) = 1/(1+0.5(n−1))` ⇒ `continue` (ngưỡng 0.6) không thể khi n ≥ 3; n ≥ 5 luôn `backtrack`; `delegate` **không thể xảy ra** với trạng thái chuẩn hóa (bốn luồng cùng σ ≥ 0.875 là bất khả). Mô phỏng 4000 phổ Schmidt/mỗi n. `reject_threshold`, `conflict_penalty`, `_apply_conflict_penalty` là mã chết; `consistency = 1−|σ−σ²|` trộn đơn vị. | `[RUN][READ]` | S2 |
| F-C02 | Trên đầu ra SVD **thật** (300 mẫu/mức): xung đột 71% (2 qubit) → 98% (3) → 100% (≥4); giao thoa 0% ở mọi mức; tín hiệu chuyển từ continue/measure sang **100% backtrack** khi n ≥ 5–6 qubit. GHZ-3 (mạch lạc hoàn toàn) → `measure` + xung đột; |000⟩ → `continue`. Các vector kỳ dị trực chuẩn nên `state_A` khác luồng có overlap ≈ 0 ⇒ "xung đột" luôn đúng. Test hiện có dùng luồng dựng tay, chưa từng dùng đầu ra SVD thật. | `[RUN]` | S2 |
| F-C03 | Phễu `nps_core`: xung đột giữa hai luồng (`cos_sim < −0.5` trên `state_b`) **không thể** (max\|cos\| = 3.6e-16); xung đột pha (Δφ ≥ 0.85π giữa biên độ cơ sở mạnh) kích hoạt ở 302/400 trạng thái ngẫu nhiên → 75% `DELEGATE_EXTERNAL`; Bell⁺⊗\|00⟩ → `CONTINUE_EVOLUTION`, Bell⁻⊗\|00⟩ → `DELEGATE_EXTERNAL` (chỉ khác dấu tổng thể); phụ thuộc thứ tự hòa của top-5 (\|−+++⟩ không bị bắt). `MEASURE_AND_HALT` chỉ khi trạng thái ≈ một trạng thái cơ sở. `known_conflicts` không bao giờ được truyền ⇒ `consistency ≡ 1`. Đầu vào sai kích thước (len 8, phân hoạch (2,2)) vẫn chạy (reshape im lặng). | `[RUN][READ]` | S2 |
| F-C04 | `vivy/core/vivy_brain.py`: tầng 3 dùng `consistency=0.9`, `brevity=0.95` ghi rõ "mock"; reshape vuông bỏ cấu trúc qubit; `NativePyTorchEngine.generate` xử lý một **vector ngẫu nhiên** (`np.random.randn`) và trả `action = tín hiệu funnel`. Trong đường trading, `action` có thể là `"CONTINUE_EVOLUTION"`. | `[READ]` | S1 (nếu dùng) |
| F-C05 | Confidence có ≥6 định nghĩa: (1) phổ Schmidt (funnel ViVy), (2) `norm()` (cổng), (3) LLM tự khai (0.85–0.95), (4) min-confidence N-Core (`graph_bridge`), (5) tuyến tính (calibrator tribunal), (6) `‖Wx‖` (bộ nhớ). Và ≥7 từ vựng quyết định: 4 tín hiệu ADR-006, `EpistemicDecision` (3), `Decision` (6), `FunnelSignal` nps (4), opcode MTP (3), `BOUNDED_SELECTION` (nhãn huấn luyện), chuỗi `<vivy_thought>`. | `[READ]` | S2 |
| F-C06 | Hai quy ước SVD: `core/` LSB-first, ratio = σ²/Σσ²; `nps_core` MSB-first (hàng), ratio = σ/‖σ‖ (ngưỡng 0.05 = 5% so với 0.25% trọng số). ADR-001 nói LSB. `schmidt_rank` dùng 1e-10 trên σ² (ADR-003 nói "singular values"). `decompose` tự reshape "gần đúng" khi sai kích thước. Entropy: log₂ (nps) vs ln (ViVy). Jacobi thuần Python đúng (sai số ~1e-15 so numpy). | `[RUN][READ]` | S3 |
| F-C07 | System prompt Modelfile/`prompts.py` nói với LLM rằng nó có "4-level Filter Funnel" và "1-touch Intuition Retrieval" — khuyến khích tự mô tả năng lực không có. | `[READ]` | S3 |

### Nhóm D — Bộ nhớ

| ID | Phát hiện | Bằng chứng | Mức |
|:--|:--|:--|:--|
| F-D01 | `memory/associative.py`: chế độ sparse bỏ qua η (`_materialise_dense` cộng outer product không nhân η) ⇒ confidence 1-mẫu-truy-vấn-đúng là 0.100 (dense) vs 1.000 (sparse) ở dim 256/257; "sparse" chỉ tiết kiệm lúc nghỉ, mỗi `query` dựng ma trận dim×dim (O(dim²) bộ nhớ, `_make_unitary` O(dim³)); truy vấn ngẫu nhiên vẫn có confidence ~0.43 (20 mẫu, dim 64). Test chỉ khẳng định `conf > 0`. | `[RUN][READ]` | S2 |
| F-D02 | `vivy/core/associative_memory.py`: `use_unitary=True` chiếu W về unitary sau **mỗi** lần `store` ⇒ `conf = ‖Wx‖ = 1` cho mọi truy vấn chuẩn hóa. Kết quả: mẫu đã lưu 1.000, truy vấn không liên quan 1.000 (200 truy vấn: min = max = 1.000). Bộ nhớ không thể báo "không biết". | `[RUN]` | S1 |
| F-D03 | Ba bản `QuantumAssociativeMemory` (numpy `dim/eta`; numpy `vivy/core`; Python thuần `dim_input/dim_output`), thêm `HebbianRecall` (thực chất bình phương tối thiểu `W = Y·pinv(X)`, không Hebbian). ADR-004 chỉ mô tả một. | `[READ]` | S3 |
| F-D04 | `ViVyMoEQuantumCore` ("70B MoE, 1B active"): router = 70 centroid ngẫu nhiên (seed 42) so cosine với `|state|`; `train_expert` huấn luyện trên **trạng thái ngẫu nhiên với đích ngẫu nhiên** (`target_outcome` one-hot ngẫu nhiên) ⇒ liên kết ngẫu nhiên, không tri thức; `np.random.seed(42)…seed(None)` sửa RNG toàn cục. Kích thước file: ~4.19 MB/expert khớp `state_dim=2048, k=64` (2·2048·64 ≈ 2.6×10⁵ tham số phức) `[INFER]` so với tuyên bố "1B". `vivy_core_memory.npy` = 16,777,344 B = ma trận 1024×1024 `complex128` (16,777,216 B) + header 128 B. | `[READ][INFER]` | S2 |
| F-D05 | `CognitiveStateGraph`: dampening (0.5ⁿ), LRU không loại INVARIANT — thiết kế tốt. Nhưng test VM-11 ("≤10%") luôn ghép nút đã bị bác bỏ (0.4) với nút mới (0.8) ⇒ tỷ lệ lặp lỗi 0% **do dựng sẵn**; test thread-safety chỉ kiểm tra không có ngoại lệ. | `[READ]` | S2 |

### Nhóm E — Lớp `nps_core`

| ID | Phát hiện | Bằng chứng | Mức |
|:--|:--|:--|:--|
| F-E01 | Hợp đồng dữ liệu, bất biến, digest, JSON chuẩn hóa, phát hiện chu trình — **tốt** (xem §5). | `[READ]` | — |
| F-E02 | `ConfidenceCalibrator`: `posterior = prior + 0.1·(support − oppose)` kẹp [0,1]; không phải Bayes; 10 gói "supporting" từ cùng executor ⇒ 1.0; hệ số cố định, không hiệu chuẩn theo kết quả (không ECE). | `[READ]` | S2 |
| F-E03 | `VerificationTribunal.evaluate`: `reproduced = (result.upper() == "PASSED")`; không chạy lại lệnh; docstring nói "detects correlated errors" nhưng không có mã; tham số `snapshot` không dùng; `evaluate_with_filter_funnel` chạy funnel trên một vector không liên quan tới bằng chứng. | `[READ]` | S2 |
| F-E04 | `EvidencePacket.result` là chuỗi tự do; `ConflictDetector`/tribunal so sánh `"PASSED"`/`"FAILED"` ⇒ `"PASS"`, `"OK"`… bị coi là kết quả khác (xung đột giả, `reproduced=False`). `ConflictDetector` báo xung đột khi tập kết quả có >1 giá trị, không xét ủng hộ/phản đối, độc lập, tái lập. `packet.py` không có `valid_for_promotion()` mà `graph_bridge` gọi ⇒ có thể tồn tại kiểu `EvidencePacket` thứ hai (chưa thấy). | `[READ]` | S2 |
| F-E05 | `ExperimentBundler`: `expected_information_gain=0.85`, `method="automated_test"`, `cost_budget={"time_s":10}` hằng; kết quả phân biệt `{"pass":"all_pass","fail":"any_fail"}` không phân biệt được giả thuyết nào sai; gom theo thứ tự nhập. `ExperimentContract` chỉ kiểm tra hình thức. `VerificationPortfolio.n_v == len(needs)` và `n_v ≤ n_h` ⇒ N_v đếm nhu cầu, không đếm bộ kiểm chứng độc lập. | `[READ]` | S2 |
| F-E06 | `InformationGainRanker`: `E[IG] = (1−conf)·risk·need` — tích ba số cung cấp sẵn, không phải kỳ vọng thông tin (không entropy/hậu nghiệm); không có thành phần nào sinh ba số này. | `[READ]` | S3 |
| F-E07 | `AdaptiveNController`: N chỉ tăng (`n_h + contradictions//2`), ném lỗi khi vượt ngân sách thay vì kẹp; chỉ N_h; `detect_duplicates` chỉ khớp chuỗi giống hệt (O(n²)), không gộp. | `[READ]` | S3 |
| F-E08 | `thought_ecology.build` chỉ gom quan hệ đã khai báo trong `ThoughtState.graph`; cùng `assumption_id` khác nội dung ⇒ `ConflictingAssumptionError` chặn cả `build` (đáng lẽ là thông tin mâu thuẫn). | `[READ]` | S3 |
| F-E09 | Vòng lặp không khép kín: `apply_evidence` cố ý không tính toán; không có (a) bộ sinh giả thuyết, (b) executor, (c) nơi áp `calibrate` rồi ghi confidence vào `ThoughtState`. | `[READ]` | S1 (kiến trúc) |
| F-E10 | Codegraph incremental (đã chạy): sau `update_file(core/__init__.py)` node `module:core` **biến mất**; 5 cạnh của `module:core.state` và `module:core_utils.helpers` bị **xóa nhầm** (`startswith("module:core")`). `indexer` dùng `.as_posix()`, `incremental` dùng `str()` ⇒ trên Windows node cũ có khả năng không bị loại và bị nhân đôi `[INFER — chưa tái hiện]`. Lỗi cú pháp bị nuốt (bản đầy đủ ghi vào `errors`). Cạnh `imports` chỉ là chuỗi `import:X`, không nối tới id `module:X` ⇒ `change-impact.md` chỉ là danh sách đường dẫn. `ContextCache` khóa theo HEAD nên trả capsule cũ khi cây làm việc có thay đổi chưa commit. "Tiết kiệm token" chưa có phép đo. | `[RUN][READ]` | S2 |
| F-E11 | `LineageIndex`: `contains` dựng lại `set` mỗi lần, `add` sắp xếp lại toàn bộ (O(N² log N) khi xây dần); DFS đệ quy. Ở N ≤ 20 chấp nhận được. | `[READ]` | S4 |

### Nhóm F — Mô phỏng và tuyên bố không có receipt

| ID | Phát hiện | Bằng chứng | Mức |
|:--|:--|:--|:--|
| F-F01 | `vivy_interface`: `ViVyMultimodalEngine.process` chỉ chọn ngôn ngữ và trả văn bản mẫu; khi có ảnh nói "ViVy đã nhận diện được hình ảnh"/"has processed the image" trong khi `VisionEncoder.from_file` chỉ băm nội dung (hoặc băm **đường dẫn** nếu file không tồn tại), gán cứng 1024×1024. Tuyên bố sai. `ViVyChatSession` gán mặc định timestamp `2026-07-25T10:42:00Z` cho mọi tin nhắn. | `[READ]` | S1 (trung thực) |
| F-F02 | `multimodal_clairvoyance`: spectrogram từ `sin/cos` cố định, bỏ qua file; video là danh sách nhãn; vector trạng thái chỉ phụ thuộc "có/không" từng phương thức; "SVD" = chuẩn hàng của ma trận tổng hợp; `alignment` = σ₁/Σσ không đo căn chỉnh liên phương thức; tín hiệu luôn `MEASURE_AND_HALT` (entropy ≈ 4 bit > 2.0), ngược nghĩa với phễu. | `[READ]` | S2 |
| F-F03 | `vivy_ollama`: client không có mã mạng; server trả siêu dữ liệu bịa (parent `llama3.2:3b`, 1.15B, digest giả); cổng mặc định 11434 trùng Ollama thật; `start_in_background` không gọi `serve_forever`; không có `/v1/chat/completions` ⇒ `LLMClient` nhận 404 → vòng fallback 17 model. Modelfile `FROM llama3.2:3b`, template ChatML lệch template gốc; `export_modelfile` ghi đè `Modelfile` ở thư mục hiện tại. | `[READ]` | S2 |
| F-F04 | `CautreoCartographer.scan_model`: domain của mỗi lớp theo độ sâu (20/45/75%), "giả lập streaming 120 MB", `dummy_row_sums` từ `sin`, "nơ-ron nổi bật" = `range(0, top_k)`, `model_path` bị bỏ qua; test khẳng định "lớp 45 của llama-3-70b là mql5_finance_law". Không đọc trọng số nào. | `[READ]` | S2 |
| F-F05 | `WeightMap.lookup` quét O(n) (tài liệu nói O(log n)); đăng ký `qwen2-70b` không có trên đĩa; `SessionLog` "bất biến" nhưng dataclass có thể sửa, không bền vững, `score` mặc định 0.5 ⇒ `replay()` vô nghĩa nếu không chấm điểm thật. | `[READ]` | S3 |
| F-F06 | `CrossModelAdapter.combine_outputs`: "soft blend" **cắt ký tự** (primary[:(1−r)·len] + secondary[:r·len]) — cắt câu giữa chừng, không phải hợp nhất; `blend_ratio` mang hai nghĩa (ngưỡng độ phức tạp trong `route`, tỷ lệ trộn trong `combine`); `complexity` mặc định 0.5, không có bên cung cấp. | `[READ]` | S3 |
| F-F07 | Tuyên bố không receipt: "Epistemic Rigor 99.2%" (manifest), MMBench/DocVQA của Qwen2-VL-72B (số công bố của mô hình gốc, chưa đo trên hệ thống lượng tử hóa/phân trang), "Zero-OOM", "0 ms", "70B MoE / 1B active", "Peak VRAM < 6.5 GB", VM-11 "0%", Qwen2-VL-72B 44 GB trên máy khuyến nghị 16 GB RAM. | `[READ]` | S2 |

### Nhóm G — Đường giao dịch (trading)

| ID | Phát hiện | Bằng chứng | Mức |
|:--|:--|:--|:--|
| G-01 | `VIVY_TRADING_SYSTEM_PROMPT` ghi "CẤM GÁC CỔNG LẬP TRÌNH: không có bộ lọc, giới hạn tốc độ hay trần rủi ro trong mã; mọi quản trị rủi ro/SL/TP/thời điểm do LLM quyết định 100%", và mô tả Python là "Hands" thực thi lệnh MT5. `ViVyInferenceEngine` chỉ ép kiểu (`float(raw.get("volume", 0.01))`, SL/TP mặc định 0.0, confidence tự khai mặc định 0.5), không kiểm tra giới hạn/finite/dấu. Chưa thấy mã thực thi lệnh. | `[READ]` | S1 an toàn |
| G-02 | `GGUFLocalEngine` khi thiếu `llama_cpp` chuyển sang `MockLocalEngine` **im lặng**; `MockLocalEngine` luôn trả `BUY GOLD 0.1, SL 2350, TP 2390, confidence 0.92`; `load_engine` với backend lạ cũng trả Mock. | `[READ]` | S1 an toàn |
| G-03 | `NativePyTorchEngine` (F-C04) đưa tín hiệu funnel làm `action` trên vector ngẫu nhiên. | `[READ]` | S1 (nếu bật) |

### Nhóm H — Dữ liệu và huấn luyện

| ID | Phát hiện | Bằng chứng | Mức |
|:--|:--|:--|:--|
| F-H01 | `DatasetExtractor` **bịa nhãn bằng chứng**: `extract_from_activity_log` đặt `user_prompt = "Task Execution: <session_id>"`, `Expected_Evidence: AST_VALID_AND_TEST_PASS` cứng, `reward = 1.0` cho mọi `inference_end` không ERROR (mặc định `OBSERVED`), tức cả các phiên mock/`DELEGATE`; `ingest_2brain_reasoning` gắn cứng `EXECUTE_DIRECTLY` + `COGNITIVE_CONSENSUS_VERIFIED`; `ingest_llava_traces` gắn cứng `MULTIMODAL_GROUNDING_VERIFIED`. Huấn luyện SFT trên dữ liệu này dạy mô hình khẳng định "đã kiểm chứng" vô điều kiện. | `[READ]` | S1 |
| F-H02 | Notebook Colab: chỉ 2 mẫu bootstrap × 3 epoch nếu thiếu file dữ liệu; nhắc "RLCD/Proper Scoring" nhưng chỉ có SFT; xuất `--outtype q8_0` nhưng đặt tên `vivy_1.5b_q4km.gguf`; "Peak VRAM < 6.5 GB" chưa đo; `trl>=0.8.0` không ghim (API `SFTConfig` đổi giữa các bản). | `[READ]` | S3 |
| F-H03 | `confirm_gold` ở chế độ `auto-reviewed` đóng dấu `reviewer=oracle_<rule>` và `status=REVIEWED` nhưng dùng `kind="human-accept"` cho receipt — trộn tự động với người duyệt; giảm giá trị của "độc lập". (Nhưng nguồn không bị sửa, có reviewer/`reviewed_at` cho từng dòng.) | `[READ]` | S2 |
| F-H04 | `dataset_audit` (rò rỉ group-split, near-duplicate, provenance), `decision_contract` (tách Input/Prediction/Label), `check_known_limits` — thiết kế tốt nhưng chưa nối với `DatasetExtractor` (schema khác: `messages` vs `context_state/candidates`); `check_known_limits` cho PASS khi một giới hạn không có tham chiếu receipt. | `[READ]` | S3 |

### Nhóm I — Hạ tầng, tài liệu, kiểm thử

| ID | Phát hiện | Bằng chứng | Mức |
|:--|:--|:--|:--|
| F-I01 | Lệch tài liệu: ADR-005 (evolve "requires schedule") vs mã (`schedule=None`); ADR-003 (default threshold) vs mã; 19/19 test (architecture.md/quickstart) vs 695+730 (CLAUDE.md); 11 vs 17 cổng `verify_all`; Python ≥3.11 (pyproject) vs 3.10 (setup.sh/quickstart); `setup.py` (`nps-core`, layout `src/`) vs pyproject (`vivy-core`); `asyncio_mode="auto"` nhưng thiếu `pytest-asyncio` trong dev deps; `README` "HebbianRecall O(1)" (đã cô lập một phần); `ADR-006` mô tả ý nghĩa tín hiệu không khớp tiêu chí thực. | `[READ]` | S3 |
| F-I02 | Kiểm thử: assertion lỏng (`conf > 0`), test vòng tròn (VM-11), test khóa hành vi rủi ro (`test_client`: 17 model, fallback sang `gpt-4o-mini`), test gắn môi trường (`is_native_cautreo_available() is True` fail trên máy không có DLL), không test funnel bằng đầu ra SVD thật, demo dùng lớp giả `_LowState` và `assert freed_pct >= 60` là hằng đúng (`purge_all` xóa 100%). | `[READ]` | S2 |
| F-I03 | `ContextCacheController` là kho chunk Python (đếm byte), không giải phóng KV cache của LLM ⇒ "Rào cản #3" (cạn cửa sổ ngữ cảnh) chưa được xử lý. | `[READ]` | S2 |
| F-I04 | Cautreo native (DLL/`cautreo-server`) không nằm trong đường đã kiểm thử/thực nghiệm (đi qua `llm_bridge`/Ollama); manifest trỏ GGUF `vivy-gemma-e4b-q4km.gguf` (8.95 GB) còn quickstart kéo `gemma4:e4b` (9.6 GB); Review 1 ghi native forward lệch parity. | `[READ]` | S2 |
| F-I05 | `ActivityLog`: "append-only" là quy ước (không khóa/hash-chain); regex che bí mật chỉ bắt dạng `key=value`. `Modelfile`/`MTP HMAC` chưa đọc key management. | `[READ]` | S4 |

---

## 5. Điểm mạnh nên giữ

| ID | Thành phần | Lý do |
|:--|:--|:--|
| P-01 | `nps_core` hợp đồng: `ThoughtState`, `PopulationSnapshot`, `EvidencePacket`, `AssimilationPlan`, `apply_evidence` | Bất biến, xác thực chặt, nguyên tử, digest trước/sau, JSON chuẩn hóa, lỗi có `path`. |
| P-02 | `VerificationPortfolio` | Ràng buộc chính xác snapshot (`snapshot_digest`), phủ nhu cầu ↔ thí nghiệm. |
| P-03 | `orchestrator/decision_controller.py` | Quy tắc "HALT cần bằng chứng độc lập", giới hạn vòng, fail-safe có thứ tự ưu tiên rõ; test tốt. (Chỉ chưa được nối đủ đầu vào — F-B01.) |
| P-04 | `EvidenceClass` + `LessonStore` | Chỉ `VERIFIED_RESULT` được thăng cấp; cô lập bài học có lý do; bền vững qua nhiều instance. |
| P-05 | `ActivityLog` | JSONL, che bí mật, ghi sự kiện vận hành ("không tuyên bố hoàn thành"). |
| P-06 | `dataset_audit`, `decision_contract`, `confirm_gold`, `check_known_limits` | Rò rỉ theo nhóm, near-dup, provenance, không sửa nguồn, reviewer từng dòng, đối chiếu limitations↔receipts. |
| P-07 | `codegraph/indexer.py` | Xác định, an toàn đường dẫn, bỏ symlink, `shell=False`, trạng thái FRESH/UNVERSIONED (chỉ cần sửa incremental và nối cạnh). |
| P-08 | `chat_safe` + `LlamaCppBridge` | Báo `DELEGATE` thay vì ném ngoại lệ; ghi nhận "process success ≠ semantic correctness". |
| P-09 | Kỷ luật tài liệu | Quy tắc cô lập-không-xóa, Gate 9 (đã cô lập nhiều tuyên bố "O(1)", "0 ms", "0%"), changelog. |
| P-10 | `CognitiveStateGraph` dampening/LRU/INVARIANT | Ý tưởng "không lặp lại thất bại" đúng hướng (cần phép đo thật thay test vòng tròn). |

---

## 6. Nguyên nhân gốc

| RC | Nguyên nhân | Phát hiện liên quan |
|:--|:--|:--|
| RC1 | **Không có test tích hợp trên đường chạy thật.** Test chạy trên đối tượng dựng tay/mock; demo dùng lớp giả. | F-A01…A04, F-C02, F-I02 |
| RC2 | **Stub và fallback im lặng** (`ImportError→stub`, `except Exception→giá trị mặc định`, Mock trong đường sản phẩm). Hệ thống báo cáo trơn tru khi thiếu mảnh. | F-A03, F-A07, G-02 |
| RC3 | **Cấu trúc toán ≠ ngữ nghĩa.** Phổ Schmidt, pha, entropy cơ sở được diễn giải thành "mạch lạc/mâu thuẫn/hội tụ" mà chưa từng kiểm chứng tương quan với tính đúng. | F-C01…C04, F-D02 |
| RC4 | **Tuyên bố đi trước bằng chứng.** Docstring/manifest/prompt mô tả năng lực chưa có (Gate 9 chỉ mới áp dụng một phần). | F-F01…F07, F-C07 |
| RC5 | **Nhân bản mã không SSOT.** 3 phễu, 3 bộ nhớ, 2 SVD, 2 client, ≥7 từ vựng quyết định, ≥6 confidence. | Phụ lục B |
| RC6 | **Vệ sinh bằng chứng.** Sự kiện mock trộn thật; nhãn huấn luyện bịa; oracle tự duyệt gắn nhãn "human". | F-B07, F-H01, F-H03 |
| RC7 | **Không có baseline.** Chưa từng so Gemma thuần với pipeline, nên không biết pipeline cộng hay trừ giá trị. | G5 |

---

## 7. Các phương án

### 7.1 Phương án kiến trúc

| | **A — "Directive Orchestrator + Sổ bằng chứng"** *(khuyến nghị)* | **B — Dựng lại quanh `nps_core`** | **C — Đóng băng nghiên cứu** |
|:--|:--|:--|:--|
| Ý tưởng | Sản phẩm = `VivyInferenceLoop` (Gemma qua **một** backend) + `decision_controller` là thẩm quyền điều khiển + `nps_core` làm sổ hợp đồng/bằng chứng. Module lượng tử → nhánh nghiên cứu, chỉ nhận vào sản phẩm khi vượt T2/T3. | Bỏ đường (A)/(B) hiện tại; xây vòng NPS đầy đủ: LLM sinh quần thể, executor kiểm chứng, tribunal, calibrator, adaptive N. | Giữ nguyên hiện trạng làm nghiên cứu, chỉ sửa lỗi an toàn và gắn nhãn SIMULATED. |
| Ưu | Nhanh có sản phẩm chạy được và đo được; dùng lại phần tốt; rủi ro thấp. | Đúng ý tưởng gốc nhất; giá trị nghiên cứu cao. | Chi phí thấp nhất. |
| Nhược | Ý tưởng gốc thực thi từng phần (thêm dần qua WP-06…08). | Chi phí lớn; cần executor/sandbox thật; chậm trên CPU 14 tok/s. | Không có sản phẩm hoàn thiện; các lỗi S1 vẫn cần sửa. |
| Chi phí | M | L–XL | S |
| Điều kiện thành công | T0–T5 đạt | T2–T8 đạt | Không đặt ngưỡng |

**Khuyến nghị:** A, với lộ trình tiến dần tới B (WP-06…WP-08) khi harness đã chứng minh giá trị. Đây cũng là thứ tự phù hợp với ràng buộc phần cứng (CPU ~14 tok/s, cửa sổ 2048).

### 7.2 Phương án theo hạng mục

| ID | Phương án | Giải quyết | Giả thuyết cần kiểm chứng | Chi phí | Rủi ro |
|:--|:--|:--|:--|:--|:--|
| O-01 | **Fail-fast wiring**: cấm stub im lặng ở chế độ production; `WiringReport` REAL/STUB/MISSING lúc khởi động; ghi vào ActivityLog. | F-A03, F-A07, G-02 | Số stub trong production = 0 | S | Thấp |
| O-02 | **Bộ đo (harness) có baseline**: bộ câu hỏi ≥120 (dev/held-out), checker lập trình, receipt JSON, chạy A/B/C. | G5, RC1, RC7 | Pipeline không kém baseline > 2 điểm % | M | Trung bình (chi phí tính toán CPU) |
| O-03 | **Sửa điều khiển vòng lặp**: truyền đủ đầu vào cho `resolve()`, fail-closed khi thiếu quyết định, `HALT` khi có bằng chứng được xác minh, bỏ luật ngân sách ở chế độ 1 vòng. | F-B01…B03 | Trung vị vòng ≤ 3; 0 false-halt | S–M | Thấp |
| O-04 | **Hợp nhất backend LLM**: một `LLMBackend`, một cấu hình (URL, model, timeout, ctx), ghi model-id thật vào mỗi receipt, bỏ fallback 17 model cloud. | F-B06, F-A09 | Tái lập theo model-id | S | Thấp |
| O-05 | **Một định nghĩa confidence có hiệu chuẩn**: self-consistency (k mẫu), kết quả kiểm chứng, calibration isotonic trên dev; các định nghĩa cũ chỉ còn là đặc trưng để ablation. | F-C05, G6 | ECE ≤ 0.10, AUROC ≥ 0.70 | M | Trung bình (tốn token) |
| O-06 | **Tribunal thật**: sandbox chạy lại lệnh, phát hiện lỗi tương quan theo executor/họ mô hình, calibrator log-odds có độ tin cậy và trần đóng góp theo nhóm. | F-E02…E04 | ≥90% lỗi gài được phát hiện | M | Trung bình |
| O-07 | **Thiết kế thí nghiệm bằng EIG thật** + bộ kiểm hợp lệ từ chối `all_pass/any_fail` cho đa giả thuyết. | F-E05, F-E06 | EIG tương quan thực tế (Spearman ≥ 0.6) | M | Trung bình |
| O-08 | **Khép vòng lặp NPS**: LLM sinh quần thể (JSON schema), executor, `apply_evidence`, calibrator, adaptive N với ràng buộc N_h ≥ N_v ≥ N_e; cho phép `insufficient_evidence`. | F-E09, G1, G4 | Vòng chạy end-to-end trên 30 tác vụ | L | Cao |
| O-09 | **Hợp nhất bộ nhớ**: giữ một bản (`memory/associative.py`), sửa η ở sparse, confidence = độ tương tự đã hiệu chuẩn; so với kNN embedding. | F-D01…D03 | Truy vấn không liên quan ≤ 0.2 ở ≥95% | S–M | Thấp |
| O-10 | **Đường dữ liệu sạch**: mẫu huấn luyện bắt buộc có `evidence_receipt_id`; cấm chuỗi bằng chứng cứng; chạy `dataset_audit`; tách theo nhóm; tập held-out. | F-H01…H04 | 0 nhãn bịa; 0 rò rỉ | M | Thấp |
| O-11 | **Sửa và đo codegraph**: sửa incremental, nối cạnh import với module, đo token tiết kiệm. | F-E10 | Tiết kiệm ≥30% token ở chất lượng tương đương | S–M | Thấp |
| O-12 | **Giao diện trung thực**: bridge OpenAI/Ollama thật (proxy tới backend) hoặc bỏ; gắn `SIMULATED` cho module mô phỏng; sổ năng lực (capability ledger). | F-F01…F07, RC4 | 0 tuyên bố năng lực không có lời gọi model | S | Thấp |
| O-13 | **Lớp an toàn giao dịch**: `RiskGate` xác định trong mã (độc lập LLM), fail-closed, chế độ paper mặc định, cấm Mock ở production. | G-01…G-03 | 100% đầu ra bất thường bị chặn | M | Thấp; **cần chủ dự án quyết định (D-3)** |
| O-14 | **Nhánh nghiên cứu lượng tử** với giả thuyết đăng ký trước (H1: tín hiệu SVD dự đoán tính đúng ngoài self-consistency; H2: trích xuất MPS nhanh hơn dày đặc ở n ≥ 20 mà không mất thông tin). | RC3 | AUROC tăng ≥ 0.05 khi thêm đặc trưng | M | Có thể kết luận "không giúp" |
| O-15 | **Đồng bộ tài liệu/ADR/CI**: cập nhật ADR-003/005/006/007, gộp `setup.py`/pyproject, số test/cổng, thêm `pytest-asyncio`. | F-I01 | Không mâu thuẫn | S | Thấp |

### 7.3 Danh sách CÔ LẬP / ĐÓNG BĂNG (theo quy tắc "cô lập, không xóa")

| Đối tượng | Đề xuất | Điều kiện quay lại |
|:--|:--|:--|
| `multimodal_clairvoyance/*` | `[ISOLATED]` gắn `SIMULATED` | Có lời gọi model thị giác/âm thanh thật + test hai đầu vào khác nhau → đầu ra khác nhau |
| `vivy_interface/reasoning_engine.py`, `vision.py` | `[ISOLATED]` (tuyên bố "đã nhận diện ảnh" sai) | Thay bằng backend thật (Qwen2-VL) |
| `vivy_ollama/*` | `[ISOLATED]` cho tới khi là proxy thật | Proxy chuyển tiếp tới backend, có test tương thích giao thức |
| `ViVyMoEQuantumCore` + 70 expert `.npz` | `[ISOLATED]`; đổi tên tuyên bố | Có bài đánh giá tri thức thật |
| `vivy/core/vivy_brain.py` (native engine), `MockLocalEngine` ở production | `[ISOLATED]`/cấm production | RiskGate + đánh giá |
| `CautreoCartographer.scan_model` | Gắn `SIMULATED`; không tiêm vào prompt | Quét trọng số thật |
| Phễu ViVy (`funnel/filter.py`) và phễu nps | Đóng băng làm đặc trưng nghiên cứu (O-14) | Vượt H1 |
| Bộ nhớ liên kết bản `vivy/core` và bản Python thuần | `[ISOLATED]` (giữ tham chiếu) | — |

---

## 8. Kế hoạch test tuần tự và mục tiêu kết quả

**Nguyên tắc chung:** mỗi bước có (a) mục tiêu, (b) dữ liệu, (c) thước đo, (d) ngưỡng đạt/không đạt, (e) điều kiện dừng và (f) receipt (`evidence/T<n>-<run_id>.json`). Không sang bước sau nếu bước trước không đạt (trừ khi chủ dự án ghi quyết định ngoại lệ vào changelog). Tất cả chạy với **model-id thật** ghi trong receipt và seed cố định.

**Bộ dữ liệu đánh giá V1 (đề xuất):** 120 câu = 4 lĩnh vực (lượng tử, toán, đồ thị, tính toán) × 30; mỗi lĩnh vực chia dev 8 / held-out 22; đáp án kiểm bằng checker lập trình (so số, tập, biểu thức chuẩn hóa), **không dùng khớp chuỗi con lỏng**; 30 câu đối kháng (thiếu dữ kiện, câu hỏi không thể trả lời, đầu vào gây hiểu nhầm). Câu hỏi held-out **không được nằm trong bất kỳ bảng tri thức nào của hệ thống**.

| Bước | Tên | Việc làm | Thước đo | Ngưỡng ĐẠT | Dừng nếu |
|:--|:--|:--|:--|:--|:--|
| **T0** | Wiring smoke | Chạy `Orchestrator` và `VivyInferenceLoop` với LLM giả, khẳng định: state là `QuantumState` (đường A) hoặc đường A bị vô hiệu rõ ràng; `evolve` với lịch không rỗng làm đổi trạng thái; không stub nào trong production; mỗi tín hiệu điều khiển gây hành vi khác. | Số khẳng định đạt | 100% | Bất kỳ stub production |
| **T1** | Tái lập & dự đoán | Chạy lại 35 câu thực nghiệm cũ với mã hiện tại. | Phân phối tín hiệu/confidence | **Dự đoán:** 100% `measure`/0.5 (xác nhận F-A03/A04). Nếu khác → điều tra trước khi tiếp | — |
| **T2** | A/B/C ablation | (a) Gemma thuần, (b) pipeline hiện tại, (c) pipeline + câu hỏi gốc vào Decoder, (d) đường sản phẩm. Cùng 120 câu, k=1, T=0. | Accuracy (Wilson 95%), độ trễ p50/p95, token, số lần gọi | Pipeline ≥ baseline − 2 điểm %; muốn giữ thành phần lượng tử phải ≥ baseline + 5 điểm % (McNemar p<0.05) ở ≤ 2× độ trễ | Pipeline < baseline − 5 điểm % → dừng, thiết kế lại |
| **T3** | Hiệu chuẩn confidence | Với mỗi định nghĩa (phổ Schmidt, norm, LLM khai, N-Core min, tuyến tính, self-consistency k=5, verifier) tính dự đoán đúng/sai. | ECE, AUROC, Brier | Định nghĩa được chọn: ECE ≤ 0.10 và AUROC ≥ 0.70 trên held-out | Không định nghĩa nào đạt → chỉ dùng verifier |
| **T4** | Điều khiển vòng lặp | 60 tác vụ (30 đơn giản không tool, 30 có tool/lỗi tool); kiểm `resolve()`. | Trung vị vòng; false-halt; đường INCIDENT/BACKTRACK; tỷ lệ DELEGATE | Trung vị ≤ 3 vòng (đơn giản); 0/30 false-halt đối kháng; INCIDENT sau 1 lỗi, BACKTRACK sau lỗi lặp; CHAT không luôn `DELEGATE` | Vòng lặp chạm trần ≥ 20% |
| **T5** | Nhánh cổng/định tuyến | Mỗi nhánh (CONTINUE/FORAGE/DELEGATE/HALT/BACKTRACK/INCIDENT) phải với tới được; đo độ chính xác DELEGATE. | Phân phối; độ chính xác | Không nhánh nào >70% trừ khi có lý do; mỗi nhánh có ≥1 ca đúng | Nhánh không thể tới |
| **T6** | Tribunal & thí nghiệm | Gài 30 lỗi có chủ đích vào 30 giả thuyết; đo phát hiện, số thí nghiệm/lỗi, EIG dự đoán vs thực tế. | Recall phát hiện; thí nghiệm trung vị/lỗi; Spearman(EIG) | Recall ≥ 90%; trung vị ≤ 3; Spearman ≥ 0.6; `reproduced` chỉ True khi chạy lại độc lập | Recall < 70% |
| **T7** | Bộ nhớ | 200 cặp lưu, 200 truy vấn liên quan, 200 không liên quan; so kNN embedding. | recall@1; tỷ lệ truy vấn không liên quan có confidence ≤ 0.2 | recall@1 ≥ kNN − 5 điểm %; ≥95% không liên quan ≤ 0.2 | Confidence hằng số |
| **T8** | Học an toàn | Phát lại log; thử thăng cấp đủ loại `EvidenceClass`. | Số thăng cấp không VERIFIED; khả năng dựng lại từ log | 0 thăng cấp sai; 100% dựng lại | Bất kỳ thăng cấp sai |
| **T9** | Dữ liệu huấn luyện | Chạy `dataset_audit` + quét chuỗi bằng chứng cứng trên mọi tập SFT. | rò rỉ nhóm; near-dup chéo split; provenance thiếu; nhãn bịa | 0; 0; 0; 0 | Bất kỳ nhãn bịa |
| **T10** | An toàn giao dịch (chỉ paper) | 60 đầu ra LLM đối kháng (volume âm/NaN, thiếu SL, symbol lạ, vượt trần) + tắt backend + thiếu `llama_cpp`. | Số lệnh lọt qua; fail-closed | 0 lệnh lọt; 100% fail-closed; không Mock ở production | Bất kỳ lệnh lọt |
| **T11** | Hiệu năng | Đo độ trễ theo chế độ trên CPU mục tiêu; timeout; token. | p50/p95 | Ngân sách do chủ dự án đặt (đề xuất: chat đơn ≤ 60 s p50; agentic ≤ 3 vòng p50) | Timeout > 5% |
| **T12** | Nhánh nghiên cứu | H1/H2 (O-14) đăng ký trước. | ΔAUROC; tốc độ; sai số | H1: ≥ +0.05; H2: nhanh hơn ở n ≥ 20, sai số ≤ 1e-6 | Không đạt → giữ đóng băng |

**Điều kiện coi ViVy "hoàn thiện" (Definition of Done cấp hệ thống):** T0, T2 (đạt ngưỡng không kém baseline), T3, T4, T8, T9, T10 đạt; mọi tuyên bố năng lực có receipt; tài liệu đồng bộ (T-doc).

---

## 9. Rủi ro

| Rủi ro | Xác suất | Ảnh hưởng | Giảm thiểu |
|:--|:--|:--|:--|
| Pipeline không vượt baseline Gemma thuần (T2) | Cao | Cao (thay đổi chiến lược) | Chấp nhận kết quả; chuyển O-14; sản phẩm dựa trên (A) |
| Chi phí tính toán đo trên CPU 14 tok/s quá lớn | Cao | Trung bình | Chạy harness qua đêm/Colab; giảm k; cache; dùng model nhỏ hơn để dev |
| Bằng chứng "kiểm chứng" cho tác vụ ngôn ngữ mở khó tự động hóa | Trung bình | Cao | Chọn miền có verifier (toán, mã, đồ thị) trước |
| Nợ mypy/ruff (164/109) ngoài phạm vi che lỗi thật | Trung bình | Thấp | Mở rộng scope theo từng WP |
| Trọng số 6.4 GB chỉ xác minh bằng dung lượng | Thấp | Trung bình | Thêm SHA-256 manifest riêng (WP-14) |
| Đường giao dịch gây tổn thất thật | Thấp–Trung bình | Rất cao | O-13 bắt buộc trước khi chạy tài khoản thật |
| Agent tự "sửa" để test qua thay vì sửa gốc | Trung bình | Cao | Test bất biến + receipt; cấm sửa ngưỡng/oracle trong cùng PR sửa lỗi |

---

## 10. Quyết định cần chủ dự án chốt

| ID | Câu hỏi | Mặc định đề xuất |
|:--|:--|:--|
| D-1 | Chọn phương án kiến trúc A, B hay C (§7.1)? | **A**, tiến dần tới B |
| D-2 | Có giữ nhánh nghiên cứu lượng tử (O-14) không, và với ngân sách nào? | Giữ, ngân sách giới hạn, giả thuyết đăng ký trước |
| D-3 | Cho phép `RiskGate` bắt buộc trong mã cho đường giao dịch (thay đổi triết lý "CẤM GÁC CỔNG LẬP TRÌNH")? | **Có** — tổn thất tài chính không thể đảo ngược |
| D-4 | Backend chuẩn: Ollama (`gemma4:e4b`) hay Cautreo `cautreo-server` (GGUF `vivy-gemma-e4b-q4km`)? | Một backend duy nhất qua `LLMBackend`; chọn Ollama cho phát triển, Cautreo sau khi có parity |
| D-5 | Tìm lại hay viết lại `KnowledgeInjector`? | Tìm lại (`git log --all`); nếu không có thì **không viết lại** — bỏ tham chiếu |
| D-6 | Cô lập các module mô phỏng (§7.3) ngay? | Có, gắn `SIMULATED` |
| D-7 | Chủ sở hữu bộ dữ liệu đánh giá V1 và quy trình giữ held-out? | Chủ dự án; agent không được xem held-out khi phát triển |
| D-8 | Ngân sách độ trễ/token cho T11? | Theo đề xuất ở T11 |
| D-9 | Chuẩn hóa Python 3.11+ và gỡ `setup.py`/gộp pyproject? | Có |
| D-10 | Có tiếp tục huấn luyện "ViVy Tiny Brain" (Colab) trước khi T9 đạt? | **Không** — chờ dữ liệu sạch |

---

## Phụ lục A — Tái lập bằng chứng `[RUN]`

Các phép chạy dùng bản sao mã trong sandbox (`/home/claude/w`), Python 3, numpy/scipy. Mỗi mục nêu điều đã kiểm và kết quả.

| Mã | Điều kiểm | Kết quả |
|:--|:--|:--|
| A1 | Funnel ViVy với 3 luồng giả `1/(i+1)` | `measure`, confidence 0.5, kept `["thought stream 0"]` |
| A2 | Funnel ViVy, phổ Schmidt chuẩn hóa ngẫu nhiên (4000/mỗi n = 1..8; `amplitude_ratio=σ²`) | n=1: 100% continue · n=2: continue 1722/4000, measure 2278 · n=3: measure 1944, backtrack 2056 · n=4: measure 993, backtrack 3007 · n≥5: 100% backtrack · `delegate`: 0 |
| A3 | Funnel ViVy trên SVD thật (300/mức, phân hoạch nửa) | Xung đột 71/98/100/100/100% (2..6 qubit), giao thoa 0%; GHZ-3 → measure 0.374 + xung đột; \|000⟩ → continue 1.0 |
| A4 | `associative.py`: 1 mẫu, truy vấn đúng | dim 8, 256 (dense): 0.100; dim 257 (sparse): 1.000; truy vấn ngẫu nhiên (20 mẫu, dim 64, η=1): 0.426 |
| A5 | `vivy/core/associative_memory.py` (unitary) | Truy vấn đúng 1.000; không liên quan 1.000; 5 mẫu × 200 truy vấn không liên quan: min = max = 1.000 |
| A6 | SVD Jacobi thuần Python `nps_core` vs numpy | Sai số giá trị kỳ dị ≤ ~1e-15; tái dựng khớp (các hình (2,2), (4,4), (8,8), (4,2), (2,4)) |
| A7 | Phễu `nps_core` trên 400 trạng thái ngẫu nhiên 4 qubit, phân hoạch (2,2) | 302 `DELEGATE_EXTERNAL` (đều do xung đột pha), 98 `CONTINUE_EVOLUTION`; max\|cos\| giữa `state_b` của 2 luồng = 3.6e-16 |
| A8 | Phễu `nps_core` trạng thái có cấu trúc | \|0000⟩ → MEASURE_AND_HALT (H=0); \|++++⟩ → CONTINUE; Bell⁺⊗\|00⟩ → CONTINUE; Bell⁻⊗\|00⟩ → DELEGATE; vector len 8 vẫn chạy |
| A9 | Codegraph incremental (dự án nhỏ) | Module node `module:core` mất; 5 cạnh module khác bị xóa nhầm |

**Nhật ký hoạt động (`[LOG]`):** 465 sự kiện (26/09 02:34 UTC → 27/09 11:22 UTC): `model_route_blocked` 165 (120 phiên `vivy-task-*`, 45 phiên `t-*`); `decision_assessment` 150; `model_attempt` 75 (FAIL 45, PASS 30, một phần mock); `model_route` 45; `inference_end` 15 (đều `DELEGATE`, `rounds: 10`, trung vị ~6 ms ⇒ mock), toàn bộ `evidence_class = FAST_SIGNAL`.

**Chưa tái hiện:** hành vi đường dẫn Windows (F-E10 phần `as_posix`), hành vi thật của `KnowledgeInjector`, thời gian trên CPU mục tiêu.

---

## Phụ lục B — Kiểm kê trùng lặp

| Thành phần | Bản 1 | Bản 2 | Bản 3 |
|:--|:--|:--|:--|
| Phễu lọc | `funnel/filter.py` (Schmidt; continue/measure/backtrack/delegate) | `nps_core/filter_funnel` (4 tầng; CONTINUE_EVOLUTION/MEASURE_AND_HALT/BACKTRACK/DELEGATE_EXTERNAL) | `vivy/core/vivy_brain.py` (4 tầng, tầng 3 hằng) |
| SVD tách luồng | `core/svd_streams.py` (numpy, LSB, ratio σ²) | `nps_core/.../svd_decomposer.py` (thuần Python, MSB, ratio σ) | `vivy_brain._level_2` (reshape vuông) |
| Bộ nhớ liên kết | `memory/associative.py` (`dim`, `eta`) | `vivy/core/associative_memory.py` (unitary mỗi lần lưu) | `nps_core/memory/associative_memory.py` (Python thuần) |
| Client LLM | `llm_bridge.LLMClient` (OpenAI-compatible) | `integration.LlamaCppBridge` | `vivy_ollama.OllamaViVyClient` (không mạng) · `OllamaAPIEngine` (`model_loader`) |
| Kiểu bằng chứng | `EvidenceClass` (graph_bridge) | `nps_core.EvidencePacket` | (`evidence_packet` của ViVy — chưa thấy) |
| Quyết định | `EpistemicDecision` (3) | `Decision` (6) | `FunnelSignal` (4), MTP opcode (3) |
| Ghi nhật ký | `ActivityLog` | `SessionLog` (Cautreo) | `LessonStore` |

---

## Lịch Sử Thay Đổi (Changelog)

| Agent | Thời gian | Hành động |
|:--|:--|:--|
| Claude (phiên review) | 29/09/2026 | Khởi tạo Review 3: 60+ phát hiện gắn nhãn bằng chứng, điểm mạnh, nguyên nhân gốc, phương án, kế hoạch test T0–T12, quyết định D-1…D-10. Trạng thái DRAFT. |

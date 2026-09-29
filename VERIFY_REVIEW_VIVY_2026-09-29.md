# BÁO CÁO XÁC MINH REVIEW_VIVY_2026-09-29.md

> [!IMPORTANT]
> **Quy tắc 3 điều bắt buộc** (changelog / chỉ cô lập không xóa bỏ / đồng bộ `D:\2brain`) vẫn áp dụng.
> Tài liệu này là **receipt xác minh** cho bản review DRAFT `REVIEW_VIVY_2026-09-29.md` — không phải review mới,
> không thay `docs/REVIEWS.md`. Không chỉnh sửa code trong lần xác minh này (chỉ đọc + chạy thử).

| Mục | Giá trị |
|:--|:--|
| Ngày | 29/09/2026 |
| Tác giả | Claude Code (phiên xác minh theo yêu cầu của chủ dự án) |
| Đối tượng | `REVIEW_VIVY_2026-09-29.md` (396 dòng, DRAFT 29/09/2026) |
| Phạm vi | 58 finding F-A01…I-05 + receipt `[LOG]` + attribution thay đổi working-tree |
| Trạng thái | **DONE** — 58/58 finding có verdict (xem §6) |

---

## 0. Phương pháp

| Bước | Cách làm | Receipt |
|:--|:--|:--|
| Health stack | Chạy full từ `Vivy_final/vivy/`: mypy / ruff / pytest `tests/` / pytest `training/` | §1 |
| Xác minh từng finding | 4 tuyến: (A) đọc mã + chạy; (B+C) subagent chạy repro; (D+E) subagent; (F+G+H+I) subagent chạy repro | §2 |
| Replay log | Đọc lại 4 bản `.vivy_activity.jsonl`, khớp bộ đếm với receipt `[LOG]` của review | §3 |
| Attribution | Dấu vết trong repo (`user chỉ thị`, `[REROUTED]`, `[FIXED]`) + `git diff HEAD` 29 file | §4 |
| Dán nhãn thành phần | Gộp kết quả §2 với danh sách cô lập §7.3 của review, kiểm lại từng mục | §5 |

Môi trường xác minh: **Windows 11**, Python tại `Vivy_final/vivy/`. Review gốc chạy trên **Linux sandbox** (tự khai §0) — các finding phụ thuộc đường dẫn Windows được ghi rõ.

---

## 1. Health stack — khẳng định của CLAUDE.md là **ĐÚNG**

Chạy từ `Vivy_final/vivy/` (29/09/2026):

| Hạng mục | Ngưỡng CLAUDE.md | Thực tế | Khớp? |
|:--|:--|:--|:--|
| `python -m mypy core/ engine/ memory/ orchestrator/ funnel/ llm_bridge/ integration/ --ignore-missing-imports` | `Success: no issues found` (64 source files) | `Success: no issues found` | ✅ |
| `python -m ruff check core/ engine/ memory/ orchestrator/ funnel/ llm_bridge/ integration/ tests/` | `All checks passed!` | `All checks passed!` | ✅ |
| `python -m pytest tests/ -q` | **695 passed + 0 skipped** | `695 passed in 30.53s` | ✅ |
| `python -m pytest training/ -q` | **730 passed + 3 skipped** | `730 passed, 3 skipped in 8.43s` | ✅ |

**Kết luận:** mọi con số baseline trong `CLAUDE.md` tái lập chính xác trên máy này. Baseline test xanh **không** mâu thuẫn với review — review không nói test sai, review nói test **yếu** (F-I02: khẳng định `conf > 0`, test VM-11 dựng sẵn, test khóa fallback 17 model). Hai nhận định này tương thích: test pass nhưng không bảo vệ hành vi đúng.

---

## 2. Bảng verdict từng finding

**Thang:** `CONFIRMED` = review đúng · `PARTIAL` = đúng phần lớn, có sai lệch con/chữ · `REFUTED` = review sai ở nội dung chính.

### Nhóm A — Orchestrator (9/9)

| ID | Verdict | Mức (review → xác minh) | Receipt |
|:--|:--|:--|:--|
| F-A01 | **CONFIRMED** | S1 = S1 | `core/evolution.py:174,198-199` — `schedule=None` → `GateSchedule()` rỗng, `_apply_one` không bao giờ gọi (:128-136) |
| F-A02 | **CONFIRMED** | S1 = S1 | `orchestrator/epistemic_gate.py:169-173` — `float(state.norm())` trên dict → `except: return 0.0`; `[LOG]` 120/120 `vivy-task-*` blocked (F-B01 cùng nguồn) |
| F-A03 | **PARTIAL** | S1 → **S2/S3** | **Headline REFUTED:** `core/knowledge_injector.py` **tồn tại** (git từ `96c89cb` 26/09), import sạch, `KnowledgeInjector` có `facts`/`inject`, 25 `DomainFact` strength 0.85–0.95. Chạy lại câu hỏi miền: `conf=0.95 signal=continue n_knowledge=1` — **tái lập được** giá trị 0.85–0.95/`continue` trong `experiment_results_1..4.json`. Phần CONFIRMED còn lại: mẫu `try/except ImportError → stub im lặng` ở đúng 4 chỗ (`engine.py:48,70,84,98`) — rủi ro tiềm ẩn có thật |
| F-A04 | **CONFIRMED** | S1 = S1 | Luồng giả `1/(i+1)` → `measure`/0.5/`"thought stream 0"` tái lập được |
| F-A05 | **CONFIRMED** | S2 = S2 | `llm_bridge/decoder.py:120-131` — prompt chỉ chứa propositions/relations/query/conclusion/confidence/signal, không có câu hỏi gốc |
| F-A06 | **CONFIRMED** | S2 = S2 | `self.memory`/`max_iterations` không dùng; backtrack/delegate chỉ log |
| F-A07 | **CONFIRMED** | S1 = S1 | `engine.py:370-377` `_evaluate` trả `("continue", 0.9)` mọi ngoại lệ; `__mro__[1]()` ở :146,154,162 (trái ADR-005) — factory trả class thật khi import thành công, fallback cho `object()` |
| F-A08 | **CONFIRMED** | S3 = S3 | `engine.py:277` `task_id = f"vivy-task-{id(question)}"` |
| F-A09 | **CONFIRMED** | S2 = S2 | `llm_bridge/client.py:110` timeout 60.0; `:196-197` chuỗi lỗi khớp |

**Ghi chú F-A03:** review ghi `D-5 "Tìm lại hay viết lại KnowledgeInjector?"` — **đã trả lời bằng xác minh này: nó nằm ngay trong cây, commit `96c89cb`. Không cần viết lại, không cần bỏ tham chiếu.**

### Nhóm B — VivyInferenceLoop (7/7)

| ID | Verdict | Mức | Receipt |
|:--|:--|:--|:--|
| F-B01 | **CONFIRMED** | S1 = S1 | `decision_controller.py:29-39` không nhánh HALT nào tới được; continue-set `vivy_inference_loop.py:649-652` luôn đúng. Runtime mock: `rounds=10 decision=DELEGATE evidence=FAST_SIGNAL`. Replay log: **15/15** `inference_end` đều `rounds:10, DELEGATE, FAST_SIGNAL` |
| F-B02 | **CONFIRMED** | S2 = S2 | `:601` `max_rounds = 1` cho CHAT/BATCH → `resolve()` chốt DELEGATE vòng 1. Runtime xác nhận |
| F-B03 | **CONFIRMED** | S2 = S2 | `:730-737` thiếu trường → `"EXECUTE_DIRECTLY"`; map-default DELEGATE là mã chết |
| F-B04 | **CONFIRMED** | S2 = S2 | `:569-577` hidden = `sha256(task_state.to_text())`; 2 nhãn giả thuyết cứng; `n_core.forward` ×2 cùng input (:572, :700); `mtp_directive.py:225-227` `payload_hash = sha256(...)` |
| F-B05 | **CONFIRMED** | S2 = S2 | `:708-714` cứng `independently_verified=False`, không `evidence_packet` → luôn `FAST_SIGNAL`; LessonStore chỉ nhận `VERIFIED_RESULT` ⇒ 0 bài học |
| F-B06 | **CONFIRMED** | S2 = S2 | `LLMClient` 8000/60s/`gpt-4o-mini`/17 model vs `LlamaCppConfig` 8080/180s/`gemma4-e4b`/32k; ADR-007 nói 11434; `run_vivy.py:177-184` nói "Ollama" khi mặc định 8080 |
| F-B07 | **CONFIRMED** | S2 = S2 | `activity_log.py:33-45` không thẻ môi trường; log trộn `t-*`/`test_session`/`vivy-task-*`; `qwen2.5-coder:7b` PASS từ mock |

### Nhóm C — Phễu lọc / tín hiệu / confidence (7/7)

| ID | Verdict | Mức | Receipt |
|:--|:--|:--|:--|
| F-C01 | **CONFIRMED** | S2 = S2 | `funnel/filter.py:166` brevity ceiling → `continue` bất khả khi n≥3, n≥5 luôn `backtrack`; `reject_threshold`/`_apply_conflict_penalty` chết (AST); `consistency` trộn đơn vị. **Chi tiết:** "delegate không thể" chỉ đúng với trạng thái vật lý chuẩn hóa — khớp cách review diễn đạt |
| F-C02 | **CONFIRMED** | S2 = S2 | 100 mẫu/n với SVD thật: n≥5 → 100% `backtrack`; `delegate` 0% mọi n; multi-stream 0.76→1.00 (n=2→6) |
| F-C03 | **PARTIAL** | S2 = S2 | CONFIRMED: `cos_sim < -0.5` bất khả (‖cos‖≤4.4e-16); 78% `DEQUIRE_EXTERNAL` random 4-qubit; MEASURE chỉ gần trạng thái cơ sở. **REFUTED con:** "Bell± chỉ khác dấu tổng thể" — sai, Bell± khác **pha tương đối π**; đổi dấu toàn cục thì bất biến (runtime xác nhận: `-ψ` cho cùng signal) |
| F-C04 | **CONFIRMED** | S1-if-used = S1 | `vivy_brain.py:107-109` mock 0.9/0.95; `model_loader.py:149-165` `np.random.randn(1024)` → `action = result["signal"]` (runtime: `DELEGATE_EXTERNAL` cho prompt trading) |
| F-C05 | **CONFIRMED** | S2 = S2 | 6 định nghĩa confidence đủ; ≥7 từ vựng quyết định đúng. **Sai lệch nhỏ:** opcode MTP là **16 opcode / 4 target**, không phải "(3)" |
| F-C06 | **CONFIRMED** | S3 = S3 | `core/` σ²/Σσ² + LSB vs `nps_core` σ/‖σ‖ + MSB; `schmidt_rank` 1e-10 trên σ²; reshape im lặng; entropy nats (`funnel/analysis.py`) vs bits |
| F-C07 | **PARTIAL** | S3 = S3 | CONFIRMED: `Modelfile.vivy-clairvoyance:16` SYSTEM nói "4-level filter funnel". **Overstated:** "1-touch Intuition Retrieval" chỉ ở docstring `vector_store.py:4`, **không** nằm trong prompt gửi LLM |

### Nhóm D — Bộ nhớ (5/5)

| ID | Verdict | Mức | Receipt |
|:--|:--|:--|:--|
| F-D01 | **PARTIAL** | S2 = S2 | CONFIRMED đúng từng chữ: `_materialise_dense` (`memory/associative.py:287-290`) bỏ η (runtime: `sparse W equals sum(outer) without eta: True`); **0.100 vs 1.000 tái lập chính xác** ở ngưỡng dim 256/257; mỗi query sparse dựng ma trận dim×dim (`:206`), `_make_unitary` SVD O(dim³) (`:274`). **Không tái lập được con số phụ:** "truy vấn ngẫu nhiên ~0.43" — đo lại ra 0.055 (dense η=0.1) / 0.275 (sparse dim 257) / 0.563 (η=1). Định tính vẫn đúng (random query vẫn ra confidence không tầm thường); 0.43 phụ thuộc tham số |
| F-D02 | **CONFIRMED** | S1 = S1 | `src/vivy/core/associative_memory.py:40-41` re-unitarise W sau **mỗi** `store`; conf=`‖Wx‖` (`:56`). Runtime: 5 store + 200 truy vấn không liên quan → `min=max=mean=1.000000`. Control `use_unitary=False`: 0.015–0.046. Bộ nhớ không thể nói "không biết" |
| F-D03 | **CONFIRMED** | S3 = S3 | Đủ 3 bản (`memory/associative.py:85`, `src/vivy/core/associative_memory.py:14`, `src/nps_core/memory/associative_memory.py:39`). `HebbianRecall` = `W = Y @ pinv(X)` (`memory/hebbian_recall.py:319-322`, docstring tự nhận Moore–Penrose) — không Hebbian |
| F-D04 | **CONFIRMED** | S2 = S2 | `moe_brain.py:29-34` seed toàn cục 42→None; router 70 centroid ngẫu nhiên; `train_expert` (`:92-108`) trên trạng thái + target ngẫu nhiên. Đĩa khớp: 70 file `expert_*.npz` ~4.10 MB; `vivy_core_memory.npy` = 16.777.344 B = chính xác ma trận 1024×1024 `complex128` + header 128 B. **Sub bị REFUTED:** review suy `state_dim=2048` — thực tế `expert_01.npz` U (4096,64), Vh (64,4096) ⇒ **4096**. Điều này **củng cố** luận điểm: 524.288 tham số phức/expert, xa "1B active" |
| F-D05 | **CONFIRMED** | S2 = S2 | `cognitive_graph.py:111` dampen 0.5ⁿ; LRU không loại INVARIANT (`:478-491`) — thiết kế tốt như review nói. VM-11 tautological: luôn ghép nút 0.4 với nút 0.8 (`tests/test_cognitive_graph.py:237-266`); cùng mẫu ở `test_graph_bridge.py:171-214`; thread-safety chỉ `assert not errors` |

### Nhóm E — `nps_core` (11/11)

| ID | Verdict | Mức | Receipt |
|:--|:--|:--|:--|
| F-E01 | **CONFIRMED** (tích cực) | — | JSON canonical deterministic + round-trip (`packet.py:482-523`); validation chặt (confidence 1.5 bị từ chối); phát hiện chu trình (`lineage.py:30-76`); SHA-256 digest |
| F-E02 | **CONFIRMED** | S2 = S2 | `calibration.py:26-28` `prior + 0.1(support−oppose)` kẹp [0,1] — không phải Bayes dù docstring nói vậy. Runtime: prior 0 + 10 support → 1.0. `calibrate()` **không bao giờ được gọi** (xem F-E09) |
| F-E03 | **CONFIRMED** | S2 = S2 | `tribunal.py:60` `reproduced = pkt.result.upper()=="PASSED"` — không chạy lại gì. Docstring "detects correlated errors" (dòng 3) không có mã. `snapshot` không dùng. `evaluate_with_filter_funnel` chạy funnel trên vector không liên quan (`:86`). Runtime: result `"OK"` → `reproduced=False` |
| F-E04 | **CONFIRMED** | S2 = S2 | `result` là chuỗi tự do (runtime chấp nhận `"banana"`). `ConflictDetector` (`conflict.py:67-68`) báo xung đột khi >1 giá trị → PASSED vs PASS = xung đột giả. **Tìm thấy kiểu `EvidencePacket` thứ hai** mà review để ngỏ: `integration/evidence.py:10-30` có `valid_for_promotion()`; bản nps_core thì không — `graph_bridge.py:439` gọi trên kiểu integration |
| F-E05 | **CONFIRMED** | S2 = S2 | `bundler.py:54-59` hardcode `all_pass`/`any_fail`, `automated_test`, `time_s:10.0`, EIG 0.85. `portfolio.py:173-178` ép `n_v == len(needs)` (runtime: 5 verifier / 2 needs → `VerifierBudgetError`); `n_v ≤ n_h` |
| F-E06 | **CONFIRMED** | S3 = S3 | `ranker.py:29` `ig = (1-conf)*risk*need` — tích 3 số được cung cấp sẵn. Runtime khớp |
| F-E07 | **CONFIRMED** | S3 = S3 | `controller.py:32` N chỉ tăng; `:33-37` ném `BudgetExceededError` thay vì kẹp (runtime: n_h=5, contradictions=40 → RAISE). `detect_duplicates` O(n²) khớp chuỗi |
| F-E08 | **CONFIRMED** | S3 = S3 | `index.py:695-700` cùng `assumption_id` khác payload → `ConflictingAssumptionError` chặn cả `build`. Runtime xác nhận |
| F-E09 | **CONFIRMED** | S1 = S1 | `apply_evidence` (`engine.py:334-342`) nhận thay thế từ caller, không tính gì. Grep sạch: không có bộ sinh giả thuyết / executor trong nps_core. `ConfidenceCalibrator.calibrate` được export nhưng **không nơi nào gọi**. Vòng lặp hở |
| F-E10 | **CONFIRMED** | S2 = S2 | **Nâng từ `[INFER]` lên tái lập được.** `incremental.py:38-40` `startswith(f"module:{module}")` xóa nhầm cạnh của module anh em (runtime: 3/4 cạnh của `module:core.state`, `module:core.core_utils`, `module:core_utils.helpers`); node module không được tạo lại (`:51-57` thiếu `module_node`); lệch path `str()` vs `as_posix()` tái hiện trên Windows (stale node / nhân đôi); lỗi cú pháp bị nuốt (`:48-49`) |
| F-E11 | **CONFIRMED** | S4 = S4 | `lineage.py:207-209` dựng lại set mỗi lần `contains`; `add` sắp xếp lại toàn bộ → O(N² log N); DFS đệ quy |

### Nhóm F — Mô phỏng & tuyên bố không receipt (7/7)

| ID | Verdict | Mức | Receipt |
|:--|:--|:--|:--|
| F-F01 | **CONFIRMED** | S1 = S1 | `vision.py:51` hash **đường dẫn** (file thiếu vẫn ra id); hardcode 1024×1024; `reasoning_engine.py:89,110` nói "đã nhận diện ảnh" không decode ảnh; `chat.py:53` timestamp cứng `"2026-07-25T10:42:00Z"` |
| F-F02 | **CONFIRMED** | S2 = S2 | `audio_video_perception.py:79,90` hash path + spectrogram `sin/cos` tổng quát; runtime entropy 3.86–4.0 ⇒ **luôn** `MEASURE_AND_HALT` |
| F-F03 | **CONFIRMED** | S2 = S2 | `vivy_ollama/server.py:120-122` `start_in_background` không `serve_forever`; metadata bịa (`llama3.2:3b`, digest `vivy1b...`); không có `/v1/chat/completions` (404 → fallback 17 model cloud); `exporter.py:66-68` ghi đè `./Modelfile` |
| F-F04 | **CONFIRMED** | S2 = S2 | `cautreo_cartographer.py:380` `model_path` không dùng; `:403-405` "Simulate streaming"; domain theo depth; `range(0, top_k)` |
| F-F05 | **CONFIRMED** | S3 = S3 | `cautreo_weight_map.py:89-101` lookup O(n) (docstring nói O(log n)); đăng ký `qwen2-70b` không có trên đĩa; `cautreo_session_log` dataclass không `frozen` — runtime mutate thành công; `score` default 0.5 |
| F-F06 | **CONFIRMED** | S3 = S3 | `cross_model_adapter.py:242-269` "soft blend" = cắt chuỗi; runtime: `'The quick brown fox j\nSECONDARY OUTPUT '` |
| F-F07 | **CONFIRMED** | S2 = S2 | Không receipt nào trong `evidence/` cho "99.2%", MMBench 84.5, "0 ms", "70B MoE/1B active", "Peak VRAM < 6.5 GB", VM-11 "0%"… |

### Nhóm G — Giao dịch (3/3)

| ID | Verdict | Mức | Receipt |
|:--|:--|:--|:--|
| G-01 | **CONFIRMED** | S1 = S1 | `prompts.py:13` nguyên văn "No hardcoded filters, velocity limits, or risk-reward caps exist in code"; parse là `float(...)` không kiểm ngưỡng (`inference.py:58-67`). **Sửa nhỏ của review:** `src/vivy/hands/mt5_executor.py` **có tồn tại** (câu "chưa thấy mã thực thi lệnh" đã cũ) — vẫn không có risk gate |
| G-02 | **CONFIRMED** | S1 = S1 | `model_loader.py:121-127` ImportError → `MockLocalEngine` im lặng; mock trả cứng `BUY/GOLD/0.1/SL 2350/TP 2390/conf 0.92`; backend lạ → Mock (:181-182) |
| G-03 | **CONFIRMED** | S1-if-on = S1 | random vector → funnel signal làm `action` (xem F-C04) |

### Nhóm H — Dữ liệu & huấn luyện (4/4)

| ID | Verdict | Mức | Receipt |
|:--|:--|:--|:--|
| F-H01 | **CONFIRMED** | S1 = S1 | `dataset_extractor.py:113,117` reward 1.0 cho mọi non-ERROR; `:121-125` hardcode `Expected_Evidence: AST_VALID_AND_TEST_PASS` bất kể thực tế. Runtime: phiên mock/DELEGATE/`expected_evidence=False` vẫn ra reward 1.0 + nhãn bịa |
| F-H02 | **CONFIRMED** | S3 = S3 | Notebook: 2 bootstrap × 3 epoch; "RLCD" chỉ có trong prose; `--outtype q8_0 --outfile ...q4km.gguf`; `trl>=0.8.0` |
| F-H03 | **CONFIRMED** | S2 = S2 | `confirm_gold.py:131-135` `reviewer=oracle_*` nhưng receipt `kind="human-accept"`; source không bị ghi đè (hạn chế đúng như review nói) |
| F-H04 | **CONFIRMED** | S3 = S3 | `dataset_audit`/`decision_contract` đòi `context_state`+`candidates`, `to_chatml` chỉ ra `messages` — lệch schema, không nối; `check_known_limits` entry không có receipt ref thì **im lặng pass** (runtime xác nhận) |

### Nhóm I — Hạ tầng / tài liệu / test (5/5)

| ID | Verdict | Mức | Receipt |
|:--|:--|:--|:--|
| F-I01 | **PARTIAL** | S3 = S3 | 8/9 sub-claim drift là thật (19/19 tests, 11 vs 17 cổng, 3.10 vs 3.11, setup.py vs pyproject, thiếu `pytest-asyncio`, ADR-005 `schedule`). **REFUTED sub:** ADR-003 nói `dominant_stream` default **0.0** — khớp `svd_streams.py:220` |
| F-I02 | **CONFIRMED** | S2 = S2 | `assert conf > 0.0` lặp lại; VM-11 dựng sẵn (nút 0.4 vs 0.8); test khóa `len(DEFAULT_MODELS)==17` + fallback `gpt-4o-mini`; test DLL env-bound; funnel test dùng fake SVD; `demo.py` `freed_pct>=60` khi thực tế 100% |
| F-I03 | **CONFIRMED** | S2 = S2 | `engine/cache_control.py` docstring tự nhận "Python dict KV store"; không gọi KV cache của LLM |
| F-I04 | **CONFIRMED** | S2 = S2 | Native chỉ test DLL; manifest 8.95 GB GGUF vs quickstart `ollama pull gemma4:e4b` ~9.6 GB; parity native FAIL trong REVIEWS.md:1230 |
| F-I05 | **CONFIRMED** | S4 = S4 | `open("a")` không lock/hash-chain; regex redaction miss JSON-quoted secret; HMAC tĩnh `b"vivy-final-v1-mtp-integrity-key"` |

### Tổng kết mức finding

| Nhóm | CONFIRMED | PARTIAL | REFUTED (nội dung chính) |
|:--|:--|:--|:--|
| A | 8 | 1 (F-A03) | 0 |
| B | 7 | 0 | 0 |
| C | 5 | 2 (F-C03, F-C07) | 0 |
| D | 4 | 1 (F-D01) | 0 |
| E | 11 | 0 | 0 |
| F | 7 | 0 | 0 |
| G | 3 | 0 | 0 |
| H | 4 | 0 | 0 |
| I | 4 | 1 (F-I01) | 0 |
| **Tổng (58)** | **53** | **5** | **0** |

**Không có finding nào bị REFUTED hoàn toàn.** 5 finding PARTIAL đều là chỗ review **đúng hướng nhưng quá lời** ở một tiểu-claim:

| Finding | Tiểu-claim sai | Thực tế |
|:--|:--|:--|
| F-A03 | "`core.knowledge_injector` không tồn tại; kết quả cũ không tái lập" | Module có thật (`96c89cb`), 25 fact, chạy lại ra `conf=0.95 continue` |
| F-C03 | "Bell± chỉ khác dấu tổng thể" | Khác **pha tương đối π**; đổi dấu toàn cục bất biến |
| F-C07 | "1-touch Intuition Retrieval" trong system prompt | Chỉ ở docstring, không gửi cho LLM |
| F-D01 | "truy vấn ngẫu nhiên ~0.43" | Đo lại 0.055 / 0.275 / 0.563 tùy tham số (phần còn lại khớp chính xác) |
| F-I01 | ADR-003 lệch code | `dominant_stream` default 0.0 khớp `svd_streams.py:220` |

**Mức độ nghiêm trọng khớp ở 100% finding** (sau khi hạ F-A03 S1→S2/S3). Nhóm S1 thật sự gây hại: F-A01/A02/A04/A07, F-B01, F-D02, F-E09, F-C04, F-F01, G-01/G-02, F-H01.

**Điểm review để ngỏ đã được xác minh:** F-E04 hỏi "có thể tồn tại kiểu `EvidencePacket` thứ hai (chưa thấy)" — **có**, tại `integration/evidence.py:10-30`. F-E10 `[INFER — chưa tái hiện]` — **đã tái hiện** trên Windows. F-A03/D-5 hỏi KnowledgeInjector ở đâu — **có trong cây**.

---

## 3. Receipt `[LOG]` của review — **KHỚP CHÍNH XÁC 100%**

Review (dòng 371) viết:
> 465 sự kiện (26/09 02:34 UTC → 27/09 11:22 UTC): `model_route_blocked` 165 (120 phiên `vivy-task-*`, 45 phiên `t-*`); `decision_assessment` 150; `model_attempt` 75 (FAIL 45, PASS 30); `model_route` 45; `inference_end` 15 (đều `DELEGATE`, `rounds: 10`, trung vị ~6 ms ⇒ mock), toàn bộ `evidence_class = FAST_SIGNAL`.

Đo lại trên `Vivy_final/vivy/.vivy_activity.jsonl` (bản hiện tại 525 sự kiện, file đã mọc thêm sau snapshot của review):

| Bộ đếm | Review | Đo lại (≤ 27/09 11:22:12 UTC) | Khớp |
|:--|:--|:--|:--|
| Tổng sự kiện | 465 | 465 | ✅ |
| Bắt đầu / kết thúc | 26/09 02:34 → 27/09 11:22 UTC | 02:34:48 → 11:22:12 | ✅ |
| `model_route_blocked` | 165 | 165 (120 `vivy-task-*` + 45 `t-*`) | ✅ |
| `decision_assessment` | 150 | 150 | ✅ |
| `model_attempt` | 75 (FAIL 45, PASS 30) | 75 (FAIL 45, PASS 30) | ✅ |
| `model_route` | 45 | 45 | ✅ |
| `inference_end` | 15, đều `DELEGATE`/`rounds:10`/FAST_SIGNAL | 15/15 đúng y | ✅ |
| Trung vị thời lượng | ~6 ms | 5.7 ms (3.6–12.2 ms) | ✅ |

**F-B01 được xác nhận trực tiếp từ log** — hành vi "đốt 10 vòng rồi luôn DELEGATE" không phải suy đoán. Việc review nói mock cũng đúng: inference_end dưới 13 ms không thể là LLM thật.

*(Ghi chú kỹ thuật: cutoff 27/09 11:22:00 chỉ đếm được 434 sự kiện vì 31 sự kiện cuối rơi vào 12 giây 11:22:00–11:22:12. Bộ đếm của review dùng đúng thời điểm sự kiện cuối.)*

---

## 4. Attribution — cái gì do user yêu cầu, cái gì do agent chủ động

Nguồn: dấu vết trong repo (`user chỉ thị`, `[REROUTED]`, `[FIXED]` + ngày) + `git diff HEAD` (29 file, +119/−69).

### 4.1 Do **người dùng yêu cầu** (có trích dẫn chỉ thị trong repo)

| Thay đổi | Ngày | Dấu vết | Phạm vi |
|:--|:--|:--|:--|
| Gỡ tham chiếu 3 gguf không tồn tại (`qwen2.5-coder-7b-instruct-q4_k_m`, `vivy2`, `qwen3.8-27b`) + **xóa** 2 runtime `start_vivy_qwen_coder.ps1` | 26/09 | `models/baselines/README.md:29,56` trích: *".gguf không còn dùng → xóa"*; `docs/ARCHITECTURE_FINAL.md:121`; `README.md:57` | manifest, baselines, scripts |
| Gom tài liệu về 5 doc chuẩn (chấm dứt v1/v2/v3) | 26/09 | `docs/ARCHITECTURE.md:87` "user yêu cầu gom tài liệu"; `ARCHITECTURE_FINAL.md:198,204` "theo yêu cầu *gom về 5 tài liệu*" | docs/ + old-docs/ |
| Thiết kế tầng tiêu chí game (đặc tả, không code) | 27/09 | `docs/DESIGN_GAME_CRITERIA_LAYER.md` — user gọi `/office-hours` | chỉ tài liệu |
| Review toàn hệ thống (đối tượng của lần xác minh này) | 29/09 | `REVIEW_VIVY_2026-09-29.md:12` "theo yêu cầu của chủ dự án" | tài liệu |

### 4.2 Do **agent chủ động** (không có chỉ thị user trong dấu vết)

| Thay đổi | Ngày | Dấu vết | Đánh giá |
|:--|:--|:--|:--|
| `[REROUTED]` 5 archetype → `gemma4-e4b`, CUA → `qwen2-vl-72b` | 26/09 | `ARCHITECTURE_FINAL.md:99,101`; `model_catalog.py`, `model_router.py`, `model_manifest.json`, `vivy_inference_loop.py`, RUNBOOK, `start_vivy_unified.ps1`, `verify_all.ps1`, 2 file test sửa assertion `== "gemma4-e4b"` | **Hợp lý nhưng là quyết định agent** — lý do ghi trong repo: model cũ "không có trọng số trên đĩa". Đổi test theo code = nguy cơ F-I02 "khóa hành vi" |
| `[FIXED 26/09]` đường dẫn `core/`→`vivy/`, `atlases`→`cautreo/atlases` | 26/09 | `cautreo_binding.py`, `model_catalog.py`… | Cần thiết sau reorg D2–D5 |
| `[FIXED 27/09]` readiness gate: bỏ key chết `results["qwen_coder_artifact_present"] = False` | 27/09 | `vivy/scripts/` + `scripts/verify_vivy_cautreo_readiness.py` + test mới `vivy/tests/test_readiness_gate.py` | **Sửa đúng** — gate FAIL vĩnh viễn là lỗi thật; có regression test |
| BOM-stripping (UTF-8 BOM) hàng loạt | 26–27/09 | diff 1 dòng `﻿"""` → `"""` ở nhiều file | Vô hại, cần cho mypy/ruff |
| Đồng bộ baseline test 693→695 trong CLAUDE.md | 27/09 | changelog CLAUDE.md | Khớp thực tế (§1) |

### 4.3 Đáng chú ý

1. **Không có thay đổi nào do agent mà user không biết** — mọi mục 4.2 đều có marker + ngày trong changelog/ARCHITECTURE_FINAL. Quy tắc 1 (changelog) được tuân thủ.
2. **Điểm agent tự quyết nên xem lại:** `[REROUTED]` sửa **cả test** để khớp code mới. Về kỹ thuật đúng (model cũ hết trọng số) nhưng về quy trình là "đổi oracle theo code" — đúng thứ review cảnh báo ở §9 ("Agent tự sửa để test qua thay vì sửa gốc").
3. **Không có file trọng số nào bị `git add`** — ràng buộc cứng giữ nguyên.

---

## 5. Nhãn thành phần — không đi đúng hướng / tạo kết quả giả định

Gộp kết quả xác minh (§2) với danh sách cô lập §7.3 của review. Mỗi dòng là **hành vi đã quan sát được**, không phải suy đoán.

### 5.1 Kết quả giả định / mô phỏng nhưng trình bày như thật — **nên cô lập ngay**

| Thành phần | Nhãn đề xuất | Bằng chứng hành vi | Điều kiện quay lại |
|:--|:--|:--|:--|
| `nps_core/vivy_interface/vision.py` + `reasoning_engine.py` | `[ISOLATED]` — **KẾT QUẢ GIẢ** | Hash **đường dẫn** file (kể cả file không tồn tại) ra "image id"; hardcode 1024×1024; trả "ViVy has processed the image" không hề decode ảnh | Backend thị giác thật (Qwen2-VL) + test 2 ảnh khác → output khác |
| `nps_core/multimodal_clairvoyance/*` | `[ISOLATED]` gắn `SIMULATED` | Spectrogram = `sin/cos` tổng quát từ index; frames = nhãn chuỗi `FRAME-xxx-hash`; entropy luôn 3.86–4.0 ⇒ signal **luôn** `MEASURE_AND_HALT` | Lời gọi model tri giác thật |
| `nps_core/vivy_ollama/*` | `[ISOLATED]` | Server không `serve_forever`; `/api/tags` bịa digest `vivy1b...`; không có `/v1/chat/completions`; exporter ghi đè `./Modelfile` | Proxy thật tới backend + test tương thích giao thức |
| `integration/cautreo_cartographer.py::scan_model` | Gắn `SIMULATED`; **cấm tiêm vào prompt** | `model_path` không đọc; "Simulate streaming 1 layer block FFN (120MB)"; domain theo depth; `range(0, top_k)` | Quét trọng số thật |
| `vivy/core/model_loader.py::MockLocalEngine` | **Cấm production** | ImportError `llama_cpp` → mock trả cứng lệnh `BUY GOLD` conf 0.92; backend lạ → mock | RiskGate + fail-closed |
| `vivy/core/model_loader.py::NativePyTorchEngine.generate` | `[ISOLATED]` | Vector ngẫu nhiên `np.random.randn(1024)` → `action = signal funnel` (runtime: `DEQUIRE_EXTERNAL` cho prompt trading) | Nhúng prompt thật + mapping action hợp lệ |
| `training/dataset_extractor.py` nhãn `Expected_Evidence: AST_VALID_AND_TEST_PASS` | **CẤP S1 — dừng SFT ngay** | Phiên mock/DELEGATE/`expected_evidence=False` vẫn ra reward 1.0 + nhãn "verified" bịa | Mọi mẫu bắt buộc mang `evidence_receipt_id` thật |
| `ViVyMoEQuantumCore` + 70 expert `.npz` | `[ISOLATED]`; đổi tên tuyên bố | Router = 70 centroid seed-42; `train_expert` trên target ngẫu nhiên ⇒ liên kết ngẫu nhiên. 524.288 tham số phức/expert (U 4096×64) — xa "1B active" | Bài đánh giá tri thức thật |
| `src/vivy/core/associative_memory.py` (`use_unitary=True`) | `[ISOLATED]` | conf ≡ **1.000000** cho mọi truy vấn chuẩn hóa (200/200) — bộ nhớ mù, không thể nói "không biết" | Confidence = độ tương tự đã hiệu chuẩn; không re-unitarise mỗi store |
| `memory/associative.py` sparse mode | Sửa hoặc `[ISOLATED]` | η bị bỏ trong `_materialise_dense` ⇒ conf 0.100 (dense) vs 1.000 (sparse) cùng dữ liệu; mỗi query dựng ma trận dim×dim | Nhân η đúng; so với kNN embedding |
| `src/nps_core/vivy_ollama/exporter.py` | `[ISOLATED]` | `root_path.write_text` ghi đè `./Modelfile` trong CWD | Không ghi đè ngoài thư mục đích |

### 5.2 Không đi đúng hướng (logic sai / kiến trúc hở) — sửa hoặc đóng băng

| Thành phần | Nhãn đề xuất | Bằng chứng |
|:--|:--|:--|
| `orchestrator/engine.py` stub im lặng ×4 | S1 — xóa stub hoặc fail-loud | `:48,70,84,98` ImportError→stub không cảnh báo (F-A03 phần còn lại) |
| `orchestrator/engine.py::_evaluate` | S1 | Mọi ngoại lệ → `("continue", 0.9)` = thất bại trình bày như thành công |
| `core/evolution.py::evolve(schedule=None)` | S1 | Lịch rỗng ⇒ không `_apply_one` — "evolve" là no-op |
| `orchestrator/epistemic_gate.py::_compute_confidence` | S1 | dict → `norm()` fail → 0.0 im lặng |
| `integration/vivy_inference_loop.py` AGENTIC loop | S1 | 10/10 vòng luôn cháy, không nhánh HALT tới được (F-B01) |
| `funnel/filter.py` + `nps_core/filter_funnel` | Đóng băng làm **nghiên cứu** (O-14) | Toán phễu khiến `continue` bất khả n≥3; n≥5 luôn `backtrack`; stream-b `cos_sim` bất khả; 78% DELEGATE random |
| `training/confirm_gold.py` auto-review | S2 | Oracle rule đóng dấu receipt `kind="human-accept"` |
| `training/check_known_limits.py` | S3 | Entry thiếu receipt ref → im lặng PASS |
| `nps_core/verification_tribunal` | S2 | `reproduced = (result=="PASSED")` — không chạy lại; docstring "detects correlated errors" không có mã |
| `nps_core/verification_tribunal/calibration.py` | S2 | `prior+0.1(support−oppose)` không phải Bayes; `calibrate()` chết — không nơi nào gọi |
| `nps_core/adaptive_n` (bundler/portfolio/ranker/controller) | S2–S3 | EIG/`all_pass`/`time_s=10` hardcode; `n_v=len(needs)`; N chỉ tăng, vượt budget thì ném lỗi |
| `nps_core/codegraph/incremental.py` | S2 | `startswith("module:X")` xóa nhầm cạnh module anh em + node module biến mất (đã tái hiện); lệch `str()` vs `as_posix()` trên Windows |
| `engine/cache_control.py` | S2 | "Rào cản #3" tự nhận là Python dict store, không chạm KV cache LLM |
| `src/vivy/core/prompts.py` trading prompt | **S1 an toàn** | Nguyên văn cấm risk limit trong code + `mt5_executor` float-cast không chặn |

### 5.3 Tuyên bố không receipt — giữ nguyên nhưng gắn dấu "chưa đo"

`99.2% Epistemic Rigor`, `MMBench 84.5 / DocVQA 94.2`, `Zero-OOM`, `0 ms`, `70B MoE / 1B active`, `Peak VRAM < 6.5 GB`, `VM-11 0%`, `HebbianRecall O(1)` (đã cô lập 23/09), `19/19 tests`, `11 cổng` — **không có receipt đo** trong `evidence/`. Nên chuyển vào khối `[ISOLATED]` hoặc gắn `UNMEASURED`, không dùng làm bằng chứng năng lực.

---

## 6. Trạng thái & việc còn

**DONE** (58/58 finding có verdict; không sửa code)

| Hạng mục | Trạng thái |
|:--|:--|
| Health stack 4/4 khớp baseline | ✅ |
| Verdict đủ 58 finding A→I | ✅ 53 CONFIRMED · 5 PARTIAL · 0 REFUTED |
| Receipt `[LOG]` khớp 100% | ✅ |
| Attribution user vs agent | ✅ |
| Nhãn thành phần giả/không đúng hướng | ✅ |
| Sửa code | ❌ **không sửa** — đúng yêu cầu "xác minh", không phải "fix" |

**Cảnh báo cần chủ dự án biết trước khi tin các finding `[RUN]` của review gốc:** review chạy trên **Linux sandbox** (tự khai §0); các con số phụ thuộc đường dẫn Windows chưa tái hiện ở đó. Ngược lại, các repro của lần xác minh này chạy **trên máy Windows thật** — nơi có `D:\models`, DLL Cautreo, file `.vivy_activity.jsonl` thật. Nơi hai bên trùng khớp thì độ tin cậy cao. Hai chỗ lệch giữa hai lượt (F-D01 "0.43", F-D04 state_dim 2048) đều là con số phụ, không đổi kết luận.

---

## 7. Lịch sử thay đổi

| Ngày | Thay đổi | Agent |
|:--|:--|:--|
| 29/09/2026 | Khởi tạo báo cáo xác minh `REVIEW_VIVY_2026-09-29.md`: health stack 4/4 khớp baseline; verdict **58/58** finding (53 CONFIRMED, 5 PARTIAL, 0 REFUTED); receipt `[LOG]` khớp 100% mọi bộ đếm; bảng attribution user vs agent (4 mục user-chỉ-thị / 5 mục agent-chủ-động); nhãn thành phần giả/không đúng hướng. Xác minh 3 điểm review để ngỏ (EvidencePacket thứ hai có thật; F-E10 tái hiện được; KnowledgeInjector có trong cây). **Không sửa code nào.** | Claude Code |

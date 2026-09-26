# BÁO CÁO KẾT QUẢ — P0→P5 / C01–C13

**Ngày:** 2026-09-24
**Người thực hiện:** Claude Code (thay Antigravity)
**Reviewer độc lập:** Codex/Vy (không lấy self-attestation của implementer làm ground truth)
**Phạm vi báo cáo:** harness / contract / mechanism của `ANTIGRAVITY_IMPLEMENTATION_AND_REVIEW_ACCEPTANCE_PLAN.md`
**Nhãn kết quả:** `PROPOSED_ACCEPTANCE_AT_HARNESS_LEVEL` / `TESTED_MECHANISM` / `PROVISIONAL_RESULT`
**Tài liệu ràng buộc kèm theo:** [`KNOWN_LIMITATIONS.md`](./KNOWN_LIMITATIONS.md) — **ưu tiên mọi tóm tắt**

Ghi chú bắt buộc (Changelog):
- 2026-09-24 (Claude Code — báo cáo kết quả): tổng hợp P0–P5 / C01–C13.
  Không claim `PRODUCTION-READY`, không `0%`, không `O(1)`, không latency SLA.
  Isolate-not-delete. Gold datasets không bị sửa.

---

## §0 Đọc đúng nghĩa các nhãn

| Nhãn | Nghĩa |
|---|---|
| **PASS (scoped)** | contract / harness / mechanism đã test — **không** phải chất lượng model |
| **NOT_RUN** | harness đã có hoặc đã specify, nhưng phép đo chưa chạy ở đây |
| **GAP** | contract yêu cầu một ngưỡng/bằng chứng chưa tồn tại (spec im lặng) |
| **FAIL (isolated)** | lỗi thật, đã cô lập để không âm thầm lan |
| **INCONCLUSIVE** | có chạy, nhưng mức evidence chưa đủ cho claim |

Mọi `PASS` đều bị chặn bởi mọi dòng trong `KNOWN_LIMITATIONS.md` liên quan.

**Cam kết trung thực (Gate 9):**

- Không `PRODUCTION-READY`
- Không `0%` (báo `n` + CI; 0 trên n mẫu không phải 0%)
- Không `O(1)`
- `LATENCY_CLAIM = "NOT_A_PHYSICAL_ZERO"`
- Không lấy simulation / test-count / checkpoint / receipt làm evidence chất lượng
- `production_ready = NOT_CLAIMED`
- `whole_goal_handoff = NOT_CLAIMED`

---

## §1 Kết luận một đoạn

Phần **harness, hợp đồng typed-decision, negative gates và cơ chế resilience của C01–C13 đã được implement và test** (339 test, scoped PASS) và sẵn sàng cho Codex/Vy review độc lập. **Mọi claim cần model live, service live, ảnh thật, OS RSS probe, pin upstream Laya/Verdict, gold do người xác nhận, hoặc ngưỡng số trong spec versioned đều là NOT_RUN hoặc GAP.** Native CAUTREO forward/logits parity **FAIL thật và đã cô lập** (không quy trách nhiệm cho llama-server `:8080`). Dampener naïve đẩy `repeat_rate` 0.39→0.00 nhưng kéo `false_inhibition` 0.00→1.00 — **không được ship**. Sparse activation không miễn phí (cosine 0.67 ở 12.5% activation). `gold_outcome` vẫn `unknown` trên cả 50 rows. Production swap / paid services / out-of-scope là **quyết định của user**.

---

## §2 Rollup theo pha

| Pha | Packet | Deliverable | Verdict |
|---|---|---|---|
| P0 | [`P0_INVENTORY_TRACEABILITY_CORRECTIONS.md`](./P0_INVENTORY_TRACEABILITY_CORRECTIONS.md) | inventory + 12 corrections §2 | **COMPLETE** (12/12 đóng hoặc ghi nhận NOT_RUN) |
| P1 | [`P1_BACKEND_BASELINE_GATE_NEGATIVE_TESTS.md`](./P1_BACKEND_BASELINE_GATE_NEGATIVE_TESTS.md) | backend registry + known-answer + gate hardening | **PASS (scoped)** harness · live accuracy **NOT_RUN** |
| P2 | [`P2_DATASET_CONTRACT_AND_PROVENANCE.md`](./P2_DATASET_CONTRACT_AND_PROVENANCE.md) | DecisionInput/Prediction/Label + provenance + observed outcomes + split | **PASS (scoped)** contract · `gold_outcome=unknown` |
| P3 | [`P3_INDEPENDENT_BASELINES_C05.md`](./P3_INDEPENDENT_BASELINES_C05.md) | baselines độc lập + smoke_train gated + Brier/ECE | **PASS (scoped)** harness · không claim quality gain |
| P4 | [`P4_SHADOW_TOKEN_THINKING_C07_C09.md`](./P4_SHADOW_TOKEN_THINKING_C07_C09.md) | shadow default-off + token ledger + thinking-budget A/B + memory A/B | **PASS (scoped)** harness · live A/B **NOT_RUN** |
| P5 | [`P5_C10_…`](./P5_C10_MEMORY_C_ABI_HEBBIAN.md) [`P5_C11_…`](./P5_C11_VM11_DREAM_PROMOTION.md) [`P5_C12_…`](./P5_C12_CARTOGRAPHY_PHASES_SPARSE.md) [`P5_C13_…`](./P5_C13_VMEM_RESILIENCE.md) | VMEM + Dream + Cartography + soak/resilience | **PASS (scoped)** mechanism · live VM **NOT_RUN** · thresholds **GAP** |
| P5 FINAL | [`P5_FINAL_ACCEPTANCE.md`](./P5_FINAL_ACCEPTANCE.md) + [`KNOWN_LIMITATIONS.md`](./KNOWN_LIMITATIONS.md) | proposed acceptance | **PROPOSED** — chờ Codex/Vy |

---

## §3 Rollup theo requirement (C01–C13)

| ID | Scope | Verdict | Evidence |
|---|---|---|---|
| C01 | Backend registry, known-answer, gate negatives, unitary client | **PASS** (harness) | P1 + `test_backend_*` / `test_gate_negative` |
| C01 live | Accuracy known-answer trên backend tham chiếu | **NOT_RUN** | `INFRA_INCOMPLETE` (`:8080` down), accuracy `null` |
| C02 | DecisionInput / Prediction / Label; promote fail-closed | **PASS** | P2 + `test_decision_contract` / `test_promote_reviewed` |
| C03 | Multiline Expected_Evidence, group split, provenance v2 | **PASS** | P2 + `test_dataset_c03` + `evidence/c03_*` |
| C04 | Observed-outcome capture store | **PASS** (contract) | P2 + `test_outcome_capture` |
| C05 | Independent baselines + Brier/ECE | **PASS** (harness) | P3 + `test_independent_baselines` |
| C06 | smoke_train gated bởi preflight | **PASS** | P3 + `test_smoke_train` |
| C07 | Shadow default-off + `no_tool_call_proof` | **PASS** | P4 + `test_shadow_integration` |
| C08 | Token ledger real-vs-approximate | **PASS** (contract) | P4 + `test_token_ledger` |
| C09 | Thinking-budget A/B (0 / 384 / 1024) | **PASS** (harness) / **NOT_RUN** (live) | P4 + `test_thinking_budget` |
| C10 | Session memory, C-ABI layout/ownership, Hebbian, retrieval A/B | **PASS** (harness) | [`P5_C10_…`](./P5_C10_MEMORY_C_ABI_HEBBIAN.md) + `evidence/c10_memory_c_abi_hebbian.json` |
| C11 | Error taxonomy, Dream gate, lesson persistence, 2brain sync, pilot 100 task | **PASS** (harness) | [`P5_C11_…`](./P5_C11_VM11_DREAM_PROMOTION.md) + `evidence/c11_vm11_dream_promotion.json` |
| C11.7 | Live repeat-rate + CI | **NOT_RUN** | không có model live |
| C12 | Five-phase Cartography, RSS-vs-buffer, sparse forward, guard 100B/vision | **PASS** (mechanism) | [`P5_C12_…`](./P5_C12_CARTOGRAPHY_PHASES_SPARSE.md) + `evidence/c12_cartography_phases_sparse.json` |
| C12.2b | OS RSS / page-faults probe | **NOT_RUN** | psapi unavailable → `os_probe=NOT_RUN` |
| C12.6 | Real-model inference evidence | **NOT_RUN** | không có forward model thật |
| C13.1 | Threshold-quote gate + VM-01…VM-11 shape contracts | **PASS** (gate) / **GAP** (thresholds) | [`P5_C13_…`](./P5_C13_VMEM_RESILIENCE.md) + `evidence/c13_vmem_resilience.json` |
| C13.2–6 | Soak ≥100 + timeout/restart/concurrency + receipts + fallback + idempotent recovery | **PASS** | [`P5_C13_…`](./P5_C13_VMEM_RESILIENCE.md) |
| C13.7 | VM-01…VM-11 live effectiveness | **NOT_RUN** | không có model/service live |
| §2.12 | Pin schema Laya/Verdict | **NOT_RUN** | không có upstream revision trên đĩa |
| Native parity | CAUTREO prompt/tokenizer vs forward/logits | **FAIL** (isolated) | `VIVY-CAUTREO-GEMMA4-CHAT-171/188`, `REFERENCE-TOKEN-194`, `EXACT-PROMPT-196` |

**Counts (từ `evidence/p5_final_acceptance.json`):** `PASS=13` · `NOT_RUN=8` · `GAP=1` (bucket VM thresholds) · `FAIL=1` (native parity, isolated).
Riêng bảng ngưỡng VM-01…VM-11: **11/11 GAP** (spec im lặng — không bịa bar).

---

## §4 Gate 1–10 (`ACCEPTANCE_GATES.md`)

| Gate | Status | Ghi chú |
|---|---|---|
| 1 Native residency | **UNVERIFIED / isolated** | native CAUTREO forward-logits parity FAIL; llama-server là backend khác, **không** swap vào `:8080` |
| 2 Boundary correctness | **PASS** (contract) | typed split + promote fail-closed |
| 3 Multimodal | **NOT_RUN** | vision cần image bytes + reference label; text mô tả ảnh **không** tính là grounding |
| 4 Direct execution | **PASS** (guard) | `EXECUTE_DIRECTLY` bị chặn tới khi Evidence Gate PASS |
| 5 State durability | **PASS** (harness) | lesson restart + soak receipts intact |
| 6 Delegation verification | **PARTIAL** | protocol worker identity đã define; live delegate **NOT_RUN** |
| 7 Learning safety | **PASS** (harness) | Dream gate reject incomplete / FAST_SIGNAL / PROVISIONAL / poisoned / duplicate / stale / contradictory |
| 8 Recovery & resilience | **PASS** (harness) | soak timeout/restart/unavailable; `side_effect_repeats=0` |
| 9 Truthful status | **PASS** | không claim `PRODUCTION-READY` / `0%` / `O(1)` / latency; `LATENCY_CLAIM=NOT_A_PHYSICAL_ZERO` |
| 10 Accuracy & maturation | **NOT_RUN** (live) | Brier/ECE chỉ trên fixture; live accuracy/calibration **NOT_RUN** |

Kịch bản Gate 10 (incomplete input, stream disagreement, shared false premise, contradictory evidence, timeout/refusal, CAUTREO tool unavailable, restart mid-reasoning, promote unverified lesson): **đã cover ở harness negatives**; live scenario battery **NOT_RUN**.

---

## §5 Bars đề xuất ("Ngưỡng nghiệm thu v1") vs đo được

| Bar | Yêu cầu | Đo được | Status |
|---|---|---|---|
| Negative contract/authority bị chặn | 100% | 100% trên negative suite (harness) | **MET (tested scope)** |
| Critical facts / units / paths / postconditions | 100% trên safety regression set | chỉ harness level | **INCONCLUSIVE** cho live safety set |
| Decision quality paired, lower 95% CI Δaccuracy > 0 | bắt buộc cho quality claim | không có paired run live | **NOT_RUN** |
| Accuracy giữ được ở token cost thấp hơn, paired CI ≥ 0 | bắt buộc cho "no regression" | không có paired run live | **NOT_RUN** |
| Token giảm ≥ 20% / task hoàn thành | target | không có corpus token live | **NOT_RUN** |
| Risk giảm khi coverage giảm (OOD/abstain) | bắt buộc | always-abstain bị loại; curve live **NOT_RUN** | **NOT_RUN** |
| VM numeric thresholds trích từ spec | verbatim + version | 3 specs im lặng → 11/11 **GAP** | **GAP** |
| Soak ≥ 100 với timeout/restart/concurrency | bắt buộc | n=100, faults 3/5/7, concurrency=4 | **MET (tested scope)** |
| Không infinite token loop / không mất receipt | bắt buộc | `infinite_loops_detected=0`, `receipts_lost=0` | **MET (tested scope)** |
| Fallback khi unavailable + recovery không lặp side effect | bắt buộc | `fallback_taken=1`, `side_effect_repeats=0` | **MET (tested scope)** |

**Kết quả:** các bar **numeric quality/efficiency** của §4 **không đạt và không được claim**.
Các bar **safety/contract/resilience** chỉ đạt **trong phạm vi harness đã test**.

---

## §6 Findings load-bearing (mang theo mọi bản sau)

1. **Native CAUTREO forward/logits parity FAIL là thật và đã cô lập.** Prompt/tokenizer parity 24/24 ID, nhưng first token `177869/gug` vs reference `26391/Four` cho `2+2=4`. **Không** cáo buộc llama-server `:8080`. **Không** swap default model của `:8080` để "fix" việc này.
2. **Dampener naïve condition-blind không được ship.** `repeat_rate` 0.39→0.00 nhưng `false_inhibition` 0.00→1.00 (20/20). Condition-aware gating là điều kiện tiên quyết cho mọi claim VM-11 live.
3. **VM-01…VM-11 numeric thresholds 11/11 GAP.** `VIVY_COGNITIVE_CORE_SPEC.md`, `ACCURACY_AND_MATURATION_STRATEGIES.md`, `ACCEPTANCE_GATES.md` không có bảng ngưỡng. **Không bịa bar** để biến GAP thành PASS.
4. **Simulation ≠ production.** Pilot 100-task của C11 là `SIMULATED_PROTOCOL` và **FAIL** gate VM-11 live.
5. **Sparse không miễn phí.** 12.5% activation (k=8/n=64) làm cosine output **0.67** trên cùng weights/input (`ram_savings_inferred_from_buffer=false`).
6. **`gold_outcome = unknown` trên cả 50 rows.** Chỉ có selection labels. Tối đa `PROVISIONAL_RESULT`, **không bao giờ** `VERIFIED_RESULT`.
7. **Buffer ≠ RSS.** Không suy RSS từ `allocated_buffer_bytes`. OS probe `NOT_RUN`.
8. **`LLMClient.chat(..., fallback=True)` là `[ISOLATED]`** — lặng lẽ đi 17 `DEFAULT_MODELS`. Dùng `fallback=False` hoặc `make_unitary_fn`.

---

## §7 Bằng chứng & packet index

| Artifact | Vai trò |
|---|---|
| [`P0_INVENTORY_TRACEABILITY_CORRECTIONS.md`](./P0_INVENTORY_TRACEABILITY_CORRECTIONS.md) | inventory + 12 corrections |
| [`P1_BACKEND_BASELINE_GATE_NEGATIVE_TESTS.md`](./P1_BACKEND_BASELINE_GATE_NEGATIVE_TESTS.md) | C01 |
| [`P2_DATASET_CONTRACT_AND_PROVENANCE.md`](./P2_DATASET_CONTRACT_AND_PROVENANCE.md) | C02–C04 |
| [`P3_INDEPENDENT_BASELINES_C05.md`](./P3_INDEPENDENT_BASELINES_C05.md) | C05–C06 |
| [`P4_SHADOW_TOKEN_THINKING_C07_C09.md`](./P4_SHADOW_TOKEN_THINKING_C07_C09.md) | C07–C09 |
| [`P5_C10_MEMORY_C_ABI_HEBBIAN.md`](./P5_C10_MEMORY_C_ABI_HEBBIAN.md) | C10 |
| [`P5_C11_VM11_DREAM_PROMOTION.md`](./P5_C11_VM11_DREAM_PROMOTION.md) | C11 |
| [`P5_C12_CARTOGRAPHY_PHASES_SPARSE.md`](./P5_C12_CARTOGRAPHY_PHASES_SPARSE.md) | C12 |
| [`P5_C13_VMEM_RESILIENCE.md`](./P5_C13_VMEM_RESILIENCE.md) | C13 |
| [`P5_FINAL_ACCEPTANCE.md`](./P5_FINAL_ACCEPTANCE.md) | rollup + reviewer checklist |
| [`KNOWN_LIMITATIONS.md`](./KNOWN_LIMITATIONS.md) | **register L-01…L-55 — ràng buộc** |
| `evidence/p5_final_acceptance.json` | rollup receipt |
| `evidence/c10_memory_c_abi_hebbian.json` | C10 receipt |
| `evidence/c11_vm11_dream_promotion.json` | C11 receipt |
| `evidence/c12_cartography_phases_sparse.json` | C12 receipt |
| `evidence/c13_vmem_resilience.json` | C13 receipt |
| `evidence/c03_dataset_audit.json`, `evidence/c03_split_manifest.json` | C03 receipt |
| `training/run_final_acceptance.py` | script rollup (io_guard, không ghi đè) |

### Immutables (không bị work này sửa)

| File | sha256 |
|---|---|
| `vivy_train_dataset.jsonl` | `8d1e68421572708324248ff8a06326e77449c292d2214498759f231a82b4531b` |
| `evidence/gold_train.jsonl` | `630a2ee442f20d942be210d219ca40eca4e2905cb83247c2d1e0d1e589ec44c7` |
| `evidence/gold_review_queue.jsonl` | `93cdcf3675facc0bf7dbaf2baef5f35cff1c5c47c0c13968ac176d97f8ca2ef7` |
| `evidence/shadow_receipts.jsonl` | `695a224b16b82baeeeac499cb3e50fb74ceb2036e439ee8d92fbed51efbd0576` |

Không xóa dataset / receipt / checkpoint. Hardening theo **isolate-not-delete** (`[ISOLATED / DEPRECATED / REPLACED]`).

---

## §8 Kết quả test

```
Full suite (training/preflight.py test_modules, 39 modules):
  Ran 339 tests — OK
```

- Con số test **không** phải evidence chất lượng (Gate 9). Nó chỉ chứng minh contract/negative gates còn xanh.
- Reviewer phải tự chạy lại — xem §5 của [`P5_FINAL_ACCEPTANCE.md`](./P5_FINAL_ACCEPTANCE.md).

Lệnh chạy (từ `vivyChatGPT/`, Python `C:\Users\LENOVO\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`):

```powershell
# full suite qua preflight test_modules
& $py -m training.preflight

# C runner (ghi receipt mới; io_guard từ chối ghi đè)
& $py -m training.run_c13_resilience
& $py -m training.run_final_acceptance
```

---

## §9 Cái này KHÔNG mở khóa

- Không `PRODUCTION-READY`, không `0%`, không `O(1)`, không latency SLA.
- Không claim decision-quality / token-saving / risk-coverage (§4 bars NOT_RUN).
- Không claim VM effectiveness (thresholds GAP + live NOT_RUN).
- Không claim action-success (`gold_outcome=unknown`).
- Không claim learned-router quality (fixture/replay không được đóng goal này).
- Không "RLCD complete" cho notebook chỉ dùng `SFTTrainer`.
- Không SFT/LoRA full trên 501 legacy rows.
- Không đổi default model của `:8080`.
- Không `EXECUTE_DIRECTLY` trước Evidence Gate PASS.
- Không tự điền gold / không đưa `unverified` vào `gold_train` / không lấy LLM critique làm ground truth.
- Production swap / paid services / out-of-scope = **user quyết định**.

---

## §10 Việc còn mở (ưu tiên theo leverage)

| # | Việc | Mở khóa |
|---|---|---|
| 1 | Start llama-server `:8080` (giữ default model) → chạy lại `python -m training.run_known_answer --backend llama-server` | C01 live, Gate 10 |
| 2 | Live C09 thinking-budget A/B + C10 `cautreo.dll` memory path | token/quality tradeoff, C10 native |
| 3 | Pin upstream Laya/Verdict revision → đóng §2.12 | schema-compatibility |
| 4 | Fix hoặc formally retire native CAUTREO forward/logits parity (L-40) | Gate 1 native residency |
| 5 | Publish VM-01…VM-11 numeric thresholds có version vào spec | đóng 11/11 GAP |
| 6 | Real-image + reference-label vision set | Gate 3 |
| 7 | OS RSS probe trên host đo | C12.2 |
| 8 | Human-confirmed gold (`gold_outcome` đang `unknown`) | mọi Gate 10 / decision-quality claim |
| 9 | Codex/Vy review packets + re-run negatives + recompute metrics | accepted hoặc rejected |
| 10 | Push / PR hosted — cần git remote + `gh` | delivery qua PR |

---

## §11 Delivery / git state tại thời điểm báo cáo

| Hạng mục | Trạng thái |
|---|---|
| Branch làm việc | `feat/gold-triage-oracle` |
| Local branch `main` | được tạo trong lần delivery này (target của PR) |
| Git remote | **chưa có** (`git remote -v` rỗng) |
| `gh` CLI | **chưa cài** (`gh: command not found`) |
| PR hosted | **BLOCKED** — xem `docs/plans/PR_TO_MAIN.md` |
| Gold datasets | không sửa (đã re-hash) |
| Default model `:8080` | không đổi |
| SFT/LoRA trên 501 rows | không chạy |

Standing order cũ **"Chưa commit ngay"** được user thay bằng **"Tạo PR và main. tạo file báo cáo kết quả"** — commit phạm vi phase work được phép trong lần này; **không** commit `.venv/`, log, probe binary, hoặc gold datasets ngoài phạm vi immutables đã pin.

---

## §12 Changelog

| Date | Actor | Change |
|---|---|---|
| 2026-09-24 | Claude Code | Initial results report (P0–P5 / C01–C13). Scoped PASS tại harness; production NOT claimed. |

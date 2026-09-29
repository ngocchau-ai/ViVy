# SỔ NĂNG LỰC — Capability Ledger

> **[NEW 29/09/2026 · WP-5 / O-12 / Gate 9]**
> Quy tắc: **mọi tuyên bố năng lực phải có receipt (lời gọi model thật / phép đo thật) hoặc bị gắn `UNMEASURED`.**
> Không có trạng thái thứ ba. Không có "ước lượng", "theo lý thuyết", "như thiết kế".

**Trạng thái:** ACTIVE
**Người ban hành:** Chủ dự án (qua plan `delegated-riding-blossom.md`, WP-5)
**Ghi nhận bởi:** Claude Code
**Nguồn:** `REVIEW_VIVY_2026-09-29.md` · `VERIFY_REVIEW_VIVY_2026-09-29.md` · plan GĐ1

---

## 0. Cách dùng sổ này

| Trạng thái | Nghĩa |
|:--|:--|
| `RECEIPT` | Có bằng chứng đo được, ghi `receipt:` trỏ tới file/commit thật |
| `UNMEASURED` | Tuyên bố đang sống trong code/doc nhưng **chưa từng đo** |
| `ISOLATED` | Đã cô lập khỏi đường sống; không còn claim trên luồng sản phẩm |
| `REPLACED` | Claim cũ đã bị thay bằng con số thật (vẫn lưu trong `[ISOLATED]`) |
| `SIMULATED` | Kết quả do công thức sinh ra, **không** đọc dữ liệu thật |

**Cách đóng một mục `UNMEASURED`:** chạy phép đo (thường là WP-7 harness), ghi receipt path vào cột `Receipt`, đổi trạng thái. Không được tự ghi `RECEIPT` mà không có file.

**Nơi enforce:** `vivy/tests/test_capability_honesty.py` — quét các nguồn claim sống, fail khi thấy chuỗi tuyên bố đã biết mà không có tag.

---

## 1. Khối đã sửa trong WP-5 (F-F01…F-F07, F-C07)

| # | Tuyên bố cũ | Trạng thái | Nơi sống | Việc đã làm |
|:--|:--|:--|:--|:--|
| C-01 | Ảnh có độ phân giải **1024×1024** (mọi đường dẫn, kể cả file không tồn tại) | `REPLACED` | `src/nps_core/vivy_interface/vision.py` | `width`/`height` = `None` (không decode). File thiếu → `FileNotFoundError`, hoặc `allow_simulated=True` + `simulated=True` |
| C-02 | `content_hash` = hash **đường dẫn** trình bày như hash ảnh | `REPLACED` | `vision.py` | Hash **byte** khi file thật; nhánh hash đường dẫn bị `[ISOLATED]` + cờ `simulated` |
| C-03 | *"ViVy has processed the image"* / *"nhận diện được hình ảnh"* | `REPLACED` | `vivy_interface/reasoning_engine.py` | Trả về metadata receipt, nói rõ pixel **không** được giải mã. Chuỗi cũ lưu `[ISOLATED]` |
| C-04 | *"equipped with Vision capability"* / *"có khả năng phân tích thị giác"* | `REPLACED` | `reasoning_engine.py` | Bỏ khỏi live text. Thêm cờ `from_template` / `model_call_made=False` / `pixels_decoded=False` |
| C-05 | *"Fusing visual features with ViVy multimodal knowledge base"* | `REPLACED` | `reasoning_engine.py` | Không có feature nào được trích xuất. Chain-of-Thought giờ nói đúng việc đã làm |
| C-06 | Audio: `sample_rate=16000`, `channels=1`, `duration=5.0` | `REPLACED` | `multimodal_clairvoyance/audio_video_perception.py` | `None` = không đo. Hash byte thay vì đường dẫn |
| C-07 | Video: `1920×1080`, `fps=30`, `frame_count=24` | `REPLACED` | `audio_video_perception.py` | `None` = không đo. `frames_read=False`; `temporal_frames` là **nhãn**, không phải frame |
| C-08 | Spectrogram matrix = tín hiệu âm thanh | `SIMULATED` | `audio_video_perception.py` | `sin(f)*cos(t)` theo loop index. Gắn `spectrogram_is_synthetic=True` |
| C-09 | `[ViVy Clairvoyance Direct Perception]` + modalities `VISION_2D_3D` / `VIDEO_4D_TEMPORAL` / `AUDIO_SPECTROGRAM` | `SIMULATED` | `multimodal_clairvoyance/clairvoyance_engine.py` | Summary đổi thành *"`SIMULATED` · synthetic state, NO media was decoded"*. Trả `simulated=True`, `pixels_read=False`, `audio_samples_read=False`, `video_frames_read=False` |
| C-10 | Ollama client "communicating with ViVy via Ollama API" | `ISOLATED` | `vivy_ollama/client.py` | **Không có lời gọi HTTP nào.** Dict trả về gắn `model_call_made: False`, `simulated_response: True` |
| C-11 | Ollama `/api/tags` card: `size 2147483648`, `digest sha256:vivy1b…`, `parameter_size "1.15B"` | `ISOLATED` | `vivy_ollama/server.py` | `None` / `UNMEASURED`. Card cũ lưu `[ISOLATED]` |
| C-12 | SYSTEM prompt: *"4-Level Self-Verification Filter Funnel"*, *"1-Touch Intuition Retrieval"* | `REPLACED` | `vivy_ollama/exporter.py` | Bỏ khỏi chuỗi prompt sống (prompt là chỉ thị hành vi — không được để lời nói dối). Lưu `[ISOLATED]` |
| C-13 | Modelfile: *"Native Visual/Video/Audio Perception"*, *"zero-hallucination"* | `REPLACED` | `modelfiles/Modelfile.vivy-clairvoyance` | SYSTEM giờ liệt kê **đúng** việc build làm được + danh sách "NOT measured". Khối cũ ở cuối file |
| C-14 | **"ViVy 70B MoE Quantum Core (1B Active)"** — 70 expert × 1B tham số | `REPLACED` | `src/vivy/core/moe_brain.py` | Thật: `524.288` tham số phức/expert (U 4096×64). `num_experts=70` = kích thước bảng route, không phải 70 model lớn. Tên class giữ (hard rule #3) |
| C-15 | Cartographer "Scan a 30B–100B model layer by layer" | `SIMULATED` | `integration/cautreo_cartographer.py::scan_model` | `model_path` bị bỏ qua hoàn toàn. `atlas.simulated=True`, `weights_read=False`. **`render_for_prompt()` raise** — cấm tiêm vào prompt |

---

## 2. Hạt giống `UNMEASURED` — tuyên bố đang sống, chưa có receipt

Đây là danh sách Gate 9 phải triệt. Mỗi dòng là một con số đang được nói như thể đã đo.

### 2.1 Hiệu năng model (trong `models/model_manifest.json`)

| # | Tuyên bố | Nơi | Trạng thái | Receipt | Đóng bằng |
|:--|:--|:--|:--|:--|:--|
| U-01 | `Epistemic Rigor 99.2%` | `model_manifest.json` gemma4-e4b | `UNMEASURED` | — | Bộ câu hỏi epistemic + chấm điểm lập trình (WP-7) |
| U-02 | `CPU Speed ~14 tok/s @ Port 8080` | `model_manifest.json` gemma4-e4b | `UNMEASURED` | — | Đo throughput thật trên máy chủ dự án |
| U-03 | `MMBench 84.5` | `model_manifest.json` qwen2-vl-72b | `UNMEASURED` | — | Chạy benchmark MMBench công bố + ghi run |
| U-04 | `DocVQA 94.2` | `model_manifest.json` qwen2-vl-72b | `UNMEASURED` | — | Như trên |
| U-05 | `72B Top-K Salience via Cautreo Cartography` | `model_manifest.json` qwen2-vl-72b | `SIMULATED` | — | Cartographer không đọc trọng số (C-15). Cần scan thật |
| U-06 | `HumanEval 88.4` | `model_manifest.json` qwen2.5-coder-7b | `UNMEASURED` | — | Chạy HumanEval + ghi run |
| U-07 | `CPU Speed ~8-12 tok/s` | `model_manifest.json` qwen2.5-coder-7b | `UNMEASURED` | — | Đo thật |
| U-08 | `Target CPU Speed >45 tok/s` | `model_manifest.json` vivy-1.5b-reflex | `UNMEASURED` | — | Model **chưa tồn tại** (`ROADMAP_PROPOSED`) — không được nói như có |
| U-09 | `Proper Scoring Calibrated` | `model_manifest.json` vivy-1.5b-reflex | `UNMEASURED` | — | Cần calibration curve (WP-9) |
| U-10 | `Phản xạ <300ms` | `model_manifest.json` vivy-1.5b-reflex `strengths` | `UNMEASURED` | — | Đo latency thật; model chưa có |

### 2.2 Kiến trúc / hệ thống

| # | Tuyên bố | Nơi | Trạng thái | Receipt | Đóng bằng |
|:--|:--|:--|:--|:--|:--|
| U-11 | **`70B MoE / 1B active`** | `moe_brain.py` (đã sửa) + tài liệu cũ | `REPLACED` | — | Con số thật 524.288 complex params/expert đã ghi |
| U-12 | `Zero-OOM` | tài liệu vận hành | `UNMEASURED` | — | Stress test bộ nhớ + log |
| U-13 | `0 ms` (độ trễ) | tài liệu vận hành | `UNMEASURED` | — | Không có phép đo nào cho 0 ms — hoặc đo, hoặc bỏ |
| U-14 | `Peak VRAM < 6.5 GB` | tài liệu vận hành | `UNMEASURED` | — | Đo `nvidia-smi`/`torch.cuda.max_memory_allocated` khi chạy |
| U-15 | `VM-11 0%` (tỷ lệ lặp lỗi) | `TECHNICAL_DIRECTION` / logs | `UNMEASURED` | — | Chạy VM-11 suite, đếm lỗi lặp lại |
| U-16 | `HebbianRecall O(1)` | `run_vivy.py:49` (đã cô lập 23/09) | `ISOLATED` | — | Phức tạp thực tế là O(d) trên vector; cần sửa nốt claim còn sống ở `run_vivy.py` (WP-15) |
| U-17 | Độ phức tạp HebbianRecall | `memory/associative.py` | `UNMEASURED` | — | Benchmark độ phức tạp thật |
| U-18 | Độ trễ native-memory (Cautreo) | `engine/` | `UNMEASURED` | — | Benchmark C-ABI thật |
| U-19 | `12–14 tok/s` | docs vận hành | `UNMEASURED` | — | Đo throughput |
| U-20 | `30–60s CPU / 5–8s GPU` mỗi vòng | docs vận hành | `UNMEASURED` | — | Đo wall-clock mỗi vòng |
| U-21 | `19/19 tests` | docs cũ | `REPLACED` | `tests/` 847 + `training/` 730+3 | Số test thật đã ghi ở CLAUDE.md |
| U-22 | `4-pillar 618/618 tests` | docs cũ | `REPLACED` | `tests/` 847 + `training/` 730+3 | Số test thật; 618 là con số lỗi thời |
| U-23 | `11 cổng` (ports) | docs cũ | `UNMEASURED` | — | Liệt kê cổng thật đang mở + verify script |
| U-24 | `4-level filter funnel` là cơ chế tự kiểm chứng | `exporter.py`, `Modelfile.vivy-clairvoyance` | `REPLACED` | — | Đã gỡ khỏi prompt sống. Muốn claim lại cần đo T6 |
| U-25 | `zero-hallucination` | `Modelfile.vivy-clairvoyance` | `REPLACED` | — | **Không thể chứng minh.** Không được tái lập dưới mọi hình thức |

---

## 3. Khối CÓ receipt (đóng rồi)

| # | Trạng thái | Tuyên bố | Receipt | Ngày |
|:--|:--|:--|:--|:--|
| R-01 | `RECEIPT` | RiskGate chặn **0/65** hình dạng lệnh đối kháng lọt (T10, ngưỡng ≥60) | `vivy/tests/test_risk_gate.py` — 104 test, ma trận `ADVERSARIAL` 65 case | 29/09/2026 |
| R-02 | `RECEIPT` | RiskGate mặc định **paper trading**; live cần `RiskLimits(paper_trading=False)` tường minh | `vivy/src/vivy/hands/risk_gate.py` + `docs/adr/ADR-008-risk-gate.md` | 29/09/2026 |
| R-03 | `RECEIPT` | Không còn fallback 17 model cloud | `vivy/llm_bridge/backend.py`, `tests/test_backend.py`, ADR-007 | 29/09/2026 |
| R-04 | `RECEIPT` | Không còn stub `ImportError` im lặng trong `orchestrator/engine.py` | `orchestrator/wiring_report.py`, `tests/test_wiring_failfast.py` | 29/09/2026 |
| R-05 | `RECEIPT` | `MockLocalEngine` bị cấm ở production | `tests/unit/test_vivy_core.py::test_mock_engine_banned_without_opt_in` | 29/09/2026 |
| R-06 | `RECEIPT` | Baseline test hiện tại | `pytest tests/` **847 passed** · `pytest training/` **730 passed + 3 skipped** · mypy `66 source files` · ruff sạch | 29/09/2026 |
| R-07 | `RECEIPT` | Gate 9 enforcement sống: claim cũ quay lại là fail | `vivy/tests/test_capability_honesty.py` | 29/09/2026 |

---

## 4. Quy tắc cho agent kế thừa

1. **Không thêm claim mới** vào prompt, README, doc, log hay manifest mà không thêm một dòng vào sổ này.
2. **Prompt là chỉ thị hành vi.** Claim sai trong prompt phải bị **gỡ khỏi chuỗi sống** (không chỉ comment), vì model đọc và hành vi theo nó. Bản cũ lưu trong `[ISOLATED]`.
3. **`SIMULATED` ≠ `RECEIPT`.** Kết quả do công thức sinh ra không bao giờ được trình bày như phép đo.
4. **Không tự ghi `RECEIPT`.** Phải có file receipt thật (thường `evidence/T2-<run_id>.json` từ WP-7).
5. **Con số `0` cũng là một claim.** `0 ms`, `0% lỗi`, `zero-hallucination` đều phải đo hoặc gỡ.
6. Test enforce nằm ở `vivy/tests/test_capability_honesty.py`. Nếu test đó fail, nghĩa là một claim cũ đã quay lại — **đừng sửa test**, sửa code.

---

## 5. Changelog

| Agent | Ngày | Hành động |
|:--|:--|:--|
| Claude Code | 29/09/2026 | Khởi tạo sổ. Ghi 15 mục WP-5 (C-01…C-15), 25 mục `UNMEASURED`/`REPLACED` (U-01…U-25), 6 mục đã có receipt (R-01…R-06). Nguồn hạt giống: `VERIFY_REVIEW_VIVY_2026-09-29.md` + plan WP-5. |

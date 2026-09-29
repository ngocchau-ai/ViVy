# DESIGN — Tầng tiêu chí Thẩm mỹ · Logic game · Góc nhìn người chơi

> **Trạng thái:** Đặc tả thiết kế. Chưa triển khai.
> **Phạm vi tài liệu này:** CHỈ thiết kế. Không code, không scaffolding, không cam kết thời gian triển khai.
> **Nguồn:** phiên `/office-hours` 27/09/2026. Quyết định D11, D12, D14.
> **Liên quan:** `docs/ARCHITECTURE_FINAL.md` (kiến trúc có hiệu lực) · `docs/TECHNICAL_DIRECTION.md` (định hướng NPS-core).

---

## 0. Vấn đề

Ba chỗ gãy của các lần thử trước đã thành ba ràng buộc thiết kế:

| Chỗ gãy | Ràng buộc |
|---|---|
| Chỉnh từng thành phần game cho khớp tổng thể mất 6–12 giờ | Lõi phải hiểu **toàn bộ** rồi tự chỉnh phần cho khớp |
| Giao hoàn toàn cho LLM thì rất lộn xộn | LLM **không** đứng trong vòng ghép |
| Đọc cả kho data mượn bằng API thì quá đắt | Phí đọc trả **một lần** lúc ingest, sau đó offline |

Nhưng ba ràng buộc đó chỉ dựng được **máy**. Máy chấm điểm, ghi chú, trạng thái — đúng như mô tả kiến trúc Vivy. Cái máy đó **chấm bằng gì** là câu hỏi chưa có trả lời, và thiếu nó thì:

> *"đưa ra hàng loạt lựa chọn"* chỉ là **máy sinh ngẫu nhiên có gu**.

Tài liệu này định nghĩa **nội dung** của máy chấm điểm đó: ba trục tiêu chí — **thẩm mỹ**, **logic game**, **góc nhìn người chơi** — và đường đi để biến điểm chấm mềm của một model lớn thành tiêu chí cứng mà lõi quyết định tất định dùng được.

**Đây là câu trả lời cho câu hỏi gốc:** *cái gì làm lựa chọn này tốt hơn lựa chọn kia?* — xem §9.

---

## 1. Ràng buộc cứng

Áp cho mọi phần của thiết kế. Không có ngoại lệ.

1. **LLM không đứng trong vòng ghép.** Chỉ hai việc: ghi chú lúc ingest, hiểu yêu cầu tiếng người.
2. **Phí đọc data trả một lần lúc ingest.** Sau đó tra cứu rẻ và offline được.
3. **Ăn cắp schema, không train model.** Mượn hình dạng dữ liệu, không mượn trọng số, không huấn luyện.
4. **Lõi quyết định tất định** mới là người chọn và ghép. Mọi kết quả có receipt.
5. **Kết quả chấm được** bằng thẩm mỹ + logic game + góc nhìn người chơi — cụ thể tới mức viết được thành hàm.
6. **Cô lập, không xóa bỏ.** Nội dung kiến trúc cũ đánh dấu `[ISOLATED / DEPRECATED / REPLACED]`, không xóa.

---

## 2. Kiến trúc ba tầng

```
TẦNG 1 — INGEST   (online, trả tiền MỘT LẦN)
   data mượn ──► LLM đọc ──► ghi chú + chấm 3 trục ──► annotation record
                                                              │
                                                              ▼
TẦNG 2 — DISTILL  (offline, tất định, KHÔNG LLM)
   annotation records ──► chưng cất ──► criterion set (weights/constraints/thresholds)
                                                              │
                                                              ▼
TẦNG 3 — COMPOSE  (offline, tất định, KHÔNG LLM)
   yêu cầu tiếng người ──► lõi quyết định xếp hạng ứng viên bằng criterion set
                        ──► giao diện game hoàn chỉnh + receipt
```

### 2.1 Tầng 1 — INGEST

Trả lời *"thẩm mỹ thì cần học rất nhiều"*: một model lớn **đã học sẵn** thẩm mỹ sẽ đọc và chấm mỗi mảnh data **đúng một lần** khi tải kho về local.

- **Vào:** data item mượn (ảnh, sprite, map, bản ghi entity, đoạn kịch bản) kèm metadata nguồn và license.
- **Ra:** `annotation record` (§5.1) — bất biến, append-only.
- **Model:** model lớn bất kỳ có khả năng nhìn và diễn đạt. Không phải model của dự án. Không train.
- **Chi phí:** dừng ở đây. Không có lời gọi LLM nào ở tầng 2 hay tầng 3.

Khi nhận yêu cầu tiếng người, LLM làm việc thứ hai: **hiểu yêu cầu** — chuyển câu tiếng người thành tiêu chí tìm kiếm có trọng số. Việc này là một lần gọi ngắn trên một câu, không phải đọc cả kho data.

### 2.2 Tầng 2 — DISTILL

Trả lời *"ăn cắp schema, đừng train model"*: điểm chấm mềm được **chưng cất** thành tiêu chí cứng.

- **Vào:** toàn bộ `annotation record`.
- **Ra:** `criterion set` (§5.2) — có version, có digest.
- **Cơ chế:** gom `features` (không phải `score`) thành constraint / threshold / weight.
- **Không** có gradient, không fine-tune, không cập nhật trọng số. "Trực giác" của hệ thống chính là lớp này.

### 2.3 Tầng 3 — COMPOSE

Trả lời *"giao hết cho LLM thì rất lộn xộn"*: vòng ghép **không có LLM**.

- **Vào:** yêu cầu tiếng người (đã thành tiêu chí tìm kiếm) + criterion set + kho data đã ghi chú.
- **Ra:** giao diện game hoàn chỉnh + `receipt` (§8).
- **Cơ chế:** sinh ứng viên → chấm bằng criterion set → xếp hạng → chọn → trả receipt.

### 2.4 Hợp đồng dữ liệu giữa các tầng

| Từ | Đến | Dữ liệu | Tính chất |
|---|---|---|---|
| Tầng 1 | Tầng 2 | `annotation record[]` | Append-only, bất biến |
| Tầng 2 | Tầng 3 | `criterion set` | Versioned, có digest |
| Tầng 3 | Bên ngoài | `composition + receipt` | Truy được về annotation gốc |

Không có đường nào đi ngược lại. Feedback người chơi đi vào tầng 2 (§6), không đi vào tầng 3.

---

## 3. Ba trục tiêu chí

Đây là **nội dung** của máy chấm điểm. Mỗi trục có tiêu chí con, mỗi tiêu chí con viết được thành hàm chấm.

### 3.1 Trục A — Thẩm mỹ

| Tiêu chí | Chấm cái gì | Kiểu | Dữ liệu vào |
|---|---|---|---|
| `style_family_match` | Các mảnh có cùng một họ thị giác không | constraint | `style_tag` từ annotation |
| `palette_harmony` | Quan hệ màu: tương phản / tương đồng / tam giác trong ngưỡng | threshold | `palette[]` từ annotation |
| `scale_ratio_coherence` | Kích thước các phần liên hệ bằng tỉ lệ nhất quán | threshold | `bbox`, `anchor` |
| `silhouette_distinctiveness` | Nhìn ở camera game, phân biệt được các phần không | threshold | `silhouette_hash` |
| `visual_hierarchy` | Có tiêu điểm, phần phụ lùi lại | constraint | `saliency_map` |
| `density_rhythm` | Tỉ lệ khoảng thở / dày đặc trên toàn bố cục | threshold | `coverage_ratio` |
| `detail_level_uniformity` | Độ dày nét, mức noise, độ phân giải render nhất quán | threshold | `line_weight`, `noise_level` |

### 3.2 Trục B — Logic game

| Tiêu chí | Chấm cái gì | Kiểu | Dữ liệu vào |
|---|---|---|---|
| `timing_window_coherence` | Cửa hitbox khớp với frame animation | constraint | `hitbox_frames[]`, `anim_frames[]` |
| `root_motion_continuity` | Không trượt chân, không dịch chuyển tức thời giữa chuỗi động tác | constraint | `root_motion[]` |
| `cancel_frame_safety` | Cửa cancel không phá bất biến i-frame | constraint | `cancel_windows[]`, `iframes[]` |
| `hitbox_hurtbox_disjoint` | Thể tích đánh / thể tích trúng khớp với fantasy của đòn | constraint | `hitbox`, `hurtbox` |
| `state_machine_reachability` | Mọi hành động hiển thị đều đạt được từ trạng thái hợp lệ | constraint | `fsm` mượn từ schema |
| `rule_constraint_satisfaction` | Không vi phạm luật của chính data mượn | constraint | `copy-from` inheritance |
| `resource_economy` | Giá item / năng lực nhất quán với kinh tế của bộ data | threshold | `cost`, `economy_table` |

### 3.3 Trục C — Góc nhìn người chơi

Trục này là thứ các hãng lớn đang cố nhét vào hệ thống phát triển game. Ở đây nó là **một trục chấm điểm**, không phải một model riêng.

| Tiêu chí | Chấm cái gì | Kiểu | Dữ liệu vào |
|---|---|---|---|
| `first_saccade_target` | Thứ người chơi thấy trước có phải thứ quan trọng nhất không | constraint | `saliency_map`, `importance` |
| `affordance_legibility` | Phần tương tác có nhìn ra là tương tác không | threshold | `interactive_flag` |
| `error_visibility` | Người chơi thất bại thì có nhìn ra tại sao không | constraint | `feedback_channels` |
| `cognitive_load` | Số phần tử có ý nghĩa đồng thời dưới ngưỡng | threshold | `element_count`, `salience[]` |
| `feedback_latency_expectation` | Phản hồi thị giác đến trong cửa thời gian mà hành động ngụ ý | constraint | `feedback_delay`, `action_duration` |
| `fantasy_readability` | Hành động định nghĩa đọc ra đúng là hành động đó | threshold | `action_label`, `pose_keypoints` |

---

## 4. Đường đi mềm → cứng

Đây là điểm mấu chốt của cả thiết kế. Nếu tầng này hỏng, kết quả vẫn là máy sinh ngẫu nhiên có gu.

### 4.1 Nguyên tắc

> **`score` là ý kiến của model tại một thời điểm. `features` là quan sát kiểm chứng lại được.**

Nên: **giữ `features`, dùng `features` để sinh tiêu chí.** `score` chỉ là tín hiệu ban đầu để biết đâu là chỗ đáng chú ý.

### 4.2 Các bước

```
[1] Model trả về {axis, score, rationale, features} cho mỗi data item
         │
         ▼
[2] LƯU annotation record bất biến (score + features + rationale + provenance)
         │
         ▼
[3] GOM features cùng loại trên nhiều item  →  pattern
         │
         ▼
[4] BIẾN pattern thành criterion record
         • threshold  : "trên 90% item tốt có ciede2000 ≤ 12"
         • constraint : "không item nào tốt có hitbox vượt anim frame cuối"
         • weight     : "trục này phân hạng đúng X/Y cặp đã biết"
         │
         ▼
[5] KIỂM CHỨNG criterion trên tập item đã biết → confidence
         │
         ▼
[6] criterion set vN có digest, đưa sang tầng 3
```

**Bước 4 là nơi dễ hỏng nhất.** Nếu biến pattern thành ngưỡng số vô hồn thì mất hết tinh thần. Tiêu chí **phải giữ được `features` kiểm chứng được** — mỗi criterion record trỏ về `provenance`, tức danh sách annotation gốc đã sinh ra nó.

### 4.3 Cập nhật khi có phản hồi người chơi

Phản hồi người chơi không đi vào tầng 3. Nó đi vào tầng 2:

```
phản hồi người chơi ──► điều chỉnh weight / confidence của criterion
                    ──► KHÔNG sửa annotation record gốc (bất biến)
                    ──► sinh criterion set vN+1 có digest mới
```

---

## 5. Schema bản ghi

### 5.1 `annotation record` — sinh ở tầng 1

```json
{
  "item_id": "uuid",
  "source": {
    "repo": "owner/name",
    "path": "path/in/repo",
    "license": "CC-BY-SA-4.0",
    "schema_only": true,
    "sha256": "..."
  },
  "item_kind": "sprite | tileset | map | entity | script | effect | animation",
  "axes": {
    "aesthetic":  { "score": 0.0, "features": { }, "rationale": "" },
    "game_logic": { "score": 0.0, "features": { }, "rationale": "" },
    "player_view":{ "score": 0.0, "features": { }, "rationale": "" }
  },
  "model": {
    "id": "tên model mượn",
    "prompt_hash": "sha256",
    "temperature": 0,
    "ts": "ISO-8601"
  }
}
```

Trong đó `features` của từng trục chứa **có thể kiểm chứng được**, ví dụ:

```json
"features": {
  "palette": ["#1a1a2e", "#16213e", "#0f3460", "#e94560"],
  "style_tag": "pixel-art-16x16-dark-fantasy",
  "bbox": [0, 0, 16, 16],
  "anchor": [8, 15],
  "line_weight": 1,
  "noise_level": 0.02,
  "hitbox_frames": [[4, 8], [9, 12]],
  "anim_frames": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
  "iframes": [[0, 3]],
  "cancel_windows": [[10, 14]],
  "action_label": "sword_swing_horizontal"
}
```

### 5.2 `criterion record` — sinh ở tầng 2

```json
{
  "criterion_id": "palette_harmony",
  "axis": "aesthetic",
  "kind": "threshold | constraint | weight",
  "expr": "ciede2000(p_i, p_j) <= 12.0",
  "weight": 0.18,
  "provenance": ["annotation:uuid-1", "annotation:uuid-2", "..."],
  "confidence": 0.0,
  "verified_on": { "n_items": 0, "n_agree": 0 },
  "falsified_by": [],
  "version": 1
}
```

### 5.3 `criterion set` — hợp đồng tầng 2 → tầng 3

```json
{
  "set_id": "criteria-v3",
  "digest": "sha256",
  "criteria": [ "criterion record, ..." ],
  "axis_weights": { "aesthetic": 0.34, "game_logic": 0.33, "player_view": 0.33 },
  "derived_from": ["annotation:...", "..."],
  "feedback_adjustments": [ { "criterion_id": "...", "delta": 0.0, "reason": "" } ]
}
```

---

## 6. Nguồn dữ liệu và tích lũy

| Nguồn | Đi vào đâu | Ghi chú |
|---|---|---|
| Data mượn (schema) | Kho local + annotation | Chỉ mượn **hình dạng**, không mượn asset |
| LLM lúc ingest | `annotation record` | Trả tiền một lần |
| Metadata sẵn của data mượn | `features` của trục Logic game | Hitbox, timing, FSM — không cần LLM suy ra nếu đã có |
| Phản hồi người chơi | Điều chỉnh `weight` / `confidence` ở tầng 2 | Không sửa annotation gốc |
| Yêu cầu tiếng người | Tiêu chí tìm kiếm có trọng số, vào tầng 3 | LLM làm việc thứ hai, một lần gọi ngắn |

**Offline:** sau khi ingest xong, toàn bộ tầng 2 và tầng 3 chạy local, không mạng.

---

## 7. Cắm vào code hiện có

Không viết lại máy. Đây là bảng những gì sẽ đổi khi triển khai sau này.

| Thành phần | Vị trí | Đổi gì |
|---|---|---|
| `CautreoScoreType(IntEnum)` — 8 loại | `vivy/integration/cautreo_binding.py:49` | Thêm `AESTHETIC_COHERENCE`, `GAME_LOGIC_FIT`, `PLAYER_VIEW` |
| `CautreoMemoryKind(IntEnum)` — 4 loại | `vivy/integration/cautreo_binding.py:40` | Thêm `ANNOTATION`, `PLAYER_VIEW` |
| `CautreoScoreGraph` | `vivy/integration/cautreo_binding.py:415` | Nhận 3 loại điểm mới; fallback dict đã có sẵn |
| `NodeScoreMetrics.compute_composite()` | `vivy/memory/cognitive_graph.py:520` | **Đổi chính:** mean 3 trục → weighted N tiêu chí theo `criterion set` |
| `ScoredTaskNode` | `vivy/memory/cognitive_graph.py:566` | Gắn `criterion_receipt` + giữ `negative_constraints` |
| `ScoredMindmapDAG` | `vivy/memory/cognitive_graph.py:636` | Vòng chọn/phân hạng ứng viên — `score_and_verify`, `pivot_alternative` |
| `SessionMemory` / `SessionMemoryHub` | `vivy/training/session_memory.py:39` | Kho tích lũy ghi chú ("trực giác") |
| `CautreoContextMemory.build_intuition_digest()` | `vivy/integration/cautreo_binding.py` | Nén ghi chú thành digest offline |
| `LLMClient.chat` | `vivy/llm_bridge/client.py:76` | Gọi model lúc ingest (tầng 1) |
| `Encoder` / `LogicForm` | `vivy/llm_bridge/encoder.py:29` | **Cần biến thể** cho yêu cầu game — `LogicForm` hiện dành cho câu đố logic (`propositions`/`relations`/`query`) |
| `PluginRegistry` / `ActivateApi.register_method` | `host/cautreo_host/registry.py:118` | Tiêu chí mới vào dạng plugin, không hardcode vào enum |

**Chưa có trong code** (phải đẻ ra khi triển khai, không có trong tài liệu này):

- Schema data game: map / item / phong cảnh / nhân vật. Xem §7.1.
- Bước ingest có ghi chú. `ingest_*` ở `vivy/training/dataset_extractor.py:142` là trace huấn luyện, không phải data game.
- Toàn bộ ba trục tiêu chí: rà `aesthetic` / `style` / `palette` / `layout` / `visual` / `taste` / `hitbox` / `iframe` / `cancel_frame` / `root_motion` / `damage` / `combat` / `game_logic` / `game_rule` trên `vivy/`, `host/`, `ui/`, `engine/` cho **0 điểm cài đặt**. Duy nhất một dòng comment ở `host/tests/test_ui_smoke.py:347` nhắc "palette" — không phải khái niệm có trong code.

### 7.1 Schema data game mượn từ đâu

**Nguyên tắc: ăn cắp schema, không train model, không mượn asset.**

| Nguồn | Mượn cái gì | License | Cảnh báo |
|---|---|---|---|
| Cataclysm-DDA | `copy-from` inheritance — entity ghép từ bản ghi + override | CC-BY-SA / GPL | **Copyleft.** Mượn **schema**, không mượn asset hay bản ghi |
| Universal LPC Spritesheet Character Generator | nhân vật = JSON phần rời + palette | GPL (code) | **Copyleft.** Tương tự — chỉ mượn hình dạng dữ liệu |
| Tiled | TMX/JSON map — chuẩn map đã được nhận diện rộng | BSD-2-Clause | An toàn hơn |
| flecs | typed components + JSON reflection | MIT | An toàn |
| OpenUSD | composition operators: references / payloads / variants / opinions | Apache-2.0 | An toàn; semantics mạnh cho ghép |
| Yarn Spinner | `.yarn` → cấu trúc hội thoại | MIT | An toàn |
| ink | `.ink` → JSON | MIT | An toàn |
| MTGJSON | schema có tài liệu hóa tốt | CC-BY-SA-4.0 | **Brand IP** (Magic) — chỉ xem cách viết schema, không dùng data |
| PokeAPI | — | — | **Brand IP.** Không dùng. |
| HearthSim/hsdata | — | — | **Không có license.** Chỉ tham khảo. |

---

## 8. Receipt

Mọi kết quả ghép phải truy được về nguồn.

```
receipt
├── composition_id
├── criterion_set_id + digest
├── per-criterion score + weight
├── item_ids đã chọn
├── provenance chain:  composition → criterion → annotation → source (repo/path/sha256/license)
└── reasoning: vì sao ứng viên này thắng ứng viên kế
```

Hai mục đích:

1. **Kiểm toán** — biết chính xác vì sao một mảnh được chọn, và nó đến từ đâu.
2. **Sửa sai** — khi kết quả xấu, truy ngược được về tiêu chí nào sai, annotation nào đã sinh ra nó, và model nào đã chấm.

Không có receipt thì không phân biệt được "lõi quyết định tất định" với "máy sinh ngẫu nhiên có gu".

---

## 9. Câu hỏi gốc đã được trả lời

> **Cái gì làm lựa chọn này tốt hơn lựa chọn kia?**

Ứng viên X xếp trên ứng viên Y khi và chỉ khi:

1. X đạt điểm cao hơn trên **weighted criterion set** (thẩm mỹ · logic game · góc nhìn người chơi), và
2. Mọi trọng số trong criterion set **truy được** về `features` quan sát được lúc ingest, và
3. Kết quả kèm **receipt** đầy đủ.

Không phải gu của người thiết kế. Không phải hộp đen. Không phải LLM quyết.

Đó là thứ mà Mixamo, asset store, và AI sinh ảnh **không bán được**: ghép **hình cộng timing** (hitbox, root motion, i-frame, cancel frame) thành một hợp đồng data duy nhất, chấm được, truy được.

---

## 10. Ngoại lệ phạm vi

Tài liệu này **KHÔNG** chứa:

- Code, scaffolding, module, class, hàm.
- Cam kết thời gian triển khai hay ước lượng công việc.
- Trọng số model, cách fine-tune, hay bất kỳ bước huấn luyện nào.
- Asset game, ảnh, sprite, map — chỉ có schema và hợp đồng dữ liệu.
- Quyết định về giao diện WebUI hay cách giao việc cho Vivy (đó là phạm vi khác của phiên).

---

## 11. Rủi ro

| Rủi ro | Mức | Cách giảm |
|---|---|---|
| **Tầng 2 biến điểm chấm mềm thành ngưỡng số vô hồn** — khi đó vẫn là máy sinh ngẫu nhiên có gu | **Cao** | Mọi `criterion record` bắt buộc có `provenance` + `verified_on`. Không có `features` kiểm chứng được thì không thành criterion |
| Model mượn lúc ingest chấm dở | Trung bình | `confidence` per criterion + `verified_on` cho biết criterion nào yếu. Có thể re-ingest riêng item đó với model khác |
| Gap chưa có bằng chứng: có ai ngoài người dùng cũng đau đúng 6–12 giờ này không | Trung bình | Wedge là công cụ cá nhân trước, cửa mở cho mở rộng. Người thứ hai cùng đau → quay lại Startup mode |
| Copyleft rò rỉ từ CDDA/LPC | Trung bình | Chỉ mượn **schema**, không mượn asset hay bản ghi. Ghi rõ trong bảng §7.1 |
| Các hãng lớn ship model game dev có góc nhìn người chơi | Cao | **Vị thế phòng thủ:** lõi quyết định tất định + data đã ghi chú sẵn + chạy trên máy của bạn + có receipt. Không phải "một LLM cho game dev" |

---

## 12. Bằng chứng nhu cầu (ghi lại để đối chiếu sau)

| Số liệu | Nguồn |
|---|---|
| LLM sinh code logic game: **3 phút** | Người dùng, tự đo |
| Dựng hoàn chỉnh giao diện game tĩnh HTML có hiệu ứng nhẹ: **6–12 giờ** | Người dùng, tự đo |
| Jev ghép cảnh quan tĩnh hoàn toàn từ data thô theo kịch bản: **1 giây** | Thí nghiệm thật |
| Khoảng cách | **120–240×** |
| Agent hiện tại trong game lớn | Chỉ thay được **vài bước lặp lại**; phần khó là thẩm mỹ |
| Ba chỗ gãy lần thử trước | Chỉnh từng thành phần tốn giờ · giao LLM thì lộn xộn · đọc kho data bằng API quá đắt |

---

## 13. Quyết định đã chốt

| # | Câu hỏi | Chọn |
|---|---|---|
| D11 | "Lộn xộn" nghĩa là gì | Cả ba lỗi + thiếu tiêu chí chọn |
| D12 | Bộ 6 tiền đề | Đồng ý cả 6 |
| D14 | Cơ chế học cho thẩm mỹ | Model lớn chấm một lần lúc ingest, tích lũy thành tiêu chí tất định |

**6 tiền đề (D12):**

1. Bài toán đúng là **chi phí ghép**, không phải chi phí sinh.
2. **LLM nằm ngoài vòng ghép** — chỉ ghi chú lúc ingest và hiểu yêu cầu tiếng người.
3. **Phí đọc data trả một lần** lúc ingest, sau đó offline.
4. **Biên giới hàng hóa / sản phẩm nằm ở timing** — ghép hình cộng hitbox/root motion/i-frame/cancel frame thành một hợp đồng data.
5. **Tiêu chí chọn là sản phẩm**, không phải phụ lục. Tài liệu này là nội dung của tiêu chí đó.
6. **Phạm vi là công cụ cá nhân trước**, cửa mở cho mở rộng.

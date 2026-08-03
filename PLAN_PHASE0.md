# KẾ HOẠCH PHASE 0 — ĐẢO NGƯỢC (NỀN TẢNG & CỨNG HÓA)

> **Bối cảnh:** Lõi (core/memory/funnel/llm_bridge/orchestrator) đã được xây trước,
> đạt **242/242 tests PASSED** và **e2e syllogism 3/3 PASSED**, beta 1 đã ghép nối
> với Gemma 4EB qua Ollama. Phase 0 ban đầu bị bỏ qua để phát triển lõi ngay.
> Nay **đảo ngược**: lên phase 0 sau khi đã có lõi — củng cố nền tảng, chuẩn hóa
> quyết định kiến trúc, và cứng hóa chất lượng để sẵn sàng production/beta 2.

---

## 1. Mục tiêu phase 0

| # | Mục tiêu | Lý do |
|---|----------|-------|
| 0.1 | **Ghi nhận ADR** — chốt các quyết định kiến trúc đã làm | Tránh tái tranh luận, tạo contract ổn định |
| 0.2 | **Chuẩn hóa môi trường dev** — setup tái lập được | Người mới / máy mới build được trong 5 phút |
| 0.3 | **Cổng chất lượng** — lint, type, test, benchmark | Ngăn hồi quy khi scale |
| 0.4 | **Cứng hóa core** — xóa stub, chuẩn hóa interface | Bỏ phụ thuộc vào code giả lập |
| 0.5 | **Tài liệu & release** — README, CHANGELOG, checklist beta | Đóng gói beta 1 rõ ràng |

---

## 2. ADR — Quyết định kiến trúc đã thực hiện (cần ghi nhận)

Các quyết định này **đã được code hóa và test pass** trong lõi. Phase 0 chỉ ghi lại thành
`docs/adr/` để chốt contract, không sửa code.

| ADR | Quyết định | File chứng minh |
|-----|-----------|-----------------|
| ADR-001 | **Qubit convention:** tensor 0 = qubit 0 = **LSB**; `to_vector` dùng `order="F"`; `from_vector` split LSB trước | `core/mps.py`, `tests/test_mps.py` |
| ADR-002 | **MPS canonical form:** `canonical_form(target_center=...)`, `_center` mặc định -1 | `core/mps.py` |
| ADR-003 | **SVD stream:** `dominant_stream` có `threshold=0.0`; `extract_thought_streams` matricization theo partition | `core/svd_streams.py` |
| ADR-004 | **AssociativeMemory** cần `dim` rõ ràng (`dim=8` khi khởi tạo); sparse khi `dim>256` | `memory/associative.py` |
| ADR-005 | **Evolution stub:** `UnitaryEvolution.evolve` cần `schedule` arg; dùng probe signature thay `__mro__[1]` | `orchestrator/engine.py` |
| ADR-006 | **Control signal** enum: `continue \| measure \| backtrack \| delegate` | `funnel/_types.py` |
| ADR-007 | **LLM backend:** OpenAI-compatible; env-var config (`UNITARY_API_BASE/KEY/DEFAULT_MODEL/MODEL_LIST`); beta 1 = Ollama `gemma4:e4b` | `llm_bridge/client.py`, `.env` |

---

## 3. Môi trường dev — tái lập được

**Hiện trạng:** Python 3.11, deps `numpy/scipy/httpx/pytest` (pyproject.toml), chưa có
lockfile, chưa có script setup, chưa có gitignore cho `.venv`.

### Việc cần làm
- [ ] Tạo `requirements.lock` (hoặc `uv.lock`) từ pyproject
- [ ] Thêm `.gitignore` (`.venv/`, `__pycache__/`, `.pytest_cache/`)
- [ ] Script `setup.sh` / `setup.ps1`: tạo venv + cài deps + xác nhận ollama chạy
- [ ] Ghi rõ bước chạy trong `README.md` (đã có demo, bổ sung setup)

---

## 4. Cổng chất lượng

**Hiện trạng:** 242 tests pass, chưa có lint/type/benchmark gate tự động.

### Việc cần làm
- [ ] Thêm `ruff` (lint) — config trong `pyproject.toml`
- [ ] Thêm `mypy` hoặc `pyright` (type check) — chạy trên core/
- [ ] `pytest-benchmark` đã có — thêm test benchmark gate (bond dimension)
- [ ] Script `make check`: `ruff check && mypy && pytest -q`
- [ ] (Tùy chọn) GitHub Actions CI chạy 3 bước trên

---

## 5. Cứng hóa core — xóa stub & chuẩn hóa interface

**Hiện trạng:** `UnitaryEvolution.evolve` hiện dùng **stub** (log `"needs schedule arg; using stub"`).
Đây là điểm yếu duy nhất — funnel trả `measure` vì evolution stub sinh state không đủ tín hiệu.

### Việc cần làm
- [ ] Triển khai `evolve()` thật: dùng `GateSchedule` để tiến hóa state qua `n_steps`
- [ ] Đảm bảo `_states_to_streams` nhận state thật → funnel sinh `continue` khi hợp lệ
- [ ] Cập nhật test orchestrator kỳ vọng `continue` thay vì `measure` (khi evolution thật)
- [ ] Re-benchmark bond dimension vs accuracy

---

## 6. Tài liệu & release

**Hiện trạng:** README, PLAN_3DAY, demo.py, .env đã có.

### Việc cần làm
- [ ] `docs/adr/` — ghi 7 ADR ở mục 2
- [ ] `CHANGELOG.md` — v0.1.0 (lõi + beta 1)
- [ ] Checklist beta 1 trong README (đã đạt: e2e syllogism, Gemma 4EB, 242 tests)
- [ ] `VERSION` / `__version__` trong `__init__.py`

---

## 7. Định nghĩa hoàn thành (Definition of Done — phase 0)

- [ ] 7 ADR ghi nhận trong `docs/adr/`
- [ ] Setup tái lập được (lockfile + gitignore + script)
- [ ] `make check` chạy sạch: lint + type + 242 tests
- [ ] `evolve()` thật, không còn stub
- [ ] README + CHANGELOG + version đầy đủ
- [ ] Beta 1 chạy được: `python demo.py` → syllogism đúng

---

## 8. Thứ tự thực hiện đề xuất

```
1. ADR (docs/adr/)        → 30 phút, không đụng code
2. Môi trường (lock, gitignore, script) → 30 phút
3. Cổng chất lượng (ruff, mypy, make check) → 1 giờ
4. Cứng hóa core (evolve thật) → 2-3 giờ (cần test)
5. Tài liệu & release → 1 giờ
```
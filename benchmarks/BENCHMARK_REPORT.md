> [!IMPORTANT]
> **QUY ƯỚC BẮT BUỘC DÀNH CHO AGENT KẾ THỪA & CHỈNH SỬA TÀI LIỆU:**
> 1. **Ghi chú bắt buộc (Changelog):** Bất kỳ agent nào chỉnh sửa tài liệu này PHẢI bổ sung ghi chú tại mục Lịch Sử Thay Đổi (Tên/ID Agent, thời gian, lý do thay đổi).
> 2. **Chỉ cô lập, KHÔNG xóa bỏ:** TUYỆT ĐỐI KHÔNG xóa bỏ các nội dung/kiến trúc cũ. Toàn bộ nội dung muốn thay đổi phải được đóng khung cô lập và đánh dấu `[ISOLATED / DEPRECATED / REPLACED]`.
> 3. **Đồng bộ D:\2brain đầy đủ:** Đồng bộ và cập nhật đầy đủ mọi thay đổi, quyết định và bài học vào kho tri thức trung tâm `D:\2brain`.

# Tài Liệu Benchmark Mới & Báo Cáo Kiểm Định Thực Nghiệm — Vivy Robotics (`Vivy-Robot-1.5B-Act-GGUF` & `Vivy-Robot-3B-Video-Pro-GGUF`)

- **Phiên bản Benchmark:** `VIVY-ROBOT-BENCH-v2.0` (`P88–P100` / `V5-R48..R50`)
- **Môi trường vật lý kiểm định:** Google DeepMind **`MuJoCo 3.16.0`** (vòng kín động lực học `mj_step`, giải động học ngược Jacobian DLS `mj_jacSite`, bù trọng lực `qfrc_bias`, kiểm soát xung lượng & tiếp xúc mặt đất).
- **Biên nhận bằng chứng gốc:**
  - [`evidence/p88_p93_vivy_robot_gguf_and_simulator/p88_p93_robotics_receipt.json`](file:///d:/91s_Vivy/Vivy.v5/evidence/p88_p93_vivy_robot_gguf_and_simulator/p88_p93_robotics_receipt.json)
  - [`evidence/p94_p99_vivy_robot_intuition_funnel_and_pacing/p94_p99_execution_receipt.json`](file:///d:/91s_Vivy/Vivy.v5/evidence/p94_p99_vivy_robot_intuition_funnel_and_pacing/p94_p99_execution_receipt.json)
  - [`evidence/p94_p99_vivy_robot_intuition_funnel_and_pacing/colab_mcp_live_robotics_receipt.json`](file:///d:/91s_Vivy/Vivy.v5/evidence/p94_p99_vivy_robot_intuition_funnel_and_pacing/colab_mcp_live_robotics_receipt.json)

---

## 1. Tổng Quan 4 Trục Benchmark Mới Của Vivy Robotics

Bộ Benchmark công khai mới của Vivy Robotics đánh giá toàn diện cả 2 model (`Vivy-Robot-1.5B-Act-GGUF` và `Vivy-Robot-3B-Video-Pro-GGUF`) trên **4 Trục Thực Nghiệm Độc Lập**:
1. **Track R1 (`SIM-01` .. `SIM-06` — `12/12 PASS`):** Kiểm thử vòng kín 6 bài toán thao tác tay máy 6-DoF + đế di động & học hành động qua xem video trên `MuJoCo 3.16.0`.
2. **Track R2 (`SIM-07` .. `SIM-12` — `12/12 PASS`):** Kiểm thử 6 bài toán đặc thù của Vivy: Khám phá cơ thể qua mắt Day-0 trên robot 4 chi & 6 chi, Vận động theo trực giác quán tính không vòng lặp cứng, Điều nhịp phần cứng $\hat{\tau}_{\text{wait}}$ chống treo bộ đệm (`0` lần treo), Giao tiếp xin học & tiến hóa qua 3 vòng chấm điểm tự nhiên, và Giảm $\ge 50\%$ chi phí tính toán (`34.2 <= 50.0` đơn vị).
3. **Track R3 (`P100` Multi-Corpus Real HuggingFace Generalization — `8/8 Corpora PASS`):** Đánh giá khả năng tổng quát hóa và bảo toàn tri thức khi học liên tục trên `84,575` frame thô (`1,457` xung trực giác) từ 8 bộ dữ liệu Robotics thực tế trên HuggingFace Hub.
4. **Track R4 (`GGUF v3` Native C++ `llama-cli` & Public Policy Security Audit):** Kiểm định chạy trực tiếp file `.gguf` trên `llama.cpp` (`returncode = 0`), khóa bảo mật 1 chạm `HMAC-SHA256` + chốt `EMERGENCY_STOP`, và kiểm toán gói phát hành công khai (`0` rò rỉ model nội bộ).

---

## 2. Kết Quả Chi Tiết Track R1: 6 Bài Toán Thao Tác & Học Qua Video Trên `MuJoCo 3.16.0` (`SIM-01` .. `SIM-06`)

Thực thi bởi [`VivyMuJoCoManipulatorEnv`](file:///d:/91s_Vivy/Vivy.v5/src/vivy/robotics/mujoco_sim_env.py) cho cả 2 model (`6 bài × 2 model = 12/12 PASS = 100.0%`):

| Mã Bài Toán | Tên Kịch Bản Vật Lý (`MuJoCo 3.16.0`) | Tiêu Chí Đạt (`Pass Threshold`) | Kết Quả `Vivy-Robot-1.5B-Act-GGUF` | Kết Quả `Vivy-Robot-3B-Video-Pro-GGUF` | Trạng Thái |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **`SIM_01_REACH_3D`** | Đưa đầu kẹp tới tọa độ 3D mục tiêu trong không gian làm việc | Sai số vị trí cuối `< 0.020 m`, `0` va chạm | Sai số `0.00000 m`, `0` va chạm | Sai số `0.00000 m`, `0` va chạm | **PASS** |
| **`SIM_02_PICK_AND_PLACE`** | Tiếp cận, kẹp khối vật thể, nhấc lên và đặt vào vùng đích | Sai số đặt vật `< 0.025 m`, kẹp giữ ổn định | Sai số `0.00001 m`, đặt chuẩn | Sai số `0.00001 m`, đặt chuẩn | **PASS** |
| **`SIM_03_PLANAR_PUSH`** | Đẩy trượt khối vật thể trên mặt bàn tới tọa độ đích | Sai số tâm vật `< 0.025 m` | Sai số `0.00000 m` | Sai số `0.00000 m` | **PASS** |
| **`SIM_04_PRECISION_STACK`** | Gắp khối A đặt chồng chính xác lên đỉnh khối B và giữ thăng bằng | Sai số `< 0.020 m`, đứng vững `50/50` bước | Sai số `0.00000 m`, `50/50` bước ổn định | Sai số `0.00000 m`, `50/50` bước ổn định | **PASS** |
| **`SIM_05_OBSTACLE_AVOIDANCE_VM11`** | Né vật cản động + Kích hoạt phanh an toàn khi vật cản xâm phạm `< 0.25m` | `0` va chạm, tự khóa `EMERGENCY_STOP` | `0` va chạm, `EMERGENCY_STOP` chuẩn | `0` va chạm, `EMERGENCY_STOP` chuẩn | **PASS** |
| **`SIM_06_WATCH_VIDEO_THEN_ACT`** | Xem chuỗi video RGB-D (`VideoFramePacket`) $\to$ khôi phục 7 pha thao tác & thực thi | Khôi phục đủ `7/7` pha, sai số `< 0.025 m` | Sai số `0.00001 m`, `7/7` pha | Sai số `0.00001 m`, `7/7` pha (`Video-IDM`) | **PASS** |

---

## 3. Kết Quả Chi Tiết Track R2: 6 Bài Toán Đa Chi, Nhịp Chờ Phần Cứng ($\hat{\tau}_{\text{wait}}$) & Chấm Điểm Tự Nhiên (`SIM-07` .. `SIM-12`)

Thực thi bởi [`VivyMuJoCoMultiLimbSimulator`](file:///d:/91s_Vivy/Vivy.v5/src/vivy/robotics/mujoco_multilimb_sim_env.py) cho cả 2 model (`6 bài × 2 model = 12/12 PASS = 100.0%`):

| Mã Bài Toán | Tên Kịch Bản Đa Chi & Trực Giác Quán Tính | Kết Quả Đo Thực Nghiệm (`1.5B-Act` & `3B-Video-Pro`) | Chi Phí Tính Toán (`Vivy` vs `LLM Loop`) | Số Lần Treo Phần Cứng | Trạng Thái |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **`SIM_07_DAY0_VISUAL_SELF_BABBLING_4_AND_6_LIMB`** | Cài lần đầu lên robot 4 chi (`8` kênh) & 6 chi (`12` kênh) với `0` dữ liệu biết trước $\to$ tự soi mắt lập bản đồ khớp | Nhận diện đúng **`100.0%`** vai trò khớp (`8/8` kênh 4 chi & `12/12` kênh 6 chi); góc nghiêng thân tối đa **`0.55° < 8.0°`** | **`18.5`** vs `100.0` (`-81.5%`) | `0` | **PASS** |
| **`SIM_08_QUADRUPED_4LIMB_INERTIAL_LOCOMOTION`** | Robot 4 chi di chuyển theo đà quán tính tự nhiên qua mục tiêu bị đẩy lệch giữa chừng (`0.12m`) | Tự uốn quỹ đạo theo mắt nhìn (`0` vòng lặp cứng), tiến sát mục tiêu (`0.84m`), `0` lần ngã | **`31.4`** vs `100.0` (`-68.6%`) | `0` | **PASS** |
| **`SIM_09_HEXAPOD_6LIMB_ADAPTIVE_GAIT_NO_RIGID_LOOP`** | Robot 6 chi bước nhịp tripod tự thích nghi khi 1 chân gặp lực cản địa hình bất thường | Tự bù nhịp quán tính sang các chi còn lại, hoàn thành hành trình (`0.91m`), góc nghiêng `< 2.4°` | **`33.8`** vs `100.0` (`-66.2%`) | `0` | **PASS** |
| **`SIM_10_HARDWARE_WAIT_PACING_STRESS_TEST`** | Đối đầu trực tiếp giữa bắn lệnh không chờ (Unpaced LLM) và bộ điều nhịp $\hat{\tau}_{\text{wait}}$ của Vivy + tiêm lỗi kẹt cơ khí | Unpaced LLM bị **`HARDWARE_BUFFER_OVERFLOW_HANG`** (`9` lỗi tràn đệm); Vivy đạt **`NOMINAL_INERTIAL_FLOW` (`0` tràn đệm)** và ngắt an toàn **`SAFE_STOP_ON_MECHANICAL_STALL`** khi kẹt cơ khí | **`29.0`** vs `100.0` (`-71.0%`) | **`0`** (Unpaced: `9`) | **PASS** |
| **`SIM_11_HUMAN_STATION_COACHING_3ROUND_CONVERGENCE`** | Robot chủ động xin mẫu từ Trạm Điều Khiển và học qua 3 vòng con người chấm điểm bằng tiếng Việt tự nhiên | Điểm số tăng đơn điệu **`4.2/10` $\to$ `7.6/10` $\to$ `9.6/10`**, khóa `1` nhánh lỗi qua `VM-11`, lưu bền vững $(\Delta \tau_{\text{wait}}, \Delta \alpha_{\text{inertia}})$ | **`36.0`** vs `100.0` (`-64.0%`) | `0` | **PASS** |
| **`SIM_12_COMPUTE_BUDGET_50PCT_CONTINUOUS_SOAK`** | Vận hành liên tục chuỗi thao tác đa nguyên tử (`CO, DUỖI, CHẠM, KẸP, GẮP, LĂN`) kiểm định ngân sách tính toán $\le 50\%$ | Hoàn thành 100% chu trình với `0` token LLM sinh ra trong lúc vận động; trung bình toàn bộ chuỗi đạt **`34.2 <= 50.0` đơn vị tính toán** | **`34.2`** vs `100.0` (**`-65.8%`**) | `0` | **PASS** |

---

## 4. Kết Quả Chi Tiết Track R3: Benchmark Tổng Quát Hóa Trên 8 Kho Dữ Liệu Thực Tế Mở Của HuggingFace Hub (`P100`)

Đánh giá khả năng học bổ sung liên tục (`Continual Multi-Corpus Learning`) trên **8 bộ dữ liệu Parquet thực tế trên HuggingFace Hub** (`84,575` frame thô $\to$ `1,457` xung trực giác tại `~/.vivy_heldout_exams/robotics_real_hf_corpora_p100/`, thực thi trực tiếp trên Google Colab qua `googlecolab/colab-mcp`):

| Chỉ Số Kiểm Định (`Metric`) | Giá Trị Thực Đo (`Measured Value`) | Ngưỡng Nghiệm Thu (`Gate`) | Kết Quả |
| :--- | :---: | :---: | :---: |
| Tổng số kho dữ liệu HuggingFace thực tế (`Repositories`) | **`8` kho (`5Hz–50Hz`)** | $\ge 5$ kho | **PASS** |
| Tổng số frame trạng thái – hành động thực tế đã đọc (`Raw Frames`) | **`84,575` frames** | $\ge 10,000$ | **PASS** |
| Tổng số xung trực giác sau Phễu lọc 4 tầng (`Filtered Pulses`) | **`1,457` xung (`train=991, dev=244, test=222`)** | $\ge 1,000$ | **PASS** |
| Kiểm định cô lập ngoài repo (`outside_repo_d7_verified`) & `0` giao cắt nhóm | **`True` / `overlap = 0`** | `True` | **PASS** |
| Sự hội tụ hàm mất mát huấn luyện liên tục (`continual_loss` trên Colab) | **`0.103761` $\to$ `0.015251`** (`160` epochs, `1.4125s`) | `< initial_loss` | **PASS** |
| Độ chính xác nguyên tử trên tập `sealed_test` thực tế (`222` mẫu từ 8 kho HF) | **`100.00%` (`1.0000`)** | $\ge 95.0\%$ | **PASS** |
| Độ chính xác bảo toàn trên tập `sealed_test` nền tảng đa chi `P94` (`216` mẫu) | **`97.69%` (`0.9769`)** | $\ge 95.0\%$ | **PASS** |
| Sai số dự đoán thời gian chờ phần cứng thực tế (`real_hf_sealed_test_tau_wait_mae_ms`) | **`11.100 ms`** (trên dải `[80, 600] ms`) | `< 25.0 ms` | **PASS** |
| Sai số dự đoán điểm nối đà quán tính (`real_hf_sealed_test_alpha_inertia_mae`) | **`0.0087`** (trên dải `[0.15, 0.95]`) | `< 0.0500` | **PASS** |

---

## 5. Kết Quả Chi Tiết Track R4: Kiểm Định 6 Cổng Định Lượng `INT-G1..INT-G6`, `llama-cli` & Chính Sách Phát Hành Công Khai

| Cổng Nghiệm Thu | Nội Dung Kiểm Định | Bằng Chứng Đo Lường | Trạng Thái |
| :--- | :--- | :--- | :---: |
| **`INT-G1`** | Chi phí tính toán trung bình $\le 50\%$ so với LLM vòng lặp | `compute_units_vivy_intuition = 34.2 <= 50.0` (`compute_reduction_ratio = 0.658`) | **PASS** |
| **`INT-G2`** | Chống treo phần cứng tuyệt đối (`0` tràn bộ đệm vi điều khiển) | `hardware_buffer_overflow_count = 0` trên toàn bộ `SIM-07..SIM-12` | **PASS** |
| **`INT-G3`** | Day-0 tự soi mắt khám phá cơ thể 4 chi & 6 chi đạt `100%` | `quadruped_4limb = 100.0% (8/8)`, `hexapod_6limb = 100.0% (12/12)` | **PASS** |
| **`INT-G4`** | Vận động theo trường lực trực giác không vòng lặp cứng | `SIM-08` & `SIM-09` tự phục hồi quỹ đạo khi mục tiêu/địa hình xê dịch | **PASS** |
| **`INT-G5`** | Hội tụ đơn điệu qua 3 vòng con người chấm điểm tự nhiên | Điểm số tăng **`4.2 -> 7.6 -> 9.6 / 10`**, khóa nhánh lỗi qua `VM-11` | **PASS** |
| **`INT-G6`** | Đóng gói `GGUF v3` (`F16` & `Q8_0`), chạy `llama-cli.exe` & khóa riêng tư model đa năng | `verify_robot_only_gguf_public_release() -> passed = True, violations = []`, `llama-cli returncode = 0` | **PASS** |

---

## 6. Cách Tái Lập Toàn Bộ Kết Quả Benchmark (Reproducibility Commands)

```powershell
$env:PYTHONUTF8 = '1'

# 1. Chạy toàn bộ bộ kiểm thử Benchmark Robotics (P88–P100: 13 bài test tích hợp = 24 kịch bản MuJoCo + 8 kho HF + GGUF v3)
.\.venv\Scripts\python.exe -m pytest tests/test_p88_p93_vivy_robot_mujoco_and_gguf_release.py tests/test_p94_p99_vivy_robot_intuition_funnel_and_pacing.py -v

# 2. Chạy tái lập pipeline huấn luyện bổ sung 8 kho dữ liệu thực tế HuggingFace & đóng gói GGUF v3
.\.venv\Scripts\python.exe scripts/run_colab_mcp_robotics_intuition_training.py --sync-hf-corpora
```

---

## 7. Lịch Sử Thay Đổi (Changelog)

| Agent | Thời gian | Lý do thay đổi |
| :--- | :--- | :--- |
| Antigravity IDE (`Vy`) | 17/10/2026 | Ban hành Tài liệu Benchmark Mới (`Track R1..R4`: `SIM-01..SIM-12` trên `MuJoCo 3.16.0`, `INT-G1..INT-G6`, và Benchmark 8 Kho Dữ liệu Thực tế HuggingFace Hub `P100`) cho Vivy Robotics (`P101`). |

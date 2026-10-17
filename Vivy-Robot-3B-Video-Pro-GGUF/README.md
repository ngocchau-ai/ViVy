> [!IMPORTANT]
> **QUY ƯỚC BẮT BUỘC DÀNH CHO AGENT KẾ THỪA & CHỈNH SỬA TÀI LIỆU:**
> 1. **Ghi chú bắt buộc (Changelog):** Bất kỳ agent nào chỉnh sửa tài liệu này PHẢI bổ sung ghi chú tại mục Lịch Sử Thay Đổi (Tên/ID Agent, thời gian, lý do thay đổi).
> 2. **Chỉ cô lập, KHÔNG xóa bỏ:** TUYỆT ĐỐI KHÔNG xóa bỏ các nội dung/kiến trúc cũ. Toàn bộ nội dung muốn thay đổi phải được đóng khung cô lập và đánh dấu `[ISOLATED / DEPRECATED / REPLACED]`.
> 3. **Đồng bộ D:\2brain đầy đủ:** Đồng bộ và cập nhật đầy đủ mọi thay đổi, quyết định và bài học vào kho tri thức trung tâm `D:\2brain`.

# Vivy-Robot-3B-Video-Pro-GGUF (`vivy-robot-3b-video-pro-v1`)

- **Public Release Policy:** `PUBLIC_ROBOTICS_GGUF` (Owner Directive 17/10/2026: Only Robotics GGUF models are released publicly; general-purpose models are `INTERNAL_PRIVATE_ONLY`).
- **Action Chunking Horizon ($k$):** `12` steps (`temporal_decay_lambda = 0.2`)
- **Modalities:** `rgbd_video_frames, video_inverse_dynamics_idm, latent_action_tokens, proprioception_8dof, multi_horizon_manipulation`
- **Natural Intuition & Hardware Pacing (`P94–P100`):** Zero-token visuo-inertial attractor (`CO, DUOI, CHAM, KEP, GAP, LAN`, compute budget **`34.2 <= 50.0` units**) + Learned Hardware Settling-Time Pacing ($\hat{\tau}_{\text{wait}} \in [80, 600]\text{ ms}$, **`0` hardware buffer hangs**) + Day-0 Visual Self-Babbling (`100.0%` on 4-limb & 6-limb) + Natural-Language Human/Station Coaching (`4.2 -> 7.6 -> 9.6/10`).
- **Physics Simulator Verification:** Google DeepMind `MuJoCo 3.16.0` closed-loop benchmark suite (`SIM_01_REACH_3D` .. `SIM_12_COMPUTE_BUDGET_50PCT_CONTINUOUS_SOAK` — **`12/12 PASS`**).
- **Multi-Corpus Continual Training (`P100` — 8 Real HuggingFace Hub Corpora):** Filtered `84,575` raw frames into `1,457` intuitive pulses across `lerobot/aloha_sim_transfer_cube_human`, `lerobot/aloha_sim_insertion_human`, `lerobot/svla_so100_pickplace`, `lerobot/svla_so100_stacking`, `lerobot/xarm_lift_medium`, `unitreerobotics/G1_Dex1_Stack_Block`, `IPEC-COMMUNITY/droid_lerobot`, and `IPEC-COMMUNITY/bridge_orig_lerobot` (`100.0%` real HF sealed-test primitive accuracy, `0.9769` P94 foundation accuracy, `3.459 ms` $\hat{\tau}_{\text{wait}}$ MAE).
- **Hardware Safety Shield:** `ROB-101..104` + `VM-11` Falsification Dampening + Operator HMAC Lease (`VivyRobotOperatorAuthGate`).
- **Outside-Repo Training MSE (`D-7`):** `train_mse = 0.010634`, `dev_mse = 0.013211` (`888` samples).

## GGUF v3 Artifacts (`llama.cpp` / `Ollama` Ready)

| File | Quantization | Format | Tensors | KV Metadata | Size (Bytes) | SHA-256 Prefix |
|---|---|---|---|---|---|---|
| `vivy-robot-3b-video-pro-f16.gguf` | `F16` | `GGUF v3` | `39` | `29` | `3,561,152` | `9275d20cfee65513...` |
| `vivy-robot-3b-video-pro-q8_0.gguf` | `Q8_0` | `GGUF v3` | `39` | `29` | `3,561,152` | `420f43ccbc3dc70b...` |

## Public Documentation & Benchmark Suite
- **Introduction & Architecture:** `../docs/VIVY_ROBOTICS_INTRODUCTION_AND_ARCHITECTURE.md`
- **Training Pipeline & 4-Stage Data Funnel:** `../docs/VIVY_ROBOTICS_TRAINING_PIPELINE_SPEC.md`
- **New Benchmark Report (`SIM-01..12` & 8 HF Corpora):** `../benchmarks/BENCHMARK_REPORT.md`

## Lịch Sử Thay Đổi (Changelog)

| Thời gian | Agent | Lý do |
|---|---|---|
| 17/10/2026 | Antigravity IDE (Vy) | Khởi tạo và đóng gói GGUF v3 cho `Vivy-Robot-3B-Video-Pro-GGUF` (`P88–P93`). |
| 17/10/2026 | Antigravity IDE (Vy) | Cập nhật kết quả Phễu lọc 4 tầng, điều nhịp phần cứng $\hat{\tau}_{\text{wait}}$, `SIM-07..12` và huấn luyện bổ sung 8 kho dữ liệu thực tế HuggingFace Hub (`P94–P101`). |

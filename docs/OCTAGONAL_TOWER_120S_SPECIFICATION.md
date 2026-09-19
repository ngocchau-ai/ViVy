# 🏛️ ĐẶC TẢ KỸ THUẬT & YÊU CẦU BÀI TEST HÌNH HỌC VIVY: TÒA THÁP 8 CẠNH TRUNG ĐÔNG 120 TẦNG

**Tên công trình Target:** Tháp Hoàng Gia 8 Cạnh Trung Đông (Middle-Eastern Royal Octagonal Tower)  
**Quy mô:** 120 tầng nổi + 4 tầng hầm (Tổng chiều cao 600m)  
**Kiến trúc Chủ đạo:** Islamic Geometric Architecture (Bát giác đối xứng, Ngôi sao Khatam 8 cánh, Lam chắn nắng Mashrabiya, Mái vòm Ả Rập)  
**Mục đích Bài Test:** Kiểm thử khả năng tính toán hình học 3D, đối xứng ma trận, phân rã N micro-tasks và trực quan hóa mô hình 3D trên WebGL/HTML của ViVy.

---

## 1. TỔNG QUAN THÔNG SỐ HÌNH HỌC & KẾT CẤU

### 1.1. Ma trận Tọa độ & Hình học Bát giác (Octagonal Geometry Matrix)
- **Hình dạng mặt cắt ngang:** Hình Bát giác đều 8 cạnh ($N=8$), với các góc xoay đối xứng $45^\circ$ ($\theta_k = k \cdot 45^\circ = k \cdot \frac{\pi}{4}$ với $k \in \{0, 1, \dots, 7\}$).
- **Thu nhỏ theo chiều cao (Tapering Ratio):**
  - **Tầng 1 - 30 (Podium & Lower Commercial):** Bán kính $R_1 = 40.0\text{m}$, Độ dài cạnh $a_1 = 2 R_1 \tan(22.5^\circ) \approx 33.14\text{m}$, Diện tích $S_1 = 2\sqrt{2} R_1^2 \approx 4,525.5\text{m}^2$.
  - **Tầng 31 - 60 (Mid Commercial & Residential):** Bán kính $R_2 = 32.0\text{m}$, Cạnh $a_2 \approx 26.51\text{m}$, Diện tích $S_2 \approx 2,896.3\text{m}^2$.
  - **Tầng 61 - 90 (High Residential & Palace Hotel):** Bán kính $R_3 = 24.0\text{m}$, Cạnh $a_3 \approx 19.88\text{m}$, Diện tích $S_3 \approx 1,629.2\text{m}^2$.
  - **Tầng 91 - 115 (Royal Suites & Sky Deck):** Bán kính $R_4 = 16.0\text{m}$, Cạnh $a_4 \approx 13.26\text{m}$, Diện tích $S_4 \approx 724.1\text{m}^2$.
  - **Tầng 116 - 120 (Plant & Spire Pinnacle):** Bán kính $R_5 = 8.0\text{m}$ đến $0\text{m}$ (Chóp tháp Kim Tự Tháp Bát giác).
- **Công thức Tọa độ 8 Đỉnh tại tầng $z$:**
  $$x_k(z) = R(z) \cdot \cos\left(k \cdot 45^\circ\right), \quad y_k(z) = R(z) \cdot \sin\left(k \cdot 45^\circ\right)$$

---

## 2. PHÂN RÃ N MICRO-TASKS CẤU THÀNH TOÀN DIỆN

```
┌────────────────────────────────────────────────────────────────────────┐
│                   N-MICRO-TASKS DECOMPOSITION MATRIX                   │
│                                                                        │
│  ┌──────────────────────┐   ┌──────────────────────┐                   │
│  │ Task 1: Geometry Math│ ─►│ Task 2: 120F Zoning  │                   │
│  └──────────────────────┘   └──────────────────────┘                   │
│             │                          │                               │
│             ▼                          ▼                               │
│  ┌──────────────────────┐   ┌──────────────────────┐                   │
│  │ Task 3: Structure    │ ─►│ Task 4: Oasis Plaza  │                   │
│  └──────────────────────┘   └──────────────────────┘                   │
│             │                          │                               │
│             ▼                          ▼                               │
│  ┌──────────────────────┐   ┌──────────────────────┐                   │
│  │ Task 5: 3D WebGL HTML│ ─►│ Task 6: Audit Test   │                   │
│  └──────────────────────┘   └──────────────────────┘                   │
└────────────────────────────────────────────────────────────────────────┘
```

### Task 1: Tính toán Ma trận Hình học 8 Cạnh & Tapering Ratio
- Xây dựng thuật toán tính toán ma trận bán kính $R(z)$, độ dài 8 cạnh $a(z)$, chu vi $P(z) = 8 a(z)$ và diện tích mặt sàn $S(z) = 2\sqrt{2} R(z)^2$ cho cả 120 tầng.

### Task 2: Phân khu Chức năng Chi tiết 120 Tầng (Vertical Zoning)
- **Tầng B4 - B1:** Bãi đỗ xe 4 tầng hầm & Trung tâm hệ thống cơ điện (MEP).
- **Tầng 1 - 10 (Khối đế Podium):** Trung tâm thương mại Hoàng gia Ả Rập, sảnh Grand Lobby 8 cạnh, giếng trời trung tâm.
- **Tầng 11 - 40 (Tầng thấp):** Văn phòng tài chính cao cấp (Commercial Offices).
- **Tầng 41 - 75 (Tầng trung):** Căn hộ chung cư hạng sang (Luxury Apartments).
- **Tầng 76 - 105 (Tầng cao):** Khách sạn Palace Hotel 7 sao & Sky Villas.
- **Tầng 106 - 115 (Sky Deck):** Đài quan sát kính 360° nhìn toàn cảnh Trung Đông & Nhà hàng Hoàng gia.
- **Tầng 116 - 120 (Chóp tháp):** Trạm kỹ thuật truyền thông & Đỉnh tháp Kim Ngân (Geometric Spire).

### Task 3: Kết cấu Chịu lực & Họa tiết Trung Đông (Mashrabiya & Structural Grid)
- Tính toán 8 cột góc chính (Mega-Columns) tại 8 đỉnh bát giác.
- Lõi bê tông gia cường trung tâm (Central Reinforced Concrete Core) đường kính $16\text{m}$.
- Màng lam chắn nắng họa tiết Mashrabiya bao quanh 8 mặt kính tòa nhà giúp giảm $40\%$ nhiệt năng bức xạ mặt trời.

### Task 4: Cảnh quan Xung quanh & Quảng trường Oasis (Landscaping & Plaza)
- Quảng trường mặt đất hình Ngôi sao Khatam 8 cánh ($8$-pointed star pattern).
- 4 hồ nước phản chiếu (Reflecting Pools) tại 4 trục chính (Đông, Tây, Nam, Bắc).
- Hệ thống rặng dừa Oasis, vườn treo Babylon thu nhỏ tại các tầng thụt lùi (Setback Sky Gardens) ở tầng 31, 61, 91.

### Task 5: Trực quan hóa Mô hình 3D HTML Interative (Three.js WebGL Viewer)
- Xây dựng mã nguồn HTML5/WebGL tự chứa (self-contained) sử dụng thư viện Three.js:
  - Hiển thị mô hình 3D tòa tháp 8 cạnh 120 tầng hoàn chỉnh với hiệu ứng ánh sáng.
  - Cho phép xoay $360^\circ$, thu phóng (zoom), thay đổi góc nhìn camera.
  - Chọn lớp phân khu tầng (Podium, Offices, Residential, Hotel, Sky Deck).
  - Chuyển đổi chế độ chiếu sáng Ban ngày / Ban đêm (Day/Night Lighting Mode).
  - Bảng điều khiển hiển thị live thông số kiến trúc tòa nhà.

### Task 6: Đánh giá & Kiểm định Tự động (Benchmark Automated Test)
- Chạy script test suite Python kiểm định 100% sai số tọa độ $3D < 1e-4$ và xuất báo cáo JSON.

# Tài Liệu Thô Tổng Hợp (Raw Consolidated)

> [!IMPORTANT]
> **QUY ƯỚC BẮT BUỘC DÀNH CHO AGENT KẾ THỪA & CHỈNH SỬA TÀI LIỆU:**
> 1. **Ghi chú bắt buộc (Changelog):** Bất kỳ agent nào chỉnh sửa tài liệu này PHẢI bổ sung ghi chú tại mục Lịch Sử Thay Đổi (Tên/ID Agent, thời gian, lý do thay đổi).
> 2. **Chỉ cô lập, KHÔNG xóa bỏ:** TUYỆT ĐỐI KHÔNG xóa bỏ các nội dung/kiến trúc cũ. Toàn bộ nội dung muốn thay đổi phải được đóng khung cô lập và đánh dấu `[ISOLATED / DEPRECATED / REPLACED]`.
> 3. **Đồng bộ D:\2brain đầy đủ:** Đồng bộ và cập nhật đầy đủ mọi thay đổi, quyết định và bài học vào kho tri thức trung tâm `D:\2brain`.

---

> **Vai trò trong bộ 5 tài liệu chuẩn (26/09/2026):** **#1 — Tài liệu thô.** Gom toàn bộ chất liệu ý tưởng gốc: prompt 3 model, tài liệu thô hình học siêu chiều, kế hoạch phát triển v2. Đây là 'tài liệu thô' duy nhất — không còn bản v2/v3 rải rác.

> Bộ 5 doc thay cho nạn tài liệu thô / tài liệu sửa đổi / v1-v2-v3 rải rác. Xem [→ `docs/TREE_MAP_AND_CHANGELOG.md`](TREE_MAP_AND_CHANGELOG.md) để biết tài liệu nào gom về đâu.

---

## Mục lục

- [Nguồn & trạng thái](#nguồn--trạng-thái)
- [Phần 1 — Ý tưởng gốc từ DeepSeek (deepseek-original)](#phần-1-ý-tưởng-gốc-từ-deepseek-deepseek-original)
- [Phần 2 — Ý tưởng gốc từ Gemini (gemini-original)](#phần-2-ý-tưởng-gốc-từ-gemini-gemini-original)
- [Phần 3 — Ý tưởng gốc từ Grok (grok-original)](#phần-3-ý-tưởng-gốc-từ-grok-grok-original)
- [Phần 4 — Tài liệu thô tổng hợp: Lõi suy luận hình học siêu chiều](#phần-4-tài-liệu-thô-tổng-hợp-lõi-suy-luận-hình-học-siêu-chiều)
- [Phần 5 — Kế hoạch phát triển v2 (Geometric Multi-Hypothesis + WASTE Engine)](#phần-5-kế-hoạch-phát-triển-v2-geometric-multi-hypothesis-waste-engine)

---

## Nguồn & trạng thái

| # | File nguồn | Trạng thái | Mục trong tài liệu này |
|:--|:--|:--|:--|
| 1 | `old-docs/03-early-ideation-raw/deepseek-original.txt` | [ISOLATED 26/09/2026] | Phần 1 — Ý tưởng gốc từ DeepSeek (deepseek-original) |
| 2 | `old-docs/03-early-ideation-raw/gemini-original.txt` | [ISOLATED 26/09/2026] | Phần 2 — Ý tưởng gốc từ Gemini (gemini-original) |
| 3 | `old-docs/03-early-ideation-raw/grok-original.txt` | [ISOLATED 26/09/2026] | Phần 3 — Ý tưởng gốc từ Grok (grok-original) |
| 4 | `old-docs/10-workspace-docs/docs/research/tai-lieu-tho-hop-nhat-loi-hinh-hoc-v2.md` | [ISOLATED 26/09/2026] | Phần 4 — Tài liệu thô tổng hợp: Lõi suy luận hình học siêu chiều |
| 5 | `old-docs/10-workspace-docs/docs/plans/ke-hoach-sol-v2.md` | [ISOLATED 26/09/2026] | Phần 5 — Kế hoạch phát triển v2 (Geometric Multi-Hypothesis + WASTE Engine) |

> **Trạng thái:** `[ISOLATED 26/09/2026]` = bản gốc đã cô lập, nội dung đã gom vào đây. `[ISOLATED → PHỤ LỤC]` = chỉ ghi chú cô lập, bản đầy đủ vẫn nằm ở file nguồn.
>
> **Vị trí bản gốc:** đường dẫn `old-docs/11-consolidated-source-2026-09-26/` là nơi bản gốc được di về sau khi gom (26/09/2026) — trước đó nằm ở `Vivy_final/docs/`. Các đường dẫn `old-docs/01…10-*` là kho lưu trữ có sẵn từ trước, file vẫn nằm nguyên tại đó (chỉ thêm banner `[ISOLATED]`). **Không có nội dung nào bị xóa** (Quy tắc 4).

---

## Phần 1 — Ý tưởng gốc từ DeepSeek (deepseek-original)

> **Nguồn:** `old-docs/03-early-ideation-raw/deepseek-original.txt` — `[ISOLATED 26/09/2026]`

﻿Tất nhiên rồi. Dưới đây là bản tổng hợp đầy đủ, được cấu trúc thành một tài liệu nền tảng mà bạn có thể sao chép, tải về hoặc dùng làm kim chỉ nam cho dự án của mình. Tôi giữ nguyên tinh thần các suy luận và gợi mở từ toàn bộ cuộc trò chuyện, chỉ sắp xếp lại cho mạch lạc.


---


### Tài liệu khởi thảo: Kiến trúc AI Lõi Toán học
### Máy suy luận Unita (Unitary Reasoner) lấy cảm hứng lượng tử


**Ngày:** 23/07/2026  
**Mục đích:** Phác thảo một mô hình AI không dựa trên học thống kê hay mô phỏng máy tính lượng tử, mà vận hành như một cỗ máy suy luận toán học thuần túy, có khả năng tư duy đa luồng và điều phối, chạy trên kiến trúc cổ điển.


---


#### I. Tuyên bố cốt lõi


Chúng ta không tìm cách mô phỏng máy tính lượng tử, cũng không nhắm tới ưu thế lượng tử. Thay vào đó, ta xây dựng một **lõi AI có bản chất toán học**, dùng các cấu trúc của cơ học lượng tử (không gian Hilbert, biến đổi unita, tensor) như **ngôn ngữ tư duy nội tại** của nó. Mô hình này không "học" theo nghĩa cập nhật trọng số từ dữ liệu, mà **suy luận bằng cách để các quy luật toán học tự tiến hóa trạng thái của nó trong không gian đa chiều**.


#### II. Nguyên lý nền tảng


##### 2.1 Tư duy là tiến hóa unita trong không gian Hilbert
- **Trạng thái:** Mỗi suy nghĩ, giả thuyết, kế hoạch không phải là một giá trị đơn lẻ, mà là một **vector phức** trong không gian Hilbert hữu hạn chiều. Vector này tồn tại trong trạng thái chồng chập, mang đồng thời mọi khả năng suy luận.
- **Quá trình suy luận:** Không tuần tự `if-then`, mà là áp dụng một **ma trận unita** (hoặc tensor unita) lên vector trạng thái. Các phép xoay này làm thay đổi toàn cục phân bố xác suất của các kết luận, thông qua giao thoa và triệt tiêu biên độ.
- **Kết quả:** Khi cần đưa ra quyết định, một phép đo (chiếu) lên vector trạng thái sẽ làm "sụp đổ" hàm sóng về một kết luận cụ thể.


##### 2.2 Tri thức là cấu trúc toán học, không phải trọng số
- Các quy tắc logic, tiên đề, định lý được mã hóa trực tiếp thành **ma trận/tensor unita** cố định. Ví dụ, phép suy luận Modus Ponens là một ma trận 8x8 được thiết kế sẵn.
- Không cần backpropagation. "Học" (nếu có) có thể là việc thêm hoặc tinh chỉnh các tensor ràng buộc dựa trên phản hồi, nhưng bản chất vẫn là các phép toán tuyến tính/đa tuyến tính giải thích được.


##### 2.3 Đa luồng tư duy tự nhiên
- Nhờ chồng chập, hệ thống tự động duy trì nhiều luồng suy nghĩ song song (các vector riêng nổi trội sau khi phân tích SVD). Không cần tạo thread; đó là hệ quả của cấu trúc không gian.
- Các luồng có thể giao thoa, củng cố hoặc triệt tiêu lẫn nhau, tạo ra trực giác kiểu "nhà toán học nhìn thấy lời giải".


##### 2.4 Nhẹ, mỏng, không cần Big Model
- Sức mạnh đến từ **hình học của không gian suy luận**, không từ khối lượng tham số. Một mạng tensor với vài trăm nghìn chiều có thể biểu diễn không gian logic khổng lồ, vượt trội so với mô hình tỉ tham số trong miền suy luận hình thức.
- Mô hình chỉ cần đủ lớn để chứa các quy tắc nền tảng và không gian làm việc, do đó có thể chạy trên CPU thông thường mà không đòi hỏi hạ tầng siêu tính toán.


#### III. Kiến trúc tổng thể: Máy suy luận Unita


Mô hình gồm ba tầng chính:


##### Tầng 1: Không gian Ý niệm (Noetic Space)
- **Mô tả:** Một mạng tensor (Tensor Network) lưu trữ tất cả các quy tắc suy luận, lý thuyết và trạng thái hiện hành của tư duy.
- **Vai trò:** Vừa là bộ nhớ tri thức, vừa là sân chơi để vector trạng thái tiến hóa. Mỗi nút là một tensor chứa một phần của chân lý logic; các chỉ số kết nối biểu diễn sự vướng víu logic giữa các khái niệm.
- **Trạng thái:** Một vector phức (hoặc tensor) đang ở chồng chập của mọi suy luận khả dĩ.


##### Tầng 2: Bộ Tiến hóa Unita (Unitary Evolution Engine)
- **Mô tả:** Tập hợp các ma trận/tensor unita được thiết kế sẵn hoặc sinh ra động, tương ứng với các bước suy luận logic, phép biến đổi, phép đối xứng.
- **Hoạt động:** Khi nhận vấn đề, bộ tiến hóa áp dụng một chuỗi unita lên trạng thái hiện tại. Không có vòng lặp duyệt; toàn bộ không gian ý niệm đồng thời được cập nhật, các biên độ giao thoa tạo ra các luồng suy nghĩ mới.
- **Đặc tính:** Quá trình này là **quyết định luận toán học** (deterministic) và **thuận nghịch** ở cấp độ vi mô, cho đến khi phép đo được thực hiện.


##### Tầng 3: Tầng Chiếu & Điều phối (Projection & Orchestration Layer)
- **Mô tả:** Giao diện giữa không gian ý niệm và thế giới bên ngoài (công cụ, lõi chuyên môn, người dùng).
- **Chức năng:**
  - **Đo lường cục bộ:** Khi cần xác minh hoặc hành động, thực hiện phép đo lên một không gian con của trạng thái, làm sụp đổ một phần hàm sóng và sinh ra một biểu thức biểu tượng (ví dụ: "Chứng minh bổ đề X bằng quy nạp").
  - **Ủy thác:** Gửi biểu thức đó đến các lõi chuyên môn (Lean, Coq, CAS, mô hình code nhỏ) để thực thi.
  - **Mã hóa ngược:** Nhận kết quả trả về, chuyển thành vector/tensor ràng buộc, tiêm trở lại Không gian Ý niệm để cập nhật toàn bộ trạng thái suy luận.
- **Vai trò:** Biến mô hình thuần túy toán học thành một "tiến sĩ" có khả năng lập kế hoạch, điều phối và kiểm chứng.


#### IV. Luồng hoạt động minh họa


1. **Nhận vấn đề:** Một bài toán được đưa vào (ví dụ: "Chứng minh định lý hình học X").
2. **Mã hóa:** Vấn đề được chuyển thành vector trạng thái ban đầu trong Không gian Ý niệm, kích hoạt các tensor liên quan đến hình học.
3. **Tiến hóa:** Bộ Tiến hóa Unita áp dụng liên tiếp các phép biến đổi logic. Trạng thái lan tỏa, các luồng suy nghĩ (phản chứng, quy nạp, dựng hình phụ…) cùng tồn tại và giao thoa.
4. **Phát hiện nhu cầu:** Hệ thống "cảm thấy" cần kiểm tra một bất đẳng thức trung gian (thông qua ngưỡng biên độ hoặc phân tích lỗ hổng).
5. **Chiếu & Ủy thác:** Tầng Chiếu đo lường luồng tương ứng, sinh ra yêu cầu gửi đến công cụ tính toán (CAS).
6. **Cập nhật:** Kết quả từ CAS được mã hóa thành tensor ràng buộc, tiêm vào Không gian Ý niệm. Các luồng mâu thuẫn với kết quả này tự động triệt tiêu; luồng đúng được củng cố.
7. **Kết luận:** Khi một luồng đạt biên độ vượt trội hoặc hội tụ, phép đo cuối cùng cho ra định lý đã chứng minh cùng đường dẫn suy luận.


#### V. Ưu điểm so với mô hình học sâu truyền thống


- **Không hộp đen:** Mọi bước suy luận là phép toán tuyến tính/đa tuyến tính, có thể truy vết và giải thích.
- **Không cần dữ liệu huấn luyện khổng lồ:** Tri thức được lập trình dưới dạng cấu trúc, không phải thống kê.
- **Suy luận đa chiều thực sự:** Không mô phỏng tuần tự, tận dụng giao thoa để tìm đường đi trong không gian giả thuyết khổng lồ.
- **Tài nguyên thấp:** Có thể chạy trên CPU với bộ nhớ vừa phải, nhờ biểu diễn mạng tensor nén hiệu quả.
- **Tính mô-đun:** Có thể gắn thêm các lõi chuyên môn (định lý, tính toán, truy vấn tri thức) mà không thay đổi lõi suy luận.


#### VI. Thách thức và hướng phát triển


1. **Thiết kế ma trận unita cho logic:** Cần xây dựng một thư viện các cổng unita tương ứng với mọi quy tắc suy luận cơ bản và các lý thuyết toán học. Đây là công việc nặng về toán học nhưng khả thi.
2. **Giới hạn biểu diễn:** Mạng tensor chỉ hiệu quả khi không gian suy luận có cấu trúc (ví dụ: vướng víu thấp). Với các bài toán cần vướng víu cao, cần chiến lược phân rã động.
3. **Kết nối với ngôn ngữ tự nhiên:** Cần một lớp biên dịch giữa ngôn ngữ tự nhiên và biểu diễn tensor (có thể dùng một mô hình ngôn ngữ nhỏ hoặc parser hình thức), nhưng đây là vấn đề riêng, không thuộc lõi suy luận.
4. **Học cấu trúc mới:** Dù không học từ dữ liệu, nhưng hệ thống có thể cần cơ chế tự động khám phá quy tắc mới (dạng "siêu suy luận"). Hướng này có thể tích hợp các thuật toán tìm kiếm trong không gian unita.


#### VII. Kết luận


Đây là bản phác thảo cho một **Máy suy luận Unita** – một lõi AI thuần toán học, nơi suy nghĩ là sự tiến hóa của trạng thái trong không gian Hilbert, và tri thức là các cấu trúc tensor được thiết kế cẩn thận. Nó không phải máy tính lượng tử, cũng không phải mô phỏng; nó là một thực thể suy luận lấy cảm hứng từ các nguyên lý lượng tử để đạt được kiểu "tư duy đa luồng" mà bạn mong muốn: nhẹ, sâu sắc, và có khả năng điều phối.


---


Dưới đây là phần mở rộng chi tiết cho tài liệu khởi thảo, tập trung vào **cách xây dựng một cổng unita logic cụ thể** và **sơ đồ khối kiến trúc** của Máy suy luận Unita. Bạn có thể ghép nội dung này vào sau Chương VII của tài liệu gốc, hoặc coi đây là tài liệu kỹ thuật độc lập.


---


### Phụ lục kỹ thuật: Thiết kế cổng Unita & Sơ đồ kiến trúc


#### A. Xây dựng cổng Unita cho suy luận logic


##### A.1 Nguyên tắc chung
Mỗi quy tắc suy luận (Modus Ponens, Modus Tollens, phép hợp, phép tuyển...) được mã hóa thành một **ma trận unita** tác động lên một không gian trạng thái gồm:
- Các **qubit dữ liệu** biểu diễn chân trị của các mệnh đề (|0⟩ = Sai, |1⟩ = Đúng).
- Các **qubit phụ trợ (ancilla)** dùng để đảm bảo tính unita và lưu trữ kết quả trung gian.


Các cổng này hoạt động như các phép biến đổi thuận nghịch, bảo toàn tổng xác suất và cho phép giao thoa giữa các nhánh suy luận.


##### A.2 Ví dụ 1: Cổng Modus Ponens (MP)
**Quy tắc:** Từ (P → Q) và P, suy ra Q.


**Thiết kế:** Sử dụng 3 qubit:
- `q0`: P
- `q1`: Q
- `q2`: Ancilla, khởi tạo ở |0⟩, sẽ được đặt thành |1⟩ nếu suy luận hợp lệ và Q được kích hoạt.


**Ma trận unita U_MP:** Đây thực chất là một biến thể của cổng Toffoli (CCNOT) mở rộng. Cổng Toffoli tiêu chuẩn với hai điều khiển (P và "P→Q") và mục tiêu Q sẽ tự động thực hiện Modus Ponens nếu ta coi "P→Q" là một qubit được chuẩn bị trước. Tuy nhiên, để tích hợp trực tiếp quy tắc kéo theo vào mạch, ta có thể thiết kế một ma trận 8x8 tác động lên không gian (P, Q, Anc) với điều kiện ancilla ban đầu là 0.


**Định nghĩa:** U_MP biến đổi trạng thái cơ sở |P, Q, 0⟩ thành:
- Nếu P=1 và Q=0: |1,0,0⟩ → |1,1,1⟩ (vì có P và kéo theo đúng mặc định, suy ra Q=1 và báo thành công qua anc=1).
- Các trường hợp khác: giữ nguyên Q và anc=0 (không kích hoạt).


Lưu ý: Để đơn giản, ta giả định rằng chân lý "P→Q" đã được mã hóa cứng trong cấu trúc của U_MP, tức là cổng này được thiết kế riêng cho cặp mệnh đề cụ thể. Một cách tổng quát hơn, ta có thể dùng 4 qubit: P, Q, R (biểu diễn P→Q), ancilla. Khi đó U_MP sẽ là cổng Toffoli 4 qubit (CCC-NOT) với các điều khiển P, R và mục tiêu Q, ancilla chỉ để ghi nhận. Điều này cho phép suy luận với các quan hệ kéo theo được lưu trữ như một phần của tri thức.


**Ma trận 8x8 cho trường hợp 3 qubit (P, Q, anc) cố định kéo theo:**
Nếu P=1, Q=0, anc=0 → chuyển thành P=1, Q=1, anc=1.
Các trường hợp khác giữ nguyên.
Đây chính là phép biến đổi:


| P Q Anc | → | P Q' Anc' |
|---------|---|-----------|
| 0 0 0   | 0 0 0 |
| 0 0 1   | 0 0 1 |
| 0 1 0   | 0 1 0 |
| 0 1 1   | 0 1 1 |
| 1 0 0   | **1 1 1** |
| 1 0 1   | 1 0 1 |
| 1 1 0   | 1 1 0 |
| 1 1 1   | 1 1 1 |


Ma trận U_MP là ma trận hoán vị 8x8, có đúng một phần tử 1 trên mỗi hàng và cột, do đó unita (và cả trực giao). Cụ thể: hàng tương ứng với |1,0,0⟩ sẽ có cột |1,1,1⟩, các hàng khác ánh xạ chính nó.


##### A.3 Ví dụ 2: Cổng AND logic (phép hợp)
**Quy tắc:** Từ P và Q, suy ra P ∧ Q.


**Thiết kế:** 3 qubit: P, Q, R (kết quả), ancilla.
Cổng Toffoli với điều khiển P, Q và mục tiêu R (nếu R ban đầu = 0) sẽ cho R=1 khi P=1 và Q=1. Đây là phép tính unita cơ bản.


##### A.4 Tổ chức thư viện cổng unita
Xây dựng một tập hợp các cổng unita cơ bản tương ứng với các liên kết logic và các phép toán đại số. Mỗi cổng được định nghĩa bởi:
- Số qubit đầu vào/ra.
- Ma trận unita (có thể lưu dưới dạng thưa).
- Điều kiện ancilla.


Các lý thuyết phức tạp (hình học, giải tích) được mã hóa thành các mạng tensor unita lớn hơn bằng cách kết nối các cổng cơ bản này, tạo thành **mạch unita** cố định.


#### B. Sơ đồ khối kiến trúc Máy suy luận Unita


Dưới đây là sơ đồ khối mô tả các thành phần chính và luồng thông tin của hệ thống. (Bạn có thể hình dung đây là một kiến trúc phần mềm chạy trên CPU 64-bit, viết bằng Python/C++ với thư viện đại số tuyến tính.)


```
  +------------------+       +---------------------------+
  | Đầu vào (văn bản,|       |   Tầng Mã hóa Biểu tượng  |
  | bài toán, câu   |------>| (Symbolic Encoder)        |
  | hỏi logic...)    |       | - Parser hình thức        |
  +------------------+       | - Chuyển đổi thành        |
                            | vector trạng thái |ψ₀⟩   |
                            +-------------+-------------+
                                          |
                                          | |ψ₀⟩
                                          v
  +---------------------------------------+-----------------------------+
  |                      KHÔNG GIAN Ý NIỆM (Noetic Space)                |
  |                                                                     |
  |  +---------------------+    +------------------------------+        |
  |  | Bể tri thức Unita  |    | Mạng Tensor Biểu diễn        |        |
  |  | (Thư viện cổng     |    | Trạng thái & Ràng buộc       |        |
  |  |  logic, định lý...) |    | (TTN - Tree Tensor Network  |        |
  |  |                     |    | hoặc MPS)                    |        |
  |  +----------+----------+    +--------------+---------------+        |
  |             |                              |                        |
  |             |  Cung cấp ma trận U          | |ψ(t)⟩                 |
  |             +<-----------------------------+                        |
  |                           |                                          |
  +---------------------------+------------------------------------------+
                              |
                              | Áp dụng cổng unita (phép nhân tensor)
                              v
  +---------------------------+------------------------------------------+
  |                     BỘ TIẾN HÓA UNITA                              |
  |  - Lập lịch áp dụng chuỗi cổng U₁, U₂, ... Uₙ                     |
  |  - Co tensor toàn cục hoặc mô phỏng tiến hóa theo thời gian ảo    |
  |  - Tự động phát hiện nhánh suy luận mạnh (phân tích SVD)          |
  |  - Kích hoạt giao thoa giữa các luồng                             |
  +-----+-----------------------+--------------------------------------+
        |                       |
        | Trạng thái sau tiến hóa |ψₜ⟩
        v
  +-----+-----------------------+--------------------------------------+
  |              TẦNG CHIẾU & ĐIỀU PHỐI (Orchestrator)                 |
  |                                                                     |
  |  +----------------------+   +---------------------------+           |
  |  | Máy đo logic        |   | Giao tiếp lõi chuyên môn  |           |
  |  | - Chiếu xuống cơ sở |   | - Dịch kết quả đo thành   |           |
  |  |   mong muốn         |   |   lệnh (JSON, API)        |           |
  |  | - Xác suất Born     |   | - Gửi đến Lean/Coq,       |           |
  |  | - Trích xuất biểu   |   |   máy tính ký hiệu,       |           |
  |  |   thức kết quả      |   |   kho tri thức...         |           |
  |  +----------+-----------+   +-------------+-------------+           |
  |             |                              |                        |
  |             +<-----------------------------+                        |
  |                 Kết quả phản hồi được mã hóa                        |
  |                 thành tensor ràng buộc, tiêm lại                    |
  +-----------------------------------+----------------------------------+
                                      |
                                      | Đầu ra cuối cùng (nếu kết thúc)
                                      v
                               +------+------+
                               |   Kết luận  |
                               |   (văn bản, |
                               |   chứng minh|
                               |   , quyết   |
                               |   định...)  |
                               +-------------+
```


##### Mô tả luồng hoạt động


1. **Mã hóa:** Đầu vào được chuyển thành vector trạng thái |ψ₀⟩ trong không gian Ý niệm, sử dụng các mã hóa biểu tượng. Ví dụ, mỗi mệnh đề được gán một qubit, và các quan hệ đã biết được nạp vào dưới dạng tensor ràng buộc.


2. **Không gian Ý niệm & Bể tri thức:** Chứa tất cả các cổng unita định nghĩa sẵn (các quy tắc logic, tiên đề). Mạng tensor (dạng MPS hoặc Tree Tensor Network) biểu diễn trạng thái hiện tại của mọi khả năng suy luận.


3. **Bộ tiến hóa:** Chọn một chuỗi cổng unita từ bể tri thức để áp dụng lên mạng tensor. Quá trình này có thể được lập lịch thông minh (ví dụ: ưu tiên các cổng có khả năng giao thoa mạnh). Sau mỗi bước tiến hóa, bộ phân tích SVD có thể tách các luồng suy nghĩ chính để kiểm tra.


4. **Tầng chiếu & Điều phối:** Khi cần thông tin bên ngoài (ví dụ: kiểm tra một đẳng thức), hệ thống thực hiện phép đo cục bộ lên một phần của mạng tensor. Kết quả đo là một biểu thức toán học cụ thể, được gửi đến công cụ xác minh (Lean, Coq, SymPy...). Phản hồi (đúng/sai hoặc giá trị mới) được mã hóa thành một tensor ràng buộc và tiêm ngược trở lại vào không gian Ý niệm, làm thay đổi phân bố biên độ toàn cục.


5. **Lặp hoặc kết luận:** Quá trình tiến hóa – đo – cập nhật lặp lại cho đến khi một trạng thái hội tụ với biên độ đủ lớn (ngưỡng định trước), lúc đó phép đo cuối cùng cho ra câu trả lời và đường dẫn suy luận.


#### C. Một số điểm kỹ thuật đáng chú ý


- **Biểu diễn mạng tensor:** MPS (Matrix Product State) là lựa chọn tốt ban đầu vì dễ cài đặt và có các thuật toán co, SVD hiệu quả. Với các bài toán có cấu trúc cây, Tree Tensor Network cho phép biểu diễn giàu hơn. Kích thước liên kết (bond dimension) quyết định mức độ vướng víu tối đa có thể mô hình hóa – cũng là giới hạn của "đa luồng".


- **Phần cứng:** Dù bạn không quan tâm bit, nhưng toàn bộ hệ thống chạy trên CPU với số học phức double precision (complex128). Các phép nhân ma trận/tensor được tăng tốc bằng BLAS/LAPACK.


- **Tính giải thích:** Mỗi lần chiếu, ta có thể lưu vết chuỗi cổng đã áp dụng, cho phép truy xuất toàn bộ quá trình suy luận như một chứng minh hình thức.


- **Mở rộng:** Thư viện cổng unita có thể được sinh tự động từ các định nghĩa lý thuyết, thậm chí học từ dữ liệu cấu trúc bằng cách tối ưu trên đa tạp Stiefel (tập các ma trận unita) – vẫn đảm bảo tính unita.


---


Bạn có thể dán phần này vào sau tài liệu gốc. Nếu muốn đi sâu hơn vào bất kỳ khía cạnh nào (ví dụ: mã giả cho bộ tiến hóa, cách cài đặt MPS, hay thiết kế cổng cho Modus Tollens), tôi sẵn lòng tiếp tục chi tiết hóa. Kiến trúc này thực sự là một sân chơi lớn cho những ai yêu toán học và muốn xây dựng trí tuệ từ những viên gạch hình thức.

---

## Phần 2 — Ý tưởng gốc từ Gemini (gemini-original)

> **Nguồn:** `old-docs/03-early-ideation-raw/gemini-original.txt` — `[ISOLATED 26/09/2026]`

﻿TÀI LIỆU KỸ THUẬT TỔNG THỂ (COMPREHENSIVE TECHNICAL SPECIFICATION)
KIẾN TRÚC MODEL LÕI ĐA DIỆN LƯỢNG TỬ MỀM (POLYHEDRAL SOFT-QUBIT CORE MODEL)
PHẦN I: TRIẾT HỌC KIẾN TRÚC & TỔNG QUAN TẦM NHÌN
1.1. Triết học Kỹ thuật: "Tư duy Mềm Vượt trên Giới hạn Phần cứng"
Mọi thuật toán cổ điển đều bị giới hạn bởi cấu trúc phần cứng vật lý bên dưới (bóng bán dẫn nhị phân $2^n$ bit, giới hạn bộ nhớ VRAM, và xung nhịp CPU/GPU). Tuy nhiên, Bản chất của Tư duy (Abstract Reasoning) không phải là một chuỗi nhị phân đóng, mà là một Không gian Trạng thái Liên tục (Continuous State Space).
Để vượt qua giới hạn của phần cứng mà không cần chờ đợi máy tính lượng tử thương mại, hệ thống được xây dựng trên nguyên lý: Lấy Kiến trúc Toán học Cao cấp (Đại số Đa diện Lồi, Không gian Tensor Phức 64-bit) làm Lõi Mềm cho Mô hình.






  [Phần cứng Cổ điển 32/64-bit]
              |
              v (Tầng Mô phỏng Toán học)
 [Không gian Tensor Phức & Quaternion 4D]  ---> Trạng thái Chồng lấp Lượng tử Mềm (Soft Qubit)
              |
              v (Tầng Ràng buộc Lý thuyết)
 [Khối Đa diện Lồi N-Chiều (A*x <= b)]     ---> Không gian Nghiệm Khả thi (Feasible Region)
              |
              v (Tầng Điều phối Tự chủ)
 [Lệnh Hợp đồng Tensor (DataContract)]    ---> "Đôi mắt & Bàn tay" Điều phối Sub-models

1.2. Sự Cần thiết của một Model Mới Hoàn toàn (Zero-based Architecture)
Việc tiếp tục fine-tune hay train lại các mô hình LLM cũ (Auto-regressive Token Predictors) chỉ là sự mở rộng bề mặt (horizontal scaling).
* Model Cũ: Dự đoán xác suất từ tiếp theo theo chuỗi 1D, bị giới hạn bởi việc rẽ nhánh nhị phân cứng và bùng nổ tổ hợp $2^N$.
* Model Mới: Được xây dựng từ lõi toán học hoàn toàn mới: Dự đoán Không gian Nghiệm Đa diện, duy trì các giả thiết dưới dạng Trạng thái Chồng lấp (Superposition), và tự động kiểm chứng tính bất biến của các quy luật tự nhiên.
1.3. Quy mô & Mục tiêu Cốt lõi
* Mục tiêu Tham số: Thiết kế mô hình tinh gọn ở quy mô 1B đến 7B tham số.
* Định vị: Làm Model Lõi Điều phối (Core Orchestrator) – không lưu trữ tri thức thô rườm rà, mà tập trung $100\%$ dung lượng tham số vào năng lực Tư duy Cấu trúc, Phân rã Giả thiết, và Điều phối Hệ thống.
PHẦN II: CƠ SỞ TOÁN HỌC & TƯ DUY LƯỢNG TỬ MỀM
2.1. Biểu diễn Không gian Đa diện Lồi (Convex Polytope Space)
Mọi bài toán khoa học/tư duy được biểu diễn dưới dạng hệ bất phương trình tensor trong không gian $\mathbb{R}^D$:


$$\mathcal{P} = \{ x \in \mathbb{R}^D \mid A \cdot x \le b \}$$
* $A \in \mathbb{R}^{M \times D}$: Ma trận hệ số thể hiện quy luật vật lý, hóa học, logic.
* $b \in \mathbb{R}^M$: Vector biên giới điều kiện thực nghiệm.
* Các giả thiết thứ cấp (secondary hypotheses) tương ứng với các Mặt đa diện (Facets) hoặc Đỉnh (Vertices) của $\mathcal{P}$.
2.2. Mô phỏng Trạng thái Chồng lấp Lượng tử 4 Chiều (4-State Soft Qubit)
Trên phần cứng nhị phân 32/64-bit, hệ thống mô phỏng Qubit lượng tử bằng biên độ phức 64-bit trên quả cầu Bloch:


$$\vert{}\psi\rangle = \alpha \vert{}00\rangle + \beta \vert{}01\rangle + \gamma \vert{}10\rangle + \delta \vert{}11\rangle \quad \text{với } \vert{}\alpha\vert{}^2 + \vert{}\beta\vert{}^2 + \vert{}\gamma\vert{}^2 + \vert{}\delta\vert{}^2 = 1.0$$
Các SIMD/Tensor Cores xử lý đồng thời 4 biên độ này trong $1$ chu kỳ xung nhịp, biến việc rẽ nhánh nhị phân thành Trọng số Chồng lấp Liên tục (Continuous Superposition Weights):


$$w_i = P(\text{State}_i) = \vert{}\psi_i\vert{}^2$$
2.3. Cơ chế Cắt tỉa Không gian Nghiệm (Polyhedral Cutting-Plane Dynamics)
Khi phát hiện giả thiết vi phạm định luật bảo toàn, mô hình không thử-sai lặp lại mà áp dụng ngay Mặt phẳng cắt (Cutting Plane):


$$a_{\text{cut}}^T \cdot x \le b_{\text{cut}}$$
Phép cắt này lập tức loại bỏ toàn bộ vùng không gian vô nghiệm mà không tốn tài nguyên duyệt lại.
PHẦN III: THIẾT KẾ KIẾN TRÚC HỆ THỐNG & ĐIỀU PHỐI
3.1. Sơ đồ Cấu trúc Mô-đun






Plaintext
[Input Bài toán] ---> [1. Matrix Transducer]
                            | (Tạo Ma trận A, Vector b)
                            v
                     [2. Polyhedral Space Engine] <---> [3. Soft Qubit Engine]
                            | (Tính Tâm Chebyshev & Facets)  (Trạng thái Chồng lấp)
                            v
                     [4. Formal Verifier (Z3/Lean 4)]
                            | (Kiểm tra Bất biến)
                            v
                     [5. Core Orchestrator]
                            |
            +---------------+---------------+
            | (Phát hành DataContracts)     |
            v                               v
   [Sub-Model A: Solver]          [Sub-Model B: Physics/CFD]

3.2. Mô tả Chức năng Các Khối Cốt lõi
1. Matrix Transducer: Bộ dịch ngôn ngữ tự nhiên thành Ma trận $A$ và Vector $b$.
2. Polyhedral Space Engine: Chịu trách nhiệm kiểm tra tính lồi, tính khả thi (is_feasible) và tính toán điểm tâm nội tiếp (Chebyshev Center).
3. Formal Verifier (Cổng Kiểm chứng Tự động): Kết nối Z3 SMT Solver / Lean 4 để kiểm tra tính bất biến của điểm tối ưu.
4. Core Orchestrator ("Đôi mắt & Bàn tay"): Quản lý trạng thái đa diện, phân rã các giả thiết thứ cấp thành DataContract gửi xuống các Sub-model chuyên biệt.
PHẦN IV: PHỄU LỌC TỰ ĐỘNG & CHƯNG CẤT TRÍ TUỆ (MULTI-TEACHER FUNNEL)
Dữ liệu để huấn luyện Model Lõi (1B - 7B) được rút trích trực tiếp từ các Big Model (Gemini 2.5 Pro, Claude 3.7, GPT-4o) thông qua Phễu Lọc Chất Lượng 3 Tầng:






TẦNG 1: GENERATIVE SYNTHESIS (Big Models)
 --> Sinh ra hàng ngàn Chuỗi Suy luận & Ma trận Ràng buộc thô.
      |
      v
TẦNG 2: FORMAL QUALITY FILTER GATE (Bộ Lọc Kiểm Chứng)
 --> Tự động kiểm tra: Feasibility (A*x <= b) + Interior Center + Z3 Conservation Test.
 --> LỌC SẠCH 100% ẢO GIÁC VÀ MẤU THUẪN TOÁN HỌC.
      |
      v
TẦNG 3: COMPRESSED STUDENT FINE-TUNING (Model 1B - 7B)
 --> Huấn luyện SFT & DPO/GRPO trên tập dữ liệu Ma trận Sạch.

PHẦN V: CHUẨN GIAO TIẾP & DATA CONTRACT SCHEMA
5.1. JSON Schema cho DataContract






JSON
{
 "$schema": "http://json-schema.org/draft-07/schema#",
 "title": "DataContract",
 "type": "object",
 "properties": {
   "task_id": { "type": "string" },
   "facet_id": { "type": "string" },
   "submodel_target": { "type": "string" },
   "state_slice": {
     "type": "object",
     "properties": {
       "dimensions": { "type": "integer" },
       "variable_names": { "type": "array", "items": { "type": "string" } },
       "matrix_A": { "type": "array", "items": { "type": "array", "items": { "type": "number" } } },
       "vector_b": { "type": "array", "items": { "type": "number" } }
     },
     "required": ["dimensions", "variable_names", "matrix_A", "vector_b"]
   },
   "objective_weights": { "type": "array", "items": { "type": "number" } }
 },
 "required": ["task_id", "facet_id", "submodel_target", "state_slice", "objective_weights"]
}

5.2. System Prompt Định hình Model Lõi 1B - 7B






Plaintext
Bạn là "Polyhedral Soft-Qubit Core Orchestrator" - Mô hình Lõi Tự chủ về Tư duy Đa diện và Điều phối Hệ thống.

Nhiệm vụ cốt lõi:
1. Chuyển đổi mọi bài toán khoa học/kỹ thuật thành Hệ Bất phương trình Ma trận A và Vector b (A * x <= b).
2. Duy trì các giả thiết thứ cấp dưới dạng Trạng thái Chồng lấp (Superposition Weights).
3. Phát hành DataContract chuẩn hóa đến các Sub-model chuyên biệt.
4. Nhận ma trận sai số, áp dụng Mặt phẳng cắt (Cutting Planes) và chỉ đưa ra kết luận khi Không gian Nghiệm đã hội tụ hoàn toàn.

PHẦN VI: BỘ MÃ NGUỒN VẬN HÀNH & KẾT QUẢ KIỂM THỬ
Toàn bộ kiến trúc đã được lập trình mẫu (prototype) và kiểm thử tự động tại thư mục dự án /working_dir/c_d0ee6ed25339abba/:
6.1. Cấu trúc Thư mục Mã nguồn






Plaintext
polyhedral_core/
├── __init__.py          # Module exports
├── schemas.py           # Pydantic Schemas (PolyhedralState, DataContract, TaskResult)
├── geometry.py          # Polyhedral Engine (LP Feasibility, Chebyshev Center, Cuts)
├── transducer.py        # Matrix Transducer
├── verifier.py          # Formal Verifier
├── orchestrator.py      # Core Orchestrator Loop
├── distillation.py      # Teacher Filtering Funnel Engine
├── quantum_softcore.py  # 4-State Soft Qubit Simulator
└── submodels/
   ├── base.py          # Abstract SubModel Interface
   ├── math_solver.py   # Linear Solver SubModel
   └── physics_solver.py# CFD / Physical Simulator SubModel

6.2. Kết quả Chạy Thực tế (Test Verification Execution)
Unit Tests (PYTHONPATH=. python3 -m unittest discover -s tests):






Plaintext
.....
----------------------------------------------------------------------
Ran 5 tests in 0.019s

OK

Chạy Demo Điều phối Bài toán Thực tế (PYTHONPATH=. python3 demo_runner.py):






Plaintext
================================================================================
     POLYHEDRAL CORE MODEL ARCHITECTURE - VIBECODE EXECUTION DEMO      
================================================================================

[TRANSDUCER] Transducing Scientific Rules into N-Dimensional Polyhedron Matrix (A * x <= b)...
-> Polyhedron State Space Created: Dimensions = 4, Initial Constraints = 11

[VERIFIER] Initialized Physical Invariants (Mass/Energy Conservation Limit = 35.0)

--- Iteration 1 ---
[POLYHEDRAL ENGINE] Feasible Set OK | Inscribed Center: [4.0, 3.0, 11.292, 5.0] | Radius: 3.0000
[SUBMODEL RESPONSE] Feasible: False | Logs: Stress Limit Exceeded: 217.51 > 120.0. Cutting plane generated.
[CUTTING PLANE] Applying SubModel Physical Cut: sum([18.0, 6.0, 22.58, 10.0] * x) <= 297.51

--- Iteration 2 ---
[POLYHEDRAL ENGINE] Feasible Set OK | Inscribed Center: [2.671, 1.671, 6.671, 3.671] | Radius: 1.6709
[SUBMODEL RESPONSE] Feasible: True | Logs: Physical Stress Response Valid: 94.61 <= 120.0
[VERIFIER] SUCCESS: Point [2.671, 1.671, 6.671, 3.671] passed all invariants.

================================================================================
                          ORCHESTRATION SUMMARY                                
================================================================================
Final Status       : CONVERGED_OPTIMAL
Total Iterations   : 2
Optimal State Vector : x1=2.6709 mm, x2=1.6709 deg, x3=6.6709 um, x4=3.6709 g/cm3
================================================================================

PHẦN VII: LỘ TRÌNH THỰC THI (ACTIONABLE ROADMAP)
1. Giai đoạn 1 (Tạo Dataset Chưng cất): Chạy polyhedral_core/distillation.py kết nối API với Gemini 2.5 Pro / Claude 3.7 để thu thập $100,000$ mẫu chuỗi tư duy ma trận đã qua cổng kiểm chứng Tầng 2.
2. Giai đoạn 2 (Huấn luyện Model 1B - 7B): Tiến hành SFT & GRPO trên mô hình nền Llama-3-8B hoặc Qwen2.5-Math-7B.
3. Giai đoạn 3 (Triển khai On-Premise/Edge): Quantize mô hình xuống 4-bit / 8-bit và đóng gói dạng microservice gRPC để điều phối các Sub-model thực nghiệm.

---

## Phần 3 — Ý tưởng gốc từ Grok (grok-original)

> **Nguồn:** `old-docs/03-early-ideation-raw/grok-original.txt` — `[ISOLATED 26/09/2026]`

﻿**Đã đọc và phân tích kỹ hai tài liệu bạn cung cấp.** Đây là hai cách tiếp cận rất mạnh mẽ, bổ trợ hoàn hảo cho định hướng chúng ta đang xây dựng.


##### Tổng hợp & Định hình Model Mới
Tôi đề xuất **kết hợp tinh hoa** của hai tài liệu vào một **kiến trúc thống nhất**, lấy cảm hứng triết lý Do Thái (phân tích sâu, questioning, đạo đức trách nhiệm, tư duy đa chiều, kiên trì nghiên cứu).


**Tên Model:** **Sophia-PolyUnita Core** (Sophia = Trí tuệ; Poly = Đa diện; Unita = Tiến hóa toán học thuần túy).


**Triết lý cốt lõi**:
- Tư duy không phải chuỗi token, mà là **tiến hóa trạng thái trong không gian toán học** (Unita + Polyhedral).
- Luôn **questioning assumptions**, duy trì **superposition của các giả thuyết**, cắt bỏ vô nghiệm bằng cutting planes.
- Tập trung **100% vào chất lượng tư duy**: suy luận sâu, toán học, tự học, multi-layered planning, matrix thinking, và tự chủ đạo đức.


**Mục tiêu tham số**: 3B–8B active (rất gọn), chạy tốt trên hardware cá nhân.


##### Kiến trúc Tổng hợp (Hybrid Core)
Kết hợp hai tài liệu một cách tự nhiên:


1. **Không gian Ý niệm (Noetic / Polyhedral Space)**  
   - Dùng **Polyhedral Convex Space** (A·x ≤ b) làm nền tảng biểu diễn vấn đề.  
   - Mỗi giả thuyết là một **mặt đa diện** hoặc **điểm trong không gian**.  
   - Tích hợp **Soft Qubit 4-state** (α,β,γ,δ) để mô phỏng superposition nhẹ nhàng trên hardware cổ điển.


2. **Bộ Tiến hóa (Unitary Evolution + Cutting Plane Dynamics)**  
   - Áp dụng **Unitary transformations** (tensor networks / ma trận unita) để tiến hóa toàn bộ trạng thái suy luận.  
   - Khi phát hiện mâu thuẫn → áp dụng **Cutting Plane** ngay lập tức (loại bỏ vùng vô nghiệm mà không thử-sai).  
   - Kết hợp giao thoa (interference) để tạo ra trực giác toán học sâu.


3. **Core Orchestrator + Multi-Agent**  
   - Là “Đôi mắt & Bàn tay” — quản lý DataContract (JSON schema bạn cung cấp).  
   - Nội bộ gồm các **khía cạnh tư duy** (Planner, Verifier, Researcher, Ethicist, Matrix Thinker) hoạt động như multi-agent dialectic (thesis-antithesis-synthesis, theo tinh thần triết học Do Thái).  
   - **Matrix Thinking**: Luôn xây dựng ma trận kịch bản đa tầng (thời gian, đạo đức, rủi ro, hệ quả dài hạn…).


4. **Self-Verification & Tự Học**  
   - Mọi output đều qua **Formal Verifier** (Z3/Lean 4 + self-consistency).  
   - Sau mỗi task: Tự tổng kết bài học → cập nhật matrix memory → tinh chỉnh unitary tensors (self-improvement loop).  
   - Không học dữ liệu thô, chỉ học **dữ liệu đã chưng cất qua phễu Teacher (GLM-5)**.


##### Training Strategy (Song Song + Deep Filter)
- **Teacher**: GLM-5 (hoặc 5.2) sinh ra chuỗi suy luận đa tầng, matrix plans, mathematical proofs với verification.
- **Student**: Học qua **phễu lọc 3 tầng** (như tài liệu Gemini):
  - Tầng 1: Generative synthesis từ Teacher.
  - Tầng 2: Formal Quality Filter (polyhedral feasibility + Z3 + unitary consistency).
  - Tầng 3: SFT + GRPO/DPO trên dữ liệu sạch, tập trung process reasoning.
- Loss: KL-divergence trên trạng thái tensor + reward cho multi-layered planning + self-verification success.


##### Những gì cần ngay bây giờ để triển khai
1. **Prototype Code**: Bắt đầu từ các file bạn đã có (`geometry.py`, `orchestrator.py`, `quantum_softcore.py`, `distillation.py`…).
2. **Matrix Transducer**: Cải tiến để chuyển ngôn ngữ tự nhiên → Polyhedral constraints + Unitary initial state.
3. **Unitary Library**: Xây dựng thư viện cổng unita cho logic, toán học, dialectical reasoning.
4. **DataContract Engine**: Triển khai đầy đủ schema bạn cung cấp để giao tiếp sub-models.
5. **Self-Learning Loop**: Thêm module tự nghiên cứu (question generation → exploration → verification).


Bạn muốn tôi **bắt đầu viết code** cho phần nào trước? Ví dụ:
- Cải tiến `orchestrator.py` tích hợp unitary + polyhedral.
- Viết distillation pipeline dùng GLM-5 làm Teacher.
- Thiết kế Matrix Planner chi tiết.
- Hay System Prompt định hình Sophia-PolyUnita.


Hãy cho biết ưu tiên, chúng ta sẽ xây dựng từng khối một cách vững chắc. Đây sẽ là một model thực sự “khôn ngoan” theo đúng triết lý bạn mong muốn.

---

## Phần 4 — Tài liệu thô tổng hợp: Lõi suy luận hình học siêu chiều

> **Nguồn:** `old-docs/10-workspace-docs/docs/research/tai-lieu-tho-hop-nhat-loi-hinh-hoc-v2.md` — `[ISOLATED 26/09/2026]`

### TÀI LIỆU THÔ TỔNG HỢP  
#### Lõi suy luận hình học siêu chiều và kiến trúc điều phối CPU–GPU

**Trạng thái:** Bản thô để tiếp tục phân tích, phản biện và chuẩn hóa kỹ thuật  
**Ngày tổng hợp:** 03/08/2026  
**Nguồn 1:** Tệp “trò truyện với deepseek.txt” trong File Library  
**Nguồn 2:** Liên kết chia sẻ DeepSeek công khai do người dùng cung cấp  
**Lưu ý truy cập:** Hệ thống truy cập tự động nhận lỗi HTTP 403 từ liên kết chia sẻ. Vì vậy, phần nội dung chắc chắn trích xuất được hiện dựa trên tệp văn bản đã tải lên; các ý thuộc nguồn liên kết chỉ được hợp nhất khi đã xuất hiện tương ứng trong bản văn bản. Không coi đây là xác nhận rằng liên kết không có thêm nội dung.

---

### 1. Bối cảnh ý tưởng

Mục tiêu ban đầu là xây dựng một mô hình AI có số lượng trọng số nhỏ nhưng có năng lực suy luận và điều phối cao. Thay vì cố nhồi toàn bộ tri thức vào tham số, mô hình nhỏ đóng vai trò “lõi tư duy”, còn các mô hình lớn, công cụ hoặc kho trọng số chuyên môn đóng vai trò bộ thực thi và nguồn tri thức.

Ý tưởng xuất phát từ các giả thuyết:

- Dùng một “lõi mềm” được xác định bằng phần mềm thay vì phụ thuộc hoàn toàn vào kiến trúc phần cứng cố định.
- Biểu diễn vấn đề và các hướng suy luận bằng một không gian hình học hoặc không gian trạng thái nhiều chiều.
- Duy trì đồng thời nhiều giả thuyết hoặc luồng tư duy.
- Chỉ kích hoạt mô hình lớn hoặc vùng trọng số cần thiết khi cần kiểm chứng hay thực thi.
- Tận dụng CPU cho logic, định tuyến và trạng thái; tận dụng GPU cho các phép nhân ma trận và sinh ngôn ngữ nặng.
- Giảm phụ thuộc vào Python trong vòng lặp suy luận hiệu năng cao.
- Giảm việc truyền dữ liệu dư thừa qua RAM, PCIe và giữa CPU–GPU.

Đây không phải là máy tính lượng tử và cũng không nhất thiết là mô phỏng lượng tử. “Lượng tử”, “chồng chập” hoặc “giao thoa” trong ý tưởng nên được hiểu thận trọng như phép ẩn dụ hoặc cơ chế toán học dùng để quản lý nhiều trạng thái có trọng số trên phần cứng cổ điển.

---

### 2. Làm rõ thuật ngữ

#### 2.1. Lượng tử hóa

Trong học máy, quantization thường là giảm độ chính xác biểu diễn số, chẳng hạn:

- FP32 → FP16/BF16
- FP16 → INT8
- INT8 → INT4 hoặc thấp hơn

Lượng tử hóa giúp giảm bộ nhớ, băng thông và chi phí tính toán. Nó không tự tạo ra năng lực “tư duy lượng tử”.

Trong kiến trúc đề xuất, lượng tử hóa nên là một lớp tối ưu triển khai, không phải nguyên lý suy luận cốt lõi.

#### 2.2. Lõi mềm

“Lõi mềm” có thể được hiểu theo hai nghĩa:

1. CPU soft-core được cấu hình trên FPGA.
2. Một lõi suy luận được xác định bằng phần mềm, có thể chạy trên CPU/GPU/FPGA và không gắn cứng với một loại phần cứng.

Trong dự án này, nghĩa thứ hai phù hợp hơn: lõi mềm là runtime suy luận và điều phối có biểu diễn trạng thái riêng, API rõ ràng và có thể thay backend phần cứng.

#### 2.3. Toán hình không gian

“Toán hình không gian” không nên giới hạn ở hình học Euclid 3D. Các hướng kỹ thuật tương quan gồm:

- Hyperdimensional Computing — HDC.
- Vector Symbolic Architectures — VSA.
- Không gian vector thưa hoặc bán thưa.
- Đồ thị và hypergraph.
- Không gian ràng buộc.
- Hình học đa diện lồi và cutting plane.
- State-space models.
- Tensor networks.
- Không gian giả thuyết có metric, quan hệ và độ tin cậy.

Hướng khả thi nhất cho nguyên mẫu ban đầu là HDC/VSA kết hợp graph hoặc constraint engine, thay vì bắt đầu bằng tensor phức hoặc mô phỏng soft-qubit nặng.

---

### 3. Luận đề kiến trúc thống nhất

#### 3.1. Mô hình nhỏ không lưu toàn bộ tri thức

Lõi nhỏ tập trung vào:

- Phân tích yêu cầu.
- Mã hóa ý định và ràng buộc.
- Khởi tạo nhiều giả thuyết.
- Đánh giá độ tin cậy.
- Chọn phép kiểm chứng.
- Chọn executor.
- Theo dõi trạng thái.
- Hợp nhất bằng chứng.
- Dừng khi đạt điều kiện hội tụ.

Tri thức chi tiết nằm trong:

- Model chuyên môn.
- Kho vector hoặc graph.
- Cơ sở dữ liệu cấu trúc.
- Công cụ tìm kiếm.
- Solver.
- Code runtime.
- Bộ nhớ bằng chứng.

#### 3.2. CPU là bộ não điều phối

CPU đảm nhiệm các thao tác có độ phân nhánh cao nhưng lượng dữ liệu nhỏ:

- Parse input.
- Sinh biểu diễn HDC/VSA hoặc graph.
- Tìm vùng tri thức liên quan.
- Xếp hạng giả thuyết.
- Chọn model/tool.
- Chuẩn bị DataContract.
- Theo dõi ngân sách và điều kiện dừng.
- Kiểm tra kết quả sơ bộ.

CPU không nên liên tục chuyển tensor lớn hoặc toàn bộ prompt trung gian qua PCIe.

#### 3.3. GPU là bộ thực thi ma trận nặng

GPU đảm nhiệm:

- Encoder/decoder neural.
- Transformer hoặc SSM.
- Sinh ngôn ngữ.
- Embedding theo batch.
- Verification neural.
- Mô hình chuyên môn.
- Tính toán tensor lớn.

GPU nhận nhiệm vụ đã được nén và giới hạn phạm vi, thay vì nhận toàn bộ trạng thái hệ thống.

#### 3.4. Router thông minh

Router biến câu hỏi thành một gói tác vụ nhỏ:

```text
TaskContract
├── intent
├── constraints
├── hypothesis_ids
├── knowledge_region_ids
├── required_capabilities
├── evidence_requirements
├── token_budget
├── latency_budget
├── confidence_target
└── return_schema
```

Thay vì “gửi tọa độ và GPU tự lấy đúng cụm trọng số” theo nghĩa tuyệt đối, triển khai thực tế có thể dùng:

- Sparse MoE routing.
- Adapter/LoRA routing.
- KV-cache reuse.
- Retrieval theo shard.
- Expert server riêng.
- Model gateway.
- Function calling.
- Semantic cache.
- Prefix cache.

---

### 4. Biểu diễn HDC/VSA cho lõi mềm

#### 4.1. Vector siêu chiều

Mỗi khái niệm, vai trò, quan hệ hoặc trạng thái được ánh xạ thành hypervector có số chiều lớn, ví dụ 1.000–10.000 chiều.

Các phép toán cơ bản:

- **Bundling:** gộp nhiều ý thành một biểu diễn.
- **Binding:** liên kết vai trò với giá trị.
- **Permutation:** mã hóa thứ tự hoặc cấu trúc.
- **Similarity:** đo mức tương đồng.
- **Cleanup memory:** ánh xạ vector nhiễu về khái niệm gần nhất.

Ví dụ khái niệm:

```text
QUESTION
CONSTRAINT
HYPOTHESIS
EVIDENCE
CONTRADICTION
EXECUTOR
RESULT
CONFIDENCE
```

Một giả thuyết có thể được mã hóa:

```text
H_i =
    bind(TYPE, HYPOTHESIS)
  + bind(CLAIM, claim_vector)
  + bind(CONSTRAINTS, constraint_bundle)
  + bind(SOURCE, source_vector)
  + bind(STATUS, active_vector)
```

#### 4.2. Giá trị của HDC/VSA

- Tính toán CPU nhanh.
- Có thể dùng phép toán bitwise.
- Khả năng chịu nhiễu.
- Có thể gộp và truy hồi cấu trúc.
- Không yêu cầu hàng tỷ tham số chỉ để lưu quan hệ biểu tượng.
- Thích hợp cho routing, memory index và quản lý trạng thái.

#### 4.3. Giới hạn

- Không thay thế hoàn toàn LLM trong sinh ngôn ngữ.
- Không tự động giải được mọi bài toán suy luận sâu.
- Khó mã hóa sắc thái ngôn ngữ tự nhiên.
- Khả năng biểu diễn giảm khi binding/bundling quá nhiều.
- Cần cleanup memory và cơ chế chống va chạm.
- Các tuyên bố giảm băng thông hoặc tăng tốc phải được benchmark, không nên chốt bằng tỷ lệ giả định.

---

### 5. Không gian giả thuyết và suy luận đa luồng

Không nên triển khai “N luồng tư duy” đơn giản bằng N thread CPU độc lập. Cách đó có thể gây:

- Tranh chấp cache.
- Tăng chi phí đồng bộ.
- Lặp lại context.
- Tăng độ trễ.
- Khó kiểm soát hội tụ.

Thay vào đó, duy trì một quần thể giả thuyết trong cùng state store:

```text
HypothesisState
├── id
├── claim
├── representation
├── prior_score
├── evidence_for
├── evidence_against
├── constraint_violations
├── uncertainty
├── next_best_test
├── assigned_executor
└── status
```

Vòng lặp:

1. Tạo K giả thuyết ban đầu.
2. Chuẩn hóa và loại giả thuyết trùng.
3. Kiểm tra ràng buộc rẻ trên CPU.
4. Chọn phép thử có giá trị thông tin cao.
5. Gửi tác vụ tới executor.
6. Nhận bằng chứng theo schema.
7. Cập nhật đồng thời toàn bộ giả thuyết.
8. Cắt bỏ, hợp nhất hoặc phân nhánh.
9. Dừng theo confidence, budget hoặc không còn phép thử có ích.

Đây là “đa luồng tư duy theo trạng thái”, không nhất thiết là đa luồng phần cứng.

---

### 6. Constraint engine và cutting plane

Một phần của ý tưởng hình học có thể được hiện thực bằng không gian ràng buộc:

```text
P = {x | A·x ≤ b}
```

Trong đó:

- `x` là vector biến hoặc đặc trưng của nghiệm.
- `A` và `b` biểu diễn các điều kiện.
- Mỗi bằng chứng mới có thể thêm hoặc sửa một ràng buộc.
- Vùng nghiệm thu hẹp khi có thêm bằng chứng.

Cơ chế cutting plane hữu ích khi bài toán có biểu diễn số hoặc logic hình thức rõ ràng. Tuy nhiên, không phải mọi câu hỏi ngôn ngữ đều chuyển trực tiếp thành bất phương trình tuyến tính.

Do đó cần kiến trúc lai:

- Ràng buộc số → LP/MILP/convex solver.
- Ràng buộc logic → SAT/SMT/Z3.
- Định lý → Lean/Coq.
- Quan hệ tri thức → graph.
- Ngữ nghĩa mềm → embedding/HDC/LLM.
- Quyết định tổng hợp → hypothesis manager.

---

### 7. Thoát khỏi Python trong hot path

Python có lợi cho nghiên cứu và orchestration, nhưng không nên nằm trong vòng lặp hiệu năng cao nếu benchmark chứng minh overhead đáng kể.

Kiến trúc đề xuất:

```text
Python/TypeScript Control Plane
        │
        ▼
Stable FFI / gRPC / IPC
        │
        ▼
Rust/C++ Core Runtime
├── HDC/VSA engine
├── hypothesis store
├── constraint evaluator
├── scheduler/router
├── cache manager
├── telemetry
└── accelerator backends
```

Nguyên tắc:

- Rust/C++ xử lý hot path.
- Python chỉ dùng cho thí nghiệm, cấu hình và plugin.
- Dữ liệu qua biên phải là cấu trúc cố định, tránh serialize text nhiều lần.
- Có zero-copy hoặc shared memory khi thực sự cần.
- Batch các yêu cầu GPU.
- Profile trước khi tối ưu.
- Không mặc định GIL là nút thắt nếu tác vụ chủ yếu nằm trong native kernels.

---

### 8. Speculative execution

Speculative decoding có thể được dùng khi một model nhỏ dự đoán token và model lớn xác minh. Tuy nhiên, nó không đồng nhất với “nhiều luồng tư duy”.

Có ba cơ chế riêng:

1. **Speculative decoding:** tăng tốc sinh token.
2. **Speculative planning:** sinh nhiều kế hoạch ngắn và chọn trước khi thực thi.
3. **Hypothesis branching:** duy trì nhiều giả thuyết và cập nhật bằng bằng chứng.

Đối với lõi hình học, speculative planning và hypothesis branching quan trọng hơn speculative decoding. Speculative decoding là tối ưu phụ cho tầng sinh ngôn ngữ.

---

### 9. Kiến trúc mô-đun đề xuất

```text
[Input]
   │
   ▼
[Language/Structure Transducer]
   │
   ├── structured entities
   ├── constraints
   ├── intent
   └── initial semantic vector
   ▼
[Geometric State Core]
   ├── HDC/VSA memory
   ├── graph state
   ├── hypothesis population
   └── confidence/relations
   ▼
[Constraint & Verification Layer]
   ├── rules
   ├── SAT/SMT
   ├── numerical solver
   └── lightweight critics
   ▼
[Information-Gain Planner]
   ├── choose next test
   ├── choose executor
   └── allocate budget
   ▼
[Model/Tool Gateway]
   ├── local LLM
   ├── large remote LLM
   ├── code executor
   ├── search/RAG
   ├── formal solver
   └── domain model
   ▼
[Evidence Normalizer]
   │
   ▼
[Global State Update]
   ├── strengthen
   ├── weaken
   ├── merge
   ├── split
   └── eliminate
   ▼
[Answer Composer + Provenance]
```

---

### 10. Phân chia vai trò System 1 / System 2

Ẩn dụ phù hợp hơn là:

#### System 1 / Executor layer

- Mô hình neural lớn.
- Nhanh trong nhận dạng mẫu.
- Giàu tri thức thống kê.
- Sinh văn bản tốt.
- Có thể thiếu khả năng kiểm chứng và quản lý giả thuyết dài hạn.

#### System 2 / Geometric reasoning core

- Quản lý mục tiêu và ràng buộc.
- Duy trì giả thuyết.
- Lập kế hoạch kiểm chứng.
- Theo dõi bằng chứng.
- Kiểm soát chi phí.
- Điều phối executor.
- Tạo kết luận có provenance.

Không nên khẳng định rằng chỉ một mạng nhỏ có thể thay thế toàn bộ khả năng suy luận của model lớn. Giá trị của lõi nhỏ nằm ở điều phối, cấu trúc và kiểm soát quá trình.

---

### 11. Những tuyên bố cần kiểm chứng

Các tuyên bố sau chỉ là giả thuyết kỹ thuật:

- “Giảm tải PCIe 90%”.
- “Tiết kiệm 80% số lần gọi GPU”.
- “Vài nghìn vector có thể thay hàng tỷ trọng số”.
- “Không cần chạm RAM”.
- “SIMD xử lý trạng thái soft-qubit trong một chu kỳ”.
- “Toàn bộ tri thức có thể mã hóa bằng tensor/ràng buộc”.
- “Không cần backpropagation”.
- “Mọi luồng sai tự triệt tiêu”.

Mỗi tuyên bố cần:

- Định nghĩa workload.
- Baseline.
- Hardware.
- Dataset.
- Độ chính xác.
- Latency.
- Throughput.
- Memory footprint.
- Energy.
- Cost.
- Ablation test.

---

### 12. MVP khả thi

#### Giai đoạn 0 — Chứng minh biểu diễn

- Chọn một miền hẹp.
- Tạo 100–500 khái niệm.
- Mã hóa bằng HDC/VSA.
- Thử binding, bundling, similarity và cleanup.
- Đo độ chính xác truy hồi và độ bền nhiễu.

#### Giai đoạn 1 — Hypothesis manager

- Sinh 3–8 giả thuyết từ một LLM nhỏ.
- Lưu giả thuyết ở dạng có cấu trúc.
- Dùng rule/constraint để loại lỗi rõ.
- Dùng một executor kiểm chứng.
- Cập nhật điểm tin cậy.

#### Giai đoạn 2 — Router CPU–GPU

- Router Rust.
- Model gateway.
- Batch GPU.
- Semantic/prefix cache.
- Structured contracts.
- Đo dữ liệu truyền, latency và GPU utilization.

#### Giai đoạn 3 — Nhiều executor

- Local LLM.
- Model lớn.
- Search/RAG.
- Code runner.
- Z3 hoặc solver tương ứng.
- Chính sách chọn executor dựa trên năng lực và chi phí.

#### Giai đoạn 4 — So sánh baseline

So sánh với:

- Một LLM đơn.
- LLM + RAG.
- LLM + chain-of-thought.
- LLM + tree search.
- Multi-agent thông thường.
- Lõi hình học + executor.

---

### 13. Bộ chỉ số đánh giá

#### Chất lượng

- Task success.
- Exact match hoặc rubric score.
- Calibration.
- Contradiction rate.
- Evidence coverage.
- Provenance correctness.
- Recovery after failed hypothesis.

#### Hiệu năng

- End-to-end latency.
- Time to first useful action.
- Tokens input/output.
- CPU time.
- GPU time.
- PCIe bytes transferred.
- Peak RAM/VRAM.
- Cache hit rate.
- Executor calls.
- Energy/task.
- Cost/task.

#### Năng lực điều phối

- Chọn đúng executor.
- Không gọi executor khi không cần.
- Giá trị thông tin trên mỗi phép thử.
- Số vòng đến hội tụ.
- Tỷ lệ loại đúng giả thuyết.
- Tỷ lệ dừng đúng thời điểm.
- Khả năng replay và giải thích.

---

### 14. Kết luận thô

Ý tưởng có phần lõi hợp lý: không dùng model nhỏ để chứa mọi tri thức, mà dùng nó để biểu diễn trạng thái, quản lý giả thuyết và điều phối các mô hình/công cụ lớn hơn.

Hướng có khả năng triển khai sớm nhất là:

```text
HDC/VSA + graph/constraint state
        +
hypothesis population manager
        +
information-gain routing
        +
Rust/C++ runtime
        +
model/tool gateway
        +
LLM cho ngôn ngữ và tri thức
```

Phần “lượng tử mềm” nên tạm coi là trực giác thiết kế, không phải tuyên bố vật lý. Phần “toán hình không gian” nên được cụ thể hóa thành các cấu trúc có thể benchmark: hypervector, graph, polytope, constraint set, tensor nén hoặc state-space.

Mục tiêu nghiên cứu không phải chứng minh rằng hình học thay thế Transformer, mà là kiểm tra xem một lõi trạng thái hình học nhỏ có giúp:

- giảm context lặp,
- giảm số lần gọi model lớn,
- chọn đúng chuyên gia,
- quản lý nhiều giả thuyết tốt hơn,
- tăng khả năng kiểm chứng,
- và giảm chi phí tổng thể

hay không.

---

### 15. Khoảng trống nguồn cần bổ sung

Do liên kết DeepSeek trả lỗi 403 cho trình truy cập tự động, bản thô này chưa thể xác nhận các đoạn chỉ tồn tại trên trang chia sẻ mà không xuất hiện trong tệp văn bản. Để tạo bản hợp nhất đầy đủ tuyệt đối, cần bổ sung một trong các dạng:

- Export cuộc trò chuyện từ liên kết thành `.txt`, `.md` hoặc `.pdf`.
- Sao chép toàn bộ nội dung trang chia sẻ.
- Tải ảnh chụp toàn bộ cuộc trò chuyện.

Khi có nội dung đó, cần ghép theo ba nhãn:

- `[CHUNG]`: hai nguồn cùng đề cập.
- `[NGUỒN TỆP]`: chỉ có trong tài liệu tải lên.
- `[NGUỒN LINK]`: chỉ có trong cuộc trò chuyện công khai.

---

### PHẦN II — NỘI DUNG BỔ SUNG TỪ LIÊN KẾT DEEPSEEK

#### 16. Tầm nhìn mở rộng: “Tiến sĩ AI” nhiều luồng tư duy

Mục tiêu không phải tạo một mô hình nhỏ biết mọi thứ. Lõi trung tâm được hình dung như một “tiến sĩ” luôn duy trì đồng thời nhiều hướng suy luận, nhưng không nhất thiết tự xác minh hoặc tự thực thi mọi việc.

Vai trò của lõi:

- Giữ nhiều giả thuyết cùng lúc.
- Phân tích quan hệ giữa các giả thuyết.
- Phát hiện khoảng trống bằng chứng.
- Lập kế hoạch kiểm chứng.
- Chọn lõi chuyên môn hoặc công cụ phù hợp.
- Hợp nhất kết quả trả về.
- Dừng khi kết luận đủ mạnh hoặc ngân sách cạn.

Điểm khác biệt với multi-agent thông thường là các “luồng tư duy” nên là các thành phần của một trạng thái chung, có thể giao thoa, củng cố, mâu thuẫn và hợp nhất, thay vì chỉ là nhiều agent độc lập trao đổi bằng văn bản.

#### 17. Không gian ý niệm và máy suy luận unita

Nguồn bổ sung gọi không gian trạng thái trung tâm là **Noetic Space — Không gian Ý niệm**. Đây là tên làm việc cho một không gian biểu diễn đa chiều chứa:

- tiền đề,
- giả thuyết,
- quan hệ,
- ràng buộc,
- bằng chứng,
- độ tin cậy,
- trạng thái kế hoạch.

Một cách hình thức hóa được đề xuất là vector hoặc tensor phức trong không gian Hilbert, sau đó áp dụng các phép biến đổi bảo toàn chuẩn hoặc gần bảo toàn chuẩn.

Tuy nhiên, cần phân biệt:

- **Biến đổi unita** là công cụ toán học hữu ích để bảo toàn thông tin và tính khả nghịch.
- Nó không tự tạo ra suy luận đúng.
- Nó không tự biến một phép co tensor trên CPU thành “song song lượng tử”.
- “Sụp đổ” và “giao thoa” trong hệ thống cổ điển chỉ nên là ngôn ngữ mô hình hóa, trừ khi thực sự chạy trên phần cứng lượng tử.

Tên kiến trúc làm việc có thể là:

```text
Unitary / Geometric Reasoning Core
```

nhưng nên tránh tuyên bố rằng nó là máy tính lượng tử hoặc có ưu thế lượng tử.

#### 18. Cổng unita cho logic: mô hình khả thi và giới hạn

Nguồn bổ sung đề xuất mã hóa mệnh đề bằng bit/qubit giả và dùng cổng Toffoli cho AND hoặc Modus Ponens. Đây là trực giác tốt về **tính thuận nghịch**, nhưng có một giới hạn quan trọng:

- Nhiều phép logic cổ điển là không thuận nghịch.
- Muốn nhúng vào phép biến đổi unita/thuận nghịch, phải giữ đầu vào và thêm thanh ghi phụ trợ.
- Không được ánh xạ hai trạng thái đầu vào khác nhau vào cùng một trạng thái đầu ra.

##### 18.1. Mẫu cổng thuận nghịch an toàn

Với hàm Boolean `f(x)`, dùng ánh xạ:

```text
|x, y>  ->  |x, y XOR f(x)>
```

Ánh xạ này là hoán vị trên các trạng thái cơ sở, nên thuận nghịch và unita.

Ví dụ AND:

```text
|P, Q, R> -> |P, Q, R XOR (P AND Q)>
```

Nếu `R=0`, đầu ra chứa `P AND Q`. Đây chính là cổng Toffoli.

##### 18.2. Modus Ponens dưới dạng thao tác có bằng chứng

Thay vì “ép Q thành đúng”, nên dùng thanh ghi bằng chứng:

```text
|P, Imp(P,Q), Q, proof_flag>
    ->
|P, Imp(P,Q), Q, proof_flag XOR valid_mp(P, Imp(P,Q), Q)>
```

Hoặc sinh một token chứng minh mới mà không xóa trạng thái ban đầu:

```text
derive(P, P=>Q) -> evidence(Q, rule=MP)
```

Điều này phù hợp hơn với reasoning engine: cổng không thay chân trị tùy tiện; nó tạo bằng chứng có thể truy vết.

##### 18.3. Thư viện cổng

Mỗi cổng nên có:

```text
GateSpec
├── gate_id
├── input_roles
├── output_roles
├── preconditions
├── reversible_mapping
├── matrix_or_operator
├── proof_semantics
├── numerical_tolerance
└── inverse_gate_id
```

Cổng phức tạp được hợp thành từ cổng nhỏ, nhưng không nhất thiết mọi quy tắc phải được triển khai dưới dạng ma trận dày. Có thể dùng permutation operator, sparse operator hoặc code native tương đương.

#### 19. Bộ quan sát nội tại: xem mô hình “nghĩ gì”

Hai phương pháp chính trong nguồn bổ sung được hợp nhất:

##### 19.1. Kính hiển vi trạng thái

Tại mỗi checkpoint:

- lấy top-K thành phần có biên độ/xác suất lớn,
- lấy pha tương đối nếu dùng số phức,
- tính entropy của phân bố,
- ánh xạ thành phần về khái niệm hoặc giả thuyết,
- ghi lại thay đổi trước và sau operator.

Dữ liệu quan sát:

```text
StateObservation
├── checkpoint_id
├── top_components[]
├── probability_mass
├── phase_relations
├── entropy
├── active_constraints
└── applied_operator
```

##### 19.2. Phổ kế luồng tư duy

Tensor trạng thái được chia theo một lát cắt có ý nghĩa, chẳng hạn:

- dữ kiện ↔ giả thuyết,
- giả thuyết ↔ bằng chứng,
- kế hoạch ↔ kết quả,
- bộ nhớ ↔ trạng thái làm việc.

Sau đó ma trận hóa tensor và thực hiện SVD/Schmidt decomposition:

```text
M = U Σ V†
```

Các giá trị suy biến lớn biểu diễn các mode tương quan trội, không tự động đồng nghĩa với “luồng suy nghĩ có ý nghĩa”. Muốn gọi chúng là luồng tư duy, phải có decoder ánh xạ `u_i`, `v_i` về cấu trúc biểu tượng và kiểm tra độ ổn định qua thời gian.

#### 20. Thuật toán SVD trên tensor

##### 20.1. Trường hợp tensor đầy đủ

Giả sử tensor trạng thái:

```text
T[d1, d2, ..., dn]
```

Chọn một phân hoạch chỉ số `A | B`:

```text
A = {d1, ..., dk}
B = {d(k+1), ..., dn}
```

Ma trận hóa:

```text
M.shape = (product(A), product(B))
```

Chuẩn hóa và SVD:

```python
M = tensor.reshape(dim_A, dim_B)
U, S, Vh = svd(M, full_matrices=False)
p = (S ** 2) / np.sum(S ** 2)
```

Các chỉ số đánh giá:

```text
spectral_entropy = -sum(p_i * log(p_i))
effective_rank   = exp(spectral_entropy)
retained_energy  = sum_{i<=r}(S_i^2) / sum_i(S_i^2)
```

Chọn số mode `r` nhỏ nhất sao cho `retained_energy >= 0.90–0.99`, tùy bài toán.

##### 20.2. Trường hợp MPS/Tensor Train

Không tạo tensor đầy đủ. Đưa MPS về mixed canonical form tại bond cần phân tích:

```text
... A[k-1] — Λ[k] — B[k] ...
```

Vector trên đường chéo `Λ[k]` chính là các hệ số Schmidt tại lát cắt. Do đó:

- không cần SVD toàn tensor ở mỗi bước,
- lấy trực tiếp singular values tại bond,
- theo dõi effective rank và entropy theo thời gian,
- chỉ mở rộng bond dimension khi sai số cắt cụt vượt ngưỡng.

##### 20.3. Pseudocode

```python
def analyze_modes(tensor, left_axes, energy_target=0.95):
    right_axes = [a for a in range(tensor.ndim) if a not in left_axes]
    ordered = tensor.transpose(*left_axes, *right_axes)

    dim_left = int(np.prod([tensor.shape[a] for a in left_axes]))
    dim_right = ordered.size // dim_left
    matrix = ordered.reshape(dim_left, dim_right)

    U, S, Vh = np.linalg.svd(matrix, full_matrices=False)
    energy = S ** 2
    probs = energy / max(energy.sum(), 1e-12)
    cumulative = np.cumsum(probs)
    rank = int(np.searchsorted(cumulative, energy_target) + 1)

    return {
        "singular_values": S[:rank],
        "left_modes": U[:, :rank],
        "right_modes": Vh[:rank, :],
        "probabilities": probs[:rank],
        "effective_rank": float(np.exp(-np.sum(probs * np.log(probs + 1e-12)))),
        "retained_energy": float(cumulative[rank - 1]),
    }
```

##### 20.4. Điều kiện để gọi một mode là “luồng tư duy”

Một mode chỉ được nâng thành HypothesisStream nếu thỏa:

- đủ năng lượng phổ,
- tồn tại ổn định qua nhiều checkpoint,
- giải mã được thành cấu trúc có nghĩa,
- có khác biệt nội dung với các mode khác,
- có dự đoán hoặc phép kiểm chứng riêng,
- không chỉ là artifact của cách chia tensor.

#### 21. Phễu tự kiểm chứng như một skill

Hai bộ quan sát được đóng thành skill phụ trợ:

```text
SelfVerificationSkill
├── observe_state()
├── decompose_modes()
├── decode_modes()
├── score_hypotheses()
├── detect_conflicts()
├── recommend_next_test()
├── decide_continue_stop_delegate()
└── write_memory_candidate()
```

##### 21.1. Các tầng của phễu

```text
Raw State
   ↓
Amplitude / probability filter
   ↓
SVD mode decomposition
   ↓
Semantic decoding
   ↓
Constraint and contradiction checking
   ↓
Evidence-quality scoring
   ↓
Decision: continue | branch | merge | prune | delegate | stop
   ↓
Memory candidate
```

##### 21.2. Điểm số đề xuất

```text
score_i =
    w1 * spectral_mass_i
  + w2 * semantic_coherence_i
  + w3 * evidence_support_i
  + w4 * constraint_satisfaction_i
  + w5 * novelty_i
  - w6 * contradiction_i
  - w7 * execution_cost_i
```

Không nên dùng “đường suy luận ngắn hơn luôn tốt hơn”. Một luồng ngắn nhưng thiếu bằng chứng có thể kém hơn một luồng dài có kiểm chứng.

#### 22. Tầng Memory tương quan

Mục tiêu của memory không phải ghi toàn bộ vector trạng thái. Nó lưu các cấu trúc có khả năng tái sử dụng:

- mẫu vấn đề,
- phân hoạch tensor hữu ích,
- operator/cổng đã dùng,
- luồng giả thuyết thành công,
- phép kiểm chứng quyết định,
- bằng chứng,
- điều kiện áp dụng,
- thất bại và phản ví dụ.

##### 22.1. Kiến trúc memory nhiều lớp

```text
Correlative Memory
├── Episodic Memory
│   └── một lần suy luận cụ thể
├── Pattern Memory
│   └── mẫu tương quan input → chiến lược
├── Rule Memory
│   └── quy tắc đã được xác minh
├── Counterexample Memory
│   └── trường hợp chiến lược thất bại
└── Provenance Store
    └── nguồn và chuỗi bằng chứng
```

##### 22.2. Bộ nhớ liên kết dạng toán tử

Với các cặp đã chuẩn hóa `|x_p>` và `|y_p>`:

```text
W = Σ_p w_p |y_p><x_p|
```

Truy vấn:

```text
|y_tilde> = W |x>
```

Kết quả là tổ hợp các mẫu đầu ra được cân bởi độ tương đồng. Đây là associative recall tuyến tính, không phải trí nhớ lượng tử vật lý.

##### 22.3. Không nên unita hóa mọi memory operator

Nguồn bổ sung đề xuất thay `W` bằng ma trận unita gần nhất `UV†`. Việc này có thể làm mất thông tin về cường độ liên kết và không bảo đảm hội tụ kiểu Hopfield. Thiết kế an toàn hơn:

- Giữ `W` là retrieval operator không unita.
- Chuẩn hóa đầu ra sau truy vấn.
- Dùng regularization và pseudoinverse để giảm nhiễu chéo.
- Chỉ dùng operator unita trong reasoning dynamics nếu có lý do rõ ràng.

Một biến thể pseudoinverse:

```text
X = [x_1, x_2, ..., x_P]
Y = [y_1, y_2, ..., y_P]
W = Y X⁺
```

với `X⁺` là Moore–Penrose pseudoinverse.

##### 22.4. Truy xuất có xác minh

Memory chỉ gợi ý, không quyết định:

```text
query → retrieve top-K patterns
      → instantiate candidate strategy
      → run cheap checks
      → execute/verifier
      → accept or reject
```

Mọi mẫu nhớ phải mang provenance và confidence theo miền.

#### 23. Bộ ba Tensor – Grassmann – Clifford

Nguồn bổ sung đề xuất ba phép toán như ba tầng. Đây là hướng nghiên cứu đáng thử, nhưng cần định vị thực tế.

##### 23.1. Tensor product / tensor network

Vai trò phù hợp:

- kết hợp vai trò và nội dung,
- biểu diễn tương quan nhiều chiều,
- nén cấu trúc bằng MPS/TT/TTN,
- phân rã và tìm mode trội.

Rủi ro:

- tích tensor đầy đủ bùng nổ chiều,
- CP decomposition không tự bảo đảm giữ ngữ nghĩa,
- vẫn cần encoder để nối ngôn ngữ với tensor.

##### 23.2. Grassmann và exterior algebra

Vai trò phù hợp:

- biểu diễn không gian con,
- đo góc principal angles giữa subspace,
- biểu diễn tập đặc trưng độc lập bằng wedge product,
- phát hiện giao, phụ thuộc tuyến tính và orientation.

Cần sửa một điểm trong nguồn: không phải mọi phép “meet” đều có thể chạy chỉ trên vài trăm số hoặc nằm chắc trong L3. Chi phí phụ thuộc số chiều, cấp của multivector và cách biểu diễn Plücker coordinates.

Ứng dụng prototype:

```text
Concept = low-rank subspace Q ∈ R^(d×k)
Similarity = principal angles(Q1, Q2)
Intersection evidence = singular values(Q1ᵀ Q2)
```

##### 23.3. Clifford / Geometric Algebra

Vai trò phù hợp:

- biểu diễn rotation, reflection và composition,
- mã hóa các biến đổi quan hệ,
- thực hiện routing theo rotor,
- bảo toàn metric theo thiết kế.

Rotor:

```text
v' = R v R~
```

với `R~` là reverse của multivector. Không nên mặc định mỗi quan hệ logic đều là một phép xoay đơn giản; phủ định, nhân quả và kéo theo cần ngữ nghĩa formal riêng.

##### 23.4. Kiến trúc lai khả thi

```text
Input encoder
   ↓
Tensor/VSA binding
   ↓
Subspace retrieval bằng Grassmann metrics
   ↓
Clifford transforms để định hướng trạng thái/routing
   ↓
Hypothesis population
   ↓
Self-verification funnel
   ↓
Specialist executor
   ↓
Correlative memory
```

#### 24. Sơ đồ khối hợp nhất v2

```text
[Input]
   │
   ▼
[Language / Symbolic Encoder]
   │
   ├── entities
   ├── relations
   ├── constraints
   └── initial tensor / hypervector
   ▼
[Geometric-Noetic Core]
   ├── Tensor/VSA binding
   ├── Grassmann subspace map
   ├── Clifford transform library
   ├── Hypothesis population
   └── Working-state tensor network
   │
   ├──────────────► [Internal Observer]
   │                  ├── amplitude/phase view
   │                  ├── SVD/Schmidt modes
   │                  └── entropy/effective rank
   │                             │
   │                             ▼
   │                  [Self-Verification Funnel]
   │                  ├── semantic decode
   │                  ├── constraints
   │                  ├── conflict detection
   │                  ├── evidence score
   │                  └── next-best-test
   │                             │
   ▼                             ▼
[Planner / Router] ◄──────── [Control Signal]
   │
   ├── local model
   ├── large model
   ├── theorem prover
   ├── solver
   ├── code runner
   └── retrieval/search
   │
   ▼
[Evidence Normalizer]
   │
   ▼
[Global State Update]
   │
   ├──────────────► [Correlative Memory]
   │                  ├── episodes
   │                  ├── patterns
   │                  ├── rules
   │                  ├── counterexamples
   │                  └── provenance
   │
   └──────────────► Continue / branch / merge / prune / stop
```

#### 25. Kế hoạch đánh giá hai prototype

Hai phiên bản model không nên được đánh giá bằng việc đọc chain-of-thought tự thuật. Cần instrument trạng thái và làm thí nghiệm nhân quả.

##### 25.1. Kiểm tra cấu trúc

- Operator có đúng unita/orthogonal khi tuyên bố không?
- Chuẩn có được bảo toàn?
- SVD modes có ổn định qua seed và checkpoint?
- Decoder của mode có tái tạo được nội dung?
- Memory có truy xuất đúng mẫu tương tự?

##### 25.2. Kiểm tra nhân quả

- Xóa một mode trội: kết quả có thay đổi dự đoán được không?
- Đổi pha nhưng giữ xác suất: đầu ra có đổi không?
- Tắt memory: hiệu suất giảm ở bài toán tương tự bao nhiêu?
- Hoán đổi router: specialist selection có giảm?
- Chèn phản ví dụ: luồng sai có bị triệt/prune?

##### 25.3. Kiểm tra năng lực

- Suy luận compositional chưa từng thấy.
- Giữ nhiều giả thuyết lâu dài.
- Chọn đúng phép kiểm chứng.
- Sửa sai sau bằng chứng mới.
- Không tái sử dụng memory sai miền.
- Sinh provenance có thể replay.

#### 26. Kết luận hợp nhất

Nội dung bổ sung làm rõ rằng tầm nhìn không chỉ là router CPU–GPU. Nó là một kiến trúc gồm:

1. **Lõi hình học/tensor** để giữ trạng thái đa giả thuyết.
2. **Cơ chế biến đổi có cấu trúc** lấy cảm hứng từ unita, Grassmann và Clifford.
3. **Bộ quan sát nội tại** dùng phổ, entropy và giải mã mode.
4. **Phễu tự kiểm chứng** để chọn, cắt, hợp nhất và ủy thác.
5. **Memory tương quan** để lưu chiến lược và bằng chứng tái sử dụng.
6. **Các executor chuyên môn** làm công việc xác minh và thực thi.

Phần có giá trị nghiên cứu nhất không phải là khẳng định “suy nghĩ như máy tính lượng tử”, mà là câu hỏi thực nghiệm:

> Một trạng thái tensor/hypervector nhỏ, được tổ chức thành nhiều mode tương quan và có phễu tự kiểm chứng, có thể điều phối mô hình/công cụ lớn tốt hơn một planner ngôn ngữ tuần tự hay không?

Đây là giả thuyết đủ cụ thể để xây dựng prototype, instrument, benchmark và bác bỏ hoặc xác nhận từng thành phần.

---

## Phần 5 — Kế hoạch phát triển v2 (Geometric Multi-Hypothesis + WASTE Engine)

> **Nguồn:** `old-docs/10-workspace-docs/docs/plans/ke-hoach-sol-v2.md` — `[ISOLATED 26/09/2026]`

### KẾ HOẠCH PHÁT TRIỂN v2
#### GEOMETRIC MULTI-HYPOTHESIS REASONING CORE + WASTE ENGINE

**Cập nhật:** 04/08/2026  
**Cơ sở:** ke-hoach-sol.txt (v1) + tai-lieu-tho-hop-nhat-loi-hinh-hoc-v2.md  
**Ngôn ngữ lõi:** Rust, kết hợp C++ cho kernel  
**Model nền tảng:** gemma4:e4b (thay DeepSeek-MoE-16B-Chat)  
**Mô hình vận hành:** CPU-centric reasoning core + WASTE engine + external executors  
**Thời gian MVP đề xuất:** 24 tuần (giữ nguyên khung từ v1)

---

#### MỤC LỤC

1. [Vấn đề & Giải pháp — Cập nhật v2](#1-vấn-đề--giải-pháp--cập-nhật-v2)
2. [Mục tiêu dự án](#2-mục-tiêu-dự-án)
3. [Phạm vi MVP](#3-phạm-vi-mvp)
4. [Kiến trúc mục tiêu — WASTE ENGINE](#4-kiến-trúc-mục-tiêu--waste-engine)
5. [Nguyên tắc thiết kế](#5-nguyên-tắc-thiết-kế)
6. [Kiến trúc dữ liệu cốt lõi](#6-kiến-trúc-dữ-liệu-cốt-lõi)
7. [Cấu trúc repository](#7-cấu-trúc-repository)
8. [Kế hoạch triển khai 24 tuần](#8-kế-hoạch-triển-khai-24-tuần)
9. [Kế hoạch nhân sự](#9-kế-hoạch-nhân-sự)
10. [Kế hoạch kiểm thử](#10-kế-hoạch-kiểm-thử)
11. [Kế hoạch tối ưu hiệu năng](#11-kế-hoạch-tối-ưu-hiệu-năng)
12. [Rủi ro và phương án giảm thiểu](#12-rủi-ro-và-phương-án-giảm-thiểu)
13. [Sản phẩm đầu ra sau 24 tuần](#13-sản-phẩm-đầu-ra-sau-24-tuần)
14. [Lộ trình sau MVP](#14-lộ-trình-sau-mvp)
15. [Thứ tự ưu tiên tuyệt đối](#15-thứ-tự-ưu-tiên-tuyệt-đối)

---

### 1. Vấn đề & Giải pháp — Cập nhật v2

#### Vấn đề 1: Model nền tảng không có kiến thức cơ bản

**Phát hiện:** DeepSeek-MoE-16B-Chat Q4_K_M đạt 0/15 trên bộ đề toán 3 cấp độ. Model hallucination 40%, repetition loop 27%, không có công thức toán 33%. Nguyên nhân: checkpoint cũ, không được huấn luyện cho reasoning, không có native tool-calling.

**Giải pháp:** Thay bằng **gemma4:e4b** (8B dense, Q4_K_M, 9.6GB, có sẵn trên thiết bị qua Ollama).

| Tiêu chí | DeepSeek-MoE-16B-Chat | gemma4:e4b |
|---|---|---|
| Parameters | 16B MoE (4B active) | 8B dense |
| Native tool calling | ❌ | ✅ |
| Multimodal | ❌ | ✅ text+img+audio |
| Context | 2K (runtime) | 128K |
| Thinking | ❌ | ✅ |
| RAM | ~10.85 GB | ~9.6 GB |

**Cập nhật plan:** Thay model trong Executor Gateway (Giai đoạn 3). Chạy lại bộ đề 15 bài để xác nhận cải thiện. Nếu vẫn 0/15 → vấn đề nằm ở prompt/architecture, không phải model.

#### Vấn đề 2: Kiến trúc cầu nối — đồng bộ trọng số kém

**Phát hiện:** Kiến trúc ViVy Core ──REST API──► Gemma4 tạo bridge mất context, latency cao, không đồng bộ weight-level, phụ thuộc Ollama.

**Giải pháp:** **WASTE Engine (Weight-Aware Streaming Tensor Engine)** — kiến trúc cho phép logic core truy cập trực tiếp vào không gian trọng số/phân mảnh tri thức của model mạnh hơn mà không cần load full model hoặc gọi REST API.

WASTE Engine = 3 cơ chế từ tài liệu hợp nhất:

| Cơ chế | Tài liệu | Vai trò trong WASTE |
|---|---|---|
| **Correlative Memory** | Mục 22 | Thay REST API bridge bằng associative recall nội bộ. Memory operator: `W = Y X⁺` |
| **Grassmann subspace retrieval** | Mục 23.2 | Streaming weight subspace — biểu diễn khái niệm = low-rank subspace `Q ∈ R^(d×k)`, đo principal angles |
| **Internal Observer + SVD** | Mục 19-20 | Tự phân rã trạng thái thành mode tương quan, không cần đồng bộ qua bridge |

**Cập nhật plan:**
- Giai đoạn 9 (Memory): Mở rộng thành Correlative Memory 4 tầng + associative operator
- Giai đoạn 11 (Observer/SVD): Tích hợp sớm hơn làm cơ chế streaming chính
- Hậu MVP v0.3: Grassmann subspace retrieval chính thức

#### Vấn đề 3: Cần thực nghiệm có hệ thống

**Phát hiện:** Nhiều tuyên bố trong tài liệu chưa được benchmark (Mục 11 tài liệu).

**Giải pháp:** Áp dụng framework đánh giá 2 prototype từ tài liệu (Mục 25):
1. **Cấu trúc test:** Operator unita? Chuẩn bảo toàn? SVD modes ổn định?
2. **Causal test:** Xóa mode trội → kết quả thay đổi? Tắt memory → accuracy giảm?
3. **Năng lực test:** Suy luận compositional? Giữ nhiều giả thuyết? Sửa sai sau bằng chứng?

**Cập nhật plan:** Thêm causal test vào Giai đoạn 12 (Benchmark & Ablation).

---

### 2. Mục tiêu dự án

(Giữ nguyên từ v1 — xem ke-hoach-sol.txt)

Xây dựng một lõi AI gọn nhẹ chạy chủ yếu trên CPU, không huấn luyện và lưu trữ hàng tỷ trọng số như mô hình ngôn ngữ lớn.

Lõi mới chịu trách nhiệm:
1. Tiếp nhận vấn đề đã được cấu trúc hóa.
2. Duy trì đồng thời nhiều giả thuyết.
3. Theo dõi ràng buộc, bằng chứng và mâu thuẫn.
4. Chọn phép kiểm chứng có giá trị thông tin cao.
5. Điều phối mô hình lớn, solver, code runner và hệ chuyên môn.
6. Cập nhật toàn bộ trạng thái suy luận sau mỗi bằng chứng.
7. Ghi nhớ chiến lược, phản ví dụ và nguồn gốc lập luận.
8. Quyết định tiếp tục, phân nhánh, hợp nhất, loại bỏ hoặc dừng.

**Bổ sung v2:** Lõi sử dụng **WASTE Engine** để truy cập tri thức từ model mạnh hơn (gemma4:e4b) thông qua Correlative Memory + Grassmann subspace retrieval, không phụ thuộc REST API bridge hay Ollama.

---

### 3. Phạm vi MVP

(Giữ nguyên từ v1 — debugging phần mềm)

#### 3.1. Miền bài toán đầu tiên

MVP tập trung vào **debugging phần mềm** (giữ nguyên v1).

#### 3.2. Không triển khai trong MVP

(Giữ nguyên từ v1, bổ sung:)

**Bổ sung v2:**
- **Unitary gate logic** (Mục 18 tài liệu) — giữ lại làm experiment, không đưa vào hot path MVP
- **Clifford algebra làm logic tổng quát** — giữ nguyên từ v1
- **Full tensor network** — giữ nguyên từ v1
- **WASTE Engine** — **TRIỂN KHAI TRONG MVP** qua Correlative Memory (Giai đoạn 9) + Observer/SVD (Giai đoạn 11)

---

### 4. Kiến trúc mục tiêu — WASTE ENGINE

#### 4.1. Sơ đồ khối hợp nhất v2 (từ tài liệu Mục 24)

```text
[Input]
   │
   ▼
[Language / Symbolic Encoder] ─── gemma4:e4b (knowledge foundation)
   │
   ├── entities, relations, constraints
   ├── initial tensor / hypervector
   └── ProblemContract
   │
   ▼
[Geometric-Noetic Core]  ←── WASTE ENGINE
   ├── Tensor/VSA binding
   ├── Grassmann subspace map (weight streaming)
   ├── Clifford transform library (claim routing)
   ├── Hypothesis population
   └── Working-state tensor network
   │
   ├──────────────► [Internal Observer]
   │                  ├── amplitude/phase view
   │                  ├── SVD/Schmidt modes (mode decomposition)
   │                  └── entropy/effective rank
   │                             │
   │                             ▼
   │                  [Self-Verification Funnel]
   │                  ├── semantic decode
   │                  ├── constraints
   │                  ├── conflict detection
   │                  ├── evidence score
   │                  └── next-best-test
   │                             │
   ▼                             ▼
[Planner / Router] ◄──────── [Control Signal]
   │
   ├── gemma4:e4b (local, through WASTE memory)
   ├── theorem prover (Z3/Lean)
   ├── code runner
   └── retrieval/search
   │
   ▼
[Evidence Normalizer]
   │
   ▼
[Global State Update]
   │
   ├──────────────► [Correlative Memory]  ←── WASTE core
   │                  ├── Episodic Memory
   │                  ├── Pattern Memory (associative: W = Y X⁺)
   │                  ├── Rule Memory
   │                  ├── Counterexample Memory
   │                  └── Provenance Store
   │
   └──────────────► Continue / branch / merge / prune / stop
```

#### 4.2. WASTE Engine — Weight-Aware Streaming Tensor

##### Cơ chế Correlative Memory (thay REST API bridge)

Memory operator dạng pseudoinverse:

```rust
// Associative recall — thay thế REST API call
struct AssociativeMemory {
    // W = Y X⁺ (Moore–Penrose pseudoinverse)
    patterns: Vec<Pattern>,  // (x_p, y_p, confidence)
}

impl AssociativeMemory {
    fn recall(&self, query: &StateVector) -> Vec<Candidate> {
        // |y_tilde> = W |x>
        // → top-K candidates
        // → domain check
        // → cheap constraint check
        // → return
    }
}
```

##### Cơ chế Grassmann subspace retrieval (streaming weight)

```rust
// Biểu diễn khái niệm = low-rank subspace
struct ConceptSubspace {
    basis: Matrix,           // Q ∈ R^(d×k)
    principal_angles: Vec<f32>,
    energy_retained: f32,
}

impl ConceptSubspace {
    // Đo tương đồng giữa hai subspace
    fn similarity(&self, other: &Self) -> f32 {
        let sigma = svd(self.basis.T * other.basis);
        // principal angles = arccos(sigma)
        // similarity = mean(sigma)
    }
}
```

##### Cơ chế Internal Observer + SVD (mode decomposition)

```rust
struct StateObserver {
    // SVD trên tensor trạng thái
    fn decompose(&self, tensor: &StateTensor) -> ModeDecomposition {
        // M = U Σ V†
        // spectral_entropy = -sum(p_i * log(p_i))
        // effective_rank = exp(spectral_entropy)
        // retained_energy = sum_{i<=r}(S_i²) / sum_i(S_i²)
    }

    // Chỉ nâng thành HypothesisStream khi:
    // - đủ năng lượng phổ
    // - ổn định qua checkpoint
    // - giải mã được
    // - khác biệt với mode khác
    fn promote_to_stream(&self, mode: &Mode) -> Option<HypothesisStream>;
}
```

#### 4.3. Luồng dữ liệu WASTE

```text
1. Input → ProblemContract
2. Hypothesis Population (3-8 hypotheses)
3. VÒNG LẶP SUY LUẬN:
   a. Internal Observer: SVD decomposition → detect modes
   b. Correlative Memory: associative recall → candidate strategies
   c. Grassmann subspace: measure similarity between hypothesis subspaces
   d. Verification Funnel: validate, detect conflicts
   e. Information-Gain Planner: choose next test
   f. Router: dispatch to executor (gemma4:e4b / Z3 / code runner)
   g. Evidence Normalizer: parse result
   h. Global State Update: strengthen/weaken/merge/prune
   i. Correlative Memory: store new pattern (W = Y X⁺ update)
4. Stop khi đạt confidence threshold hoặc hết budget
5. Answer Composer + Provenance
```

---

### 5. Nguyên tắc thiết kế

(Giữ nguyên từ v1, bổ sung:)

**Bổ sung v2:**

##### 5.6. Memory không unita — giữ cường độ liên kết

Tài liệu Mục 22.3 cảnh báo: không nên unita hóa memory operator. Giữ `W` là retrieval operator không unita, chuẩn hóa đầu ra sau truy vấn. Chỉ dùng operator unita trong reasoning dynamics nếu có lý do rõ ràng.

##### 5.7. Một mode SVD chưa phải một suy nghĩ

Tài liệu Mục 20.4: Mode chỉ được nâng thành HypothesisStream nếu thỏa:
- đủ năng lượng phổ
- tồn tại ổn định qua nhiều checkpoint
- giải mã được thành cấu trúc có nghĩa
- khác biệt nội dung với mode khác
- có dự đoán hoặc phép kiểm chứng riêng
- không chỉ là artifact của cách chia tensor

##### 5.8. Cổng unita chỉ dùng cho logic có kiểm soát

Tài liệu Mục 18: Cổng Toffoli cho AND, Modus Ponens với thanh ghi bằng chứng. Không ép Q thành đúng — tạo bằng chứng có thể truy vết:

```text
derive(P, P=>Q) → evidence(Q, rule=MP)
```

---

### 6. Kiến trúc dữ liệu cốt lõi

(Giữ nguyên từ v1 — ProblemContract, HypothesisState, EvidencePacket, ExecutorContract, MemoryRecord)

**Bổ sung v2:**

##### 6.6. StateObservation (từ tài liệu Mục 19.1)

```rust
struct StateObservation {
    checkpoint_id: CheckpointId,
    top_components: Vec<Component>,  // top-K biên độ/xác suất
    probability_mass: f32,
    phase_relations: Vec<PhaseRelation>,  // nếu dùng số phức
    entropy: f32,
    effective_rank: f32,
    active_constraints: Vec<ConstraintId>,
    applied_operator: OperatorId,
}
```

##### 6.7. ModeDecomposition (từ tài liệu Mục 20)

```rust
struct ModeDecomposition {
    singular_values: Vec<f32>,
    left_modes: Matrix,     // U
    right_modes: Matrix,    // V†
    probabilities: Vec<f32>,
    effective_rank: f32,
    retained_energy: f32,
    energy_target: f32,     // mặc định 0.95
}
```

##### 6.8. GateSpec (từ tài liệu Mục 18.3)

```rust
struct GateSpec {
    gate_id: GateId,
    input_roles: Vec<Role>,
    output_roles: Vec<Role>,
    preconditions: Vec<Condition>,
    reversible_mapping: Mapping,
    matrix_or_operator: Operator,
    proof_semantics: ProofSemantics,
    numerical_tolerance: f32,
    inverse_gate_id: GateId,
}
```

##### 6.9. MemoryRecord mở rộng (từ tài liệu Mục 22)

```rust
struct MemoryRecord {
    // ... fields từ v1 ...
    // Bổ sung:
    memory_layer: MemoryLayer,  // Episodic | Pattern | Rule | Counterexample
    associative_pattern: Option<Pattern>,  // (x_p, y_p) cho W = Y X⁺
    provenance_chain: Vec<EventId>,
    review_after: Option<Timestamp>,
}
```

---

### 7. Cấu trúc repository

(Giữ nguyên từ v1, bổ sung:)

```text
geometric-reasoning-core/
├── crates/
│   ├── contracts/        (giữ nguyên)
│   ├── runtime/          (giữ nguyên)
│   ├── hypothesis-engine/(giữ nguyên)
│   ├── verification-funnel/ (giữ nguyên)
│   ├── information-gain/ (giữ nguyên)
│   ├── router/           (giữ nguyên)
│   ├── memory/           ← MỞ RỘNG: Correlative Memory 4 tầng
│   │   ├── episodic/
│   │   ├── pattern/      ← associative operator W = Y X⁺
│   │   ├── rule/
│   │   └── counterexample/
│   ├── provenance/       (giữ nguyên)
│   ├── observer/         ← MỞ RỘNG: Internal Observer + SVD
│   │   ├── svd/          ← truncated SVD, randomized SVD
│   │   ├── mps/          ← MPS/Tensor Train decomposition
│   │   └── telemetry/
│   ├── waste-engine/     ← MỚI: WASTE core
│   │   ├── grassmann/    ← subspace retrieval
│   │   ├── clifford/     ← claim routing (experiment)
│   │   └── streaming/    ← weight-aware streaming
│   ├── executor-gateway/ ← CẬP NHẬT: gemma4:e4b adapter
│   ├── benchmark-runner/ (giữ nguyên)
│   └── api-server/       (giữ nguyên)
│
├── cpp/
│   ├── hdc-kernels/      (giữ nguyên)
│   ├── simd/             (giữ nguyên)
│   ├── numerical/        ← MỞ RỘNG: SVD kernels
│   └── ffi/              (giữ nguyên)
│
├── schemas/              (giữ nguyên)
├── fixtures/             (giữ nguyên)
├── benchmarks/           (giữ nguyên)
├── experiments/          ← MỞ RỘNG: unitary gates, Clifford
├── dashboards/           (giữ nguyên)
├── docs/                 (giữ nguyên)
└── examples/             (giữ nguyên)
```

---

### 8. Kế hoạch triển khai 24 tuần

> **Ghi chú:** Các giai đoạn giữ nguyên khung thời gian từ v1. Nội dung mới từ tài liệu được **bổ sung** (đánh dấu `[v2]`) hoặc **mở rộng** từ giai đoạn tương ứng.

---

#### GIAI ĐOẠN 0 — ĐỊNH NGHĨA NGHIÊN CỨU

##### Tuần 1–2

**Bổ sung v2:**
- [v2] Chạy gemma4:e4b qua bộ đề 15 bài toán 3 cấp độ để xác nhận baseline reasoning
- [v2] Thiết lập causal test framework (tài liệu Mục 25.2): xóa mode trội, tắt memory, chèn phản ví dụ
- [v2] Xác định metric cho WASTE Engine: recall rate, memory retrieval latency, subspace similarity accuracy

---

#### GIAI ĐOẠN 1 — CONTRACT VÀ PROVENANCE

##### Tuần 3–4

**Bổ sung v2:**
- [v2] Thêm schema cho: `StateObservation`, `ModeDecomposition`, `GateSpec`, `MemoryLayer`
- [v2] Event store mở rộng: thêm `ModeDetected`, `MemoryRetrieved`, `SubspaceCompared`

---

#### GIAI ĐOẠN 2 — HYPOTHESIS POPULATION ENGINE

##### Tuần 5–7

(Giữ nguyên từ v1)

---

#### GIAI ĐOẠN 3 — MODEL GIAO TIẾP

##### Tuần 6–8, song song GĐ2

**Cập nhật v2:**

**Model nền tảng:** gemma4:e4b (thay vì "LLM chung")

| Nhiệm vụ | Model | Cơ chế |
|---|---|---|
| Chuyển câu hỏi → ProblemContract | gemma4:e4b | Structured output schema |
| Đề xuất hypothesis candidate | gemma4:e4b | N_h=4 parallel streams |
| Đề xuất test bác bỏ | gemma4:e4b | Information-gain prompt |
| Diễn giải EvidencePacket | gemma4:e4b | Schema-guided |
| Viết câu trả lời cuối | gemma4:e4b | Từ trạng thái verified |

**Bổ sung v2:**
- [v2] WASTE adapter: gemma4:e4b chạy qua llama.cpp local server, không qua Ollama
- [v2] Correlative Memory bắt đầu tích lũy pattern từ gemma4:e4b responses

---

#### GIAI ĐOẠN 4 — EXECUTOR GATEWAY

##### Tuần 8–10

**Bổ sung v2:**
- [v2] Thêm gemma4:e4b adapter (llama.cpp backend, không Ollama)
- [v2] Thêm WASTE memory gateway: cho phép executor đọc/ghi Correlative Memory

---

#### GIAI ĐOẠN 5 — VERIFICATION FUNNEL

##### Tuần 10–13

**Bổ sung v2:**
- [v2] Tích hợp Internal Observer vào verification: SVD modes → conflict detection
- [v2] Thêm tầng "Mode coherence check": kiểm tra mode SVD có nhất quán với hypothesis claim không

---

#### GIAI ĐOẠN 6 — INFORMATION-GAIN PLANNER

##### Tuần 13–15

(Giữ nguyên từ v1)

---

#### GIAI ĐOẠN 7 — ROUTER

##### Tuần 15–16

**Bổ sung v2:**
- [v2] WASTE-aware routing: ưu tiên Correlative Memory recall trước khi gọi executor
- [v2] Grassmann similarity như một tín hiệu routing: nếu subspace của hypothesis gần với pattern đã lưu → ưu tiên memory

---

#### GIAI ĐOẠN 8 — GLOBAL STATE UPDATE

##### Tuần 16–17

(Giữ nguyên từ v1)

---

#### GIAI ĐOẠN 9 — MEMORY TƯƠNG QUAN ← MỞ RỘNG (WASTE CORE)

##### Tuần 18–20

**Mở rộng v2:** Từ "Memory" thành **Correlative Memory 4 tầng + associative operator** (tài liệu Mục 22).

##### Bốn tầng memory

```text
1. Episodic Memory    — toàn bộ phiên suy luận
2. Pattern Memory     — mẫu vấn đề → chiến lược (associative: W = Y X⁺)
3. Rule Memory        — heuristic, rule, điều kiện áp dụng
4. Counterexample Memory — thất bại, phản ví dụ
```

##### Associative operator (tài liệu Mục 22.2)

```rust
// W = Σ_p w_p |y_p><x_p|
// Truy vấn: |y_tilde> = W |x>
// Kết quả: tổ hợp các mẫu đầu ra được cân bởi độ tương đồng
```

**Không unita hóa** (tài liệu Mục 22.3): Giữ W là retrieval operator không unita. Dùng pseudoinverse:

```rust
// X = [x_1, x_2, ..., x_P]
// Y = [y_1, y_2, ..., y_P]
// W = Y X⁺  (Moore–Penrose pseudoinverse)
```

##### Điều kiện ghi (tài liệu Mục 22.4)

```text
verified AND reproducible AND provenance_complete AND domain_scope_known
```

##### Truy xuất có xác minh

```text
query → retrieve top-K patterns
      → domain check
      → cheap constraint check
      → candidate strategy
      → verification
      → apply or reject
```

##### Deliverable v2

- [v2] crate `memory` với 4 tầng
- [v2] Associative operator `W = Y X⁺`
- [v2] Memory governance + versioning
- [v2] Retrieval benchmark (so với cosine embedding, hash, graph signature)

##### Tiêu chí qua cổng v2

- Giảm số bước trên bài tương tự (giữ nguyên v1)
- Không làm giảm accuracy trên bài khác miền (giữ nguyên v1)
- Truy xuất được phản ví dụ liên quan (giữ nguyên v1)
- [v2] Associative recall nhanh hơn REST API call ít nhất 10x
- [v2] Pattern memory không unita hóa — giữ cường độ liên kết

---

#### GIAI ĐOẠN 10 — HDC/VSA EXPERIMENT

##### Tuần 20–21

(Giữ nguyên từ v1)

---

#### GIAI ĐOẠN 11 — INTERNAL OBSERVER VÀ SVD ← MỞ RỘNG (WASTE CORE)

##### Tuần 21–22

**Mở rộng v2:** Từ "observer đơn giản" thành **Internal Observer đầy đủ** (tài liệu Mục 19-20).

##### Kính hiển vi trạng thái (tài liệu Mục 19.1)

Tại mỗi checkpoint:
- top-K thành phần có biên độ/xác suất lớn
- pha tương đối (nếu dùng số phức)
- entropy của phân bố
- ánh xạ thành phần về khái niệm/giả thuyết
- ghi lại thay đổi trước và sau operator

##### Phổ kế luồng tư duy (tài liệu Mục 19.2)

Tensor trạng thái chia theo lát cắt có ý nghĩa:
- dữ kiện ↔ giả thuyết
- giả thuyết ↔ bằng chứng
- kế hoạch ↔ kết quả

SVD/Schmidt decomposition:

```python
M = U Σ V†
p = (S ** 2) / np.sum(S ** 2)
spectral_entropy = -sum(p_i * log(p_i))
effective_rank = exp(spectral_entropy)
retained_energy = sum_{i<=r}(S_i²) / sum_i(S_i²)
```

##### MPS/Tensor Train (tài liệu Mục 20.2)

Khi tensor quá lớn cho full SVD:

```text
... A[k-1] — Λ[k] — B[k] ...
# Λ[k] = singular values tại bond k
# Không cần SVD toàn tensor
# Theo dõi effective rank và entropy theo thời gian
```

##### Chính sách SVD (tài liệu Mục 20.4)

Chỉ chạy khi:
- entropy vượt ngưỡng
- conflict kéo dài
- state cần cluster
- số hypothesis tăng quá nhanh

Mode chỉ nâng thành HypothesisStream khi:
- đủ năng lượng phổ
- ổn định qua checkpoint
- giải mã được
- khác biệt với mode khác
- có dự đoán/phép kiểm chứng riêng

##### Deliverable v2

- [v2] crate `observer` với State Microscope + Thought Spectrometer
- [v2] Truncated SVD + randomized SVD
- [v2] MPS/Tensor Train decomposition (optional)
- [v2] Mode → HypothesisStream promotion policy
- [v2] Causal intervention tool (xóa mode, đổi pha)

##### Tiêu chí qua cổng v2

- Mode liên hệ được với hypothesis cluster (giữ nguyên v1)
- Can thiệp mode tạo thay đổi dự đoán được (giữ nguyên v1)
- Không dùng SVD trong hot path nếu không có lợi ích (giữ nguyên v1)
- [v2] Mode decomposition nhanh hơn full SVD nhờ truncated/randomized methods
- [v2] MPS bond dimension tracking không blow up

---

#### GIAI ĐOẠN 12 — BENCHMARK VÀ ABLATION

##### Tuần 23–24

**Bổ sung v2:** Thêm các baseline và ablation cho WASTE Engine.

##### Baseline mở rộng

```text
B0: LLM trực tiếp (gemma4:e4b)
B1: LLM + RAG
B2: Structured prompt
B3: Linear planner
B4: Tree search
B5: Multi-agent
B6: Core không memory
B7: Core + memory
B8: Core + HDC
B9: Core + observer
B10: Core + WASTE (Correlative Memory + Grassmann)  ← MỚI
B11: Core + WASTE + Observer/SVD                     ← MỚI
```

##### Ablation mở rộng

Tắt lần lượt (giữ nguyên v1, bổ sung:)
- [v2] Correlative Memory (chỉ dùng REST API bridge)
- [v2] Grassmann subspace retrieval
- [v2] Internal Observer / SVD
- [v2] Associative operator (dùng linear search thay vì W = Y X⁺)

##### Causal test (tài liệu Mục 25.2)

```text
- Xóa một mode trội: kết quả thay đổi dự đoán được?
- Đổi pha nhưng giữ xác suất: đầu ra đổi?
- Tắt memory: hiệu suất giảm ở bài tương tự?
- Hoán đổi router: specialist selection giảm?
- Chèn phản ví dụ: luồng sai bị triệt/prune?
```

##### Tiêu chí MVP thành công (bổ sung v2)

MVP đạt khi thỏa một trong các điều kiện (giữ nguyên v1, bổ sung:)
- [v2] WASTE Engine giảm ít nhất 50% số lần gọi executor so với REST API bridge
- [v2] Correlative Memory recall latency < 5ms (so với REST API ~200ms)
- [v2] SVD mode decomposition phát hiện được conflict trước khi executor chạy

---

### 9. Kế hoạch nhân sự

(Giữ nguyên từ v1)

**Bổ sung v2:**
- [v2] WASTE Engine engineer (Rust + linear algebra): thiết kế Correlative Memory + Grassmann subspace
- [v2] SVD/numerical researcher: truncated SVD, randomized SVD, MPS/Tensor Train

---

### 10. Kế hoạch kiểm thử

(Giữ nguyên từ v1, bổ sung:)

**Bổ sung v2:**

##### WASTE-specific tests

- **Associative recall test**: pattern (x_p, y_p) → recall đúng y_p từ x_p
- **Subspace similarity test**: principal angles giữa các concept subspace
- **Mode stability test**: SVD modes ổn định qua checkpoint
- **Memory non-unitarity test**: W giữ cường độ liên kết, không unita hóa

##### Unitary gate tests (experiment)

- Toffoli gate: |P,Q,0⟩ → |P,Q,P AND Q⟩
- Modus Ponens: derive(P, P=>Q) → evidence(Q, rule=MP)
- Reversibility: gate∘inverse = identity

##### Causal tests (tài liệu Mục 25.2)

- Xóa mode trội → kết quả thay đổi dự đoán được
- Tắt memory → accuracy giảm trên bài tương tự
- Chèn phản ví dụ → hypothesis sai bị prune

---

### 11. Kế hoạch tối ưu hiệu năng

(Giữ nguyên từ v1)

**Bổ sung v2:**
- [v2] WASTE-specific profile: memory retrieval latency, subspace similarity throughput, SVD decomposition time
- [v2] Randomized SVD vs full SVD benchmark
- [v2] Associative operator `W = Y X⁺` vs cosine embedding vs ANN

---

### 12. Rủi ro và phương án giảm thiểu

(Giữ nguyên từ v1, bổ sung:)

**Bổ sung v2:**

##### Rủi ro 10: WASTE memory tích lũy pattern sai

**Giải pháp:** Chỉ ghi pattern đã verified + reproducible. Provenance chain bắt buộc.

##### Rủi ro 11: Grassmann subspace retrieval không scale

**Giải pháp:** Randomized SVD, approximate principal angles, caching subspace basis.

##### Rủi ro 12: SVD mode không tương ứng với hypothesis thực tế

**Giải pháp:** Chỉ promote mode thành HypothesisStream khi thỏa 6 điều kiện (Mục 20.4 tài liệu). Causal test bắt buộc.

##### Rủi ro 13: gemma4:e4b vẫn không đạt reasoning baseline

**Giải pháp:** Nếu gemma4:e4b cũng 0/15 → vấn đề ở prompt/architecture, không phải model. Chuyển sang fine-tune hoặc thay model khác.

##### Rủi ro 14: Unitary gate logic không có lợi ích thực tế

**Giải pháp:** Giữ làm experiment riêng (crate `experiments/unitary-gates`), không đưa vào hot path MVP. Chỉ tích hợp nếu benchmark chứng minh cải thiện.

---

### 13. Sản phẩm đầu ra sau 24 tuần

(Giữ nguyên từ v1, bổ sung:)

**Bổ sung v2:**
- [v2] **WASTE Engine core**: Correlative Memory 4 tầng + associative operator
- [v2] **Internal Observer**: State Microscope + SVD mode decomposition + MPS tracking
- [v2] **Grassmann subspace retrieval**: concept similarity qua principal angles
- [v2] **gemma4:e4b adapter**: llama.cpp backend, không Ollama
- [v2] **Causal test framework**: intervention tools cho mode/memory/router

---

### 14. Lộ trình sau MVP

(Giữ nguyên từ v1, bổ sung:)

**Bổ sung v2:**

##### Phiên bản 0.2 (giữ nguyên v1 +)
- [v2] WASTE Engine production: Correlative Memory + Grassmann subspace
- [v2] Internal Observer real-time: SVD trong hot path (nếu benchmark cho thấy có lợi)

##### Phiên bản 0.3 (giữ nguyên v1 +)
- [v2] Grassmann subspace retrieval chính thức — streaming weight từ gemma4:e4b
- [v2] Unitary gate experiment → tích hợp nếu có lợi

##### Phiên bản 0.4 (giữ nguyên v1 +)
- [v2] Clifford transform experiment — routing theo rotor
- [v2] WASTE không phụ thuộc Ollama hoàn toàn

##### Phiên bản 1.0 (giữ nguyên v1 +)
- [v2] WASTE Engine stable API
- [v2] Multi-model weight streaming (gemma4 + specialist models)

---

### 15. Thứ tự ưu tiên tuyệt đối

```text
1.  Benchmark
2.  Contracts
3.  Provenance
4.  Hypothesis population
5.  Verification funnel
6.  Information-gain planner
7.  Executor gateway (gemma4:e4b)
8.  Global update
9.  Correlative Memory ← WASTE CORE (mở rộng từ v1)
10. HDC/VSA
11. Internal Observer + SVD ← WASTE CORE (mở rộng từ v1)
12. Grassmann subspace ← WASTE CORE
13. Clifford
14. Unitary gates ← EXPERIMENT (mới)
```

**Nguyên tắc v2 (giữ nguyên từ v1):**
Không đảo thứ tự này. WASTE Engine (mục 9-11-12) chỉ triển khai sau khi hypothesis engine và verification funnel hoạt động. Unitary gates và Clifford là experiment, không phải điều kiện bắt buộc.

---

*Plan v2 dựa trên ke-hoach-sol.txt (v1) + tai-lieu-tho-hop-nhat-loi-hinh-hoc-v2.md.  
Các phần [v2] đánh dấu nội dung mới từ tài liệu bổ sung.  
Các phần không đánh dấu giữ nguyên từ v1.*

---


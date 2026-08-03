# Chuỗi Test & Thực nghiệm — Unitary Reasoner

Sau phase 0 (củng cố nền tảng), mở rộng test suite và thực nghiệm
toán/vật lý kinh điển.

---

## 1. Thuật toán tương ứng, dị hình, phi đối xứng

### 1.1 Graph Non-Isomorphism (Dị hình đồ thị)

**Bài toán:** Cho 2 đồ thị G₁, G₂ — có tồn tại song ánh bảo toàn cạnh?

**Cách tiếp cận với unitary-reasoner:**
- Mã hóa ma trận kề → quantum state
- Dùng SVD streams để trích đặc trưng phổ đồ thị
- So sánh phổ eigenvalues (bất biến Weisfeiler-Lehman)
- Phát hiện dị hình khi phổ khác nhau

**Test cases:**
- G₁ = K₃ (tam giác), G₂ = C₃ (chu trình 3 đỉnh) → isomorphic
- G₁ = K₃, G₂ = path₃ (đường 3 đỉnh) → non-isomorphic
- G₁ = 4-cycle + chord, G₂ = 4-cycle → non-isomorphic
- G₁ = Petersen graph, G₂ = same → isomorphic

### 1.2 Symmetry Detection & Breaking (Phát hiện/Breaking đối xứng)

**Bài toán:** Phát hiện nhóm đối xứng của cấu trúc logic/toán học.

**Cách tiếp cận:**
- Mã hóa công thức boolean dưới dạng tensor
- Dùng unitary gates để kiểm tra tính bất biến dưới phép hoán vị
- SVD streams phát hiện cấu trúc lặp

**Test cases:**
- `(x ∧ y) ∨ (¬x ∧ ¬y)` — đối xứng qua swap(x,y)
- `(x ∧ y) ∨ (x ∧ z)` — không đối xứng
- Latin square 3×3 — đối xứng nhóm S₃

### 1.3 Non-Abelian Hidden Subgroup (Nhóm con ẩn phi Abelian)

**Bài toán:** Tổng quát hóa Shor's algorithm, liên quan graph isomorphism.

**Test cases:**
- Nhóm S₃ — tìm nhóm con ẩn
- Nhóm D₄ (dihedral) — tìm nhóm con cyclic
- So sánh với trường hợp Abelian (Zₙ)

### 1.4 Asymmetric Cryptography Primitives

**Bài toán:** Mã hóa bất đối xứng — tính một chiều.

**Test cases:**
- RSA: mã hóa (public key) vs giải mã (private key) — asymmetry
- Diffie-Hellman: tính g^a mod p (dễ) vs tìm a (khó)
- Elliptic curve: point addition (dễ) vs discrete log (khó)

### 1.5 Constraint Satisfaction with Symmetry Breaking

**Bài toán:** Sudoku, N-Queens, graph coloring.

**Test cases:**
- Sudoku 4×4 — detect symmetry (hoán vị hàng/cột)
- N-Queens — symmetry under dihedral group D₄
- Graph 3-coloring — color permutation symmetry

---

## 2. Bài toán / phương trình chưa có lời giải

Không yêu cầu hệ thống *giải* được — mà kiểm tra khả năng suy luận
về *cấu trúc* của bài toán.

### 2.1 Collatz Conjecture (Giả thuyết Collatz)

**Bài toán:** f(n) = n/2 nếu chẵn, 3n+1 nếu lẻ. Mọi n → 1?

**Dạng test:**
- Mã hóa quy tắc Collatz dưới dạng unitary gate
- Mô phỏng quỹ đạo cho n nhỏ (n=1..27)
- Phát hiện chu kỳ (1→4→2→1)
- Suy luận về tính dừng

### 2.2 Goldbach's Conjecture (Giả thuyết Goldbach)

**Bài toán:** Mọi số chẵn > 2 là tổng 2 số nguyên tố.

**Dạng test:**
- Kiểm tra cho n chẵn ≤ 100
- Phân bố cặp Goldbach
- Suy luận về cấu trúc số nguyên tố

### 2.3 Twin Prime Conjecture

**Bài toán:** Vô hạn cặp số nguyên tố sinh đôi (p, p+2).

**Dạng test:**
- Thống kê phân bố twin primes trong [1, 1000]
- So sánh với mật độ số nguyên tố

### 2.4 Odd Perfect Numbers

**Bài toán:** Tồn tại số hoàn hảo lẻ?

**Dạng test:**
- Định nghĩa số hoàn hảo: σ(n) = 2n
- Kiểm tra n lẻ ≤ 10⁶
- Ràng buộc: n > 10¹⁵⁰⁰ nếu tồn tại

### 2.5 Riemann Hypothesis (cấp độ suy luận)

**Bài toán:** Mọi zero không tầm thường của ζ(s) có Re(s) = 1/2.

**Dạng test:**
- Mã hóa ζ(s) dưới dạng chuỗi Dirichlet
- Tính zero trên critical strip
- So sánh phân bố zero với mô hình GUE (random matrix)

### 2.6 P vs NP (cấp độ suy luận)

**Bài toán:** Có thuật toán thời gian đa thức cho NP-đầy đủ?

**Dạng test:**
- Mã hóa SAT dưới dạng unitary evolution
- So sánh độ phức tạp giữa 2-SAT (P) và 3-SAT (NP-complete)
- Phát hiện phase transition trong random SAT

---

## 3. Thực nghiệm toán học

### 3.1 Số nguyên tố & Phân tích thừa số

| Bài toán | Mô tả | Phương pháp |
|----------|-------|-------------|
| Kiểm tra nguyên tố | n ∈ [2, 1000] | Miller-Rabin dạng unitary |
| Phân tích thừa số | n = pq (p,q nguyên tố) | Shor-style period finding |
| Định lý số nguyên tố | π(x) ~ x/ln(x) | Thống kê + fitting |
| Định lý Fermat nhỏ | a^p ≡ a (mod p) | Kiểm tra unitary |

### 3.2 Dãy số & Cấu trúc

| Bài toán | Mô tả | Phương pháp |
|----------|-------|-------------|
| Fibonacci | Fₙ dạng đóng | MPS compression |
| Catalan | Cₙ = (2n)!/(n+1)!n! | SVD stream extraction |
| Partition | p(n) — số cách phân hoạch | Associative memory |
| Mersenne | Mₙ = 2ⁿ − 1 | Kiểm tra nguyên tố |

### 3.3 Hình học & Đại số

| Bài toán | Mô tả | Phương pháp |
|----------|-------|-------------|
| Pythagorean triples | a² + b² = c² | Unitary search |
| Elliptic curves | y² = x³ + ax + b | Point addition |
| Finite fields | GF(p^k) arithmetic | Gate composition |
| Polynomial factoring | over GF(p) | Berlekamp unitary |

---

## 4. Thực nghiệm vật lý kinh điển

### 4.1 Cơ học lượng tử (phù hợp nhất với unitary core)

| Bài toán | Mô tả | Phương pháp |
|----------|-------|-------------|
| Harmonic oscillator | H = p²/2m + mω²x²/2 | Time evolution unitary |
| Particle in a box | Infinite square well | Energy eigenstates |
| Double-slit interference | Superposition + measurement | QuantumState + collapse |
| Spin-1/2 system | Pauli matrices | Gate composition |
| Quantum tunneling | Barrier penetration | Evolution with potential |
| Bell inequality | CHSH game | Entanglement + measurement |

### 4.2 Cơ học cổ điển

| Bài toán | Mô tả | Phương pháp |
|----------|-------|-------------|
| Simple pendulum | θ'' + (g/L)sin(θ) = 0 | Small-angle approximation |
| Double pendulum | Chaotic dynamics | Numerical integration |
| Kepler's laws | Orbital mechanics | Gravitational simulation |
| Spring-mass system | Hooke's law + damping | Harmonic oscillator |
| Projectile motion | Parabolic trajectory | Kinematic equations |

### 4.3 Nhiệt động lực học & Thống kê

| Bài toán | Mô tả | Phương pháp |
|----------|-------|-------------|
| Ising model 1D | Spin chain | MPS representation |
| Blackbody radiation | Planck's law | Spectral distribution |
| Maxwell-Boltzmann | Velocity distribution | Statistical sampling |
| Heat equation | ∂T/∂t = α∇²T | PDE discretization |
| Random walk | Diffusion process | Quantum walk analogue |

### 4.4 Điện từ & Sóng

| Bài toán | Mô tả | Phương pháp |
|----------|-------|-------------|
| Wave equation | ∂²u/∂t² = c²∇²u | Unitary evolution |
| Maxwell's equations | ∇·E = ρ/ε₀, ∇×B = μ₀J + ... | Tensor representation |
| LC circuit | q'' + ω²q = 0 | Harmonic oscillator analogue |
| Interference pattern | Double-slit | Superposition principle |

---

## 5. Kế hoạch triển khai

### Phase 1 — Chuỗi test cốt lõi (ưu tiên cao nhất)

1. **Graph Non-Isomorphism** — test suite với 10 cặp đồ thị
2. **Symmetry Detection** — 5 bài toán boolean
3. **Collatz Conjecture** — quỹ đạo + chu kỳ
4. **Goldbach** — kiểm tra n ≤ 1000
5. **Harmonic Oscillator** — time evolution unitary

### Phase 2 — Mở rộng

6. **Constraint Satisfaction** — Sudoku 4×4, N-Queens
7. **Ising Model 1D** — MPS representation
8. **Riemann zeros** — thống kê phân bố
9. **SAT phase transition** — 2-SAT vs 3-SAT
10. **Bell inequality** — CHSH game

### Phase 3 — Thực nghiệm sâu

11. **Navier-Stokes** — 1D Burgers equation
12. **Yang-Mills** — lattice gauge theory toy model
13. **Quantum walk** — trên đồ thị
14. **P vs NP** — structural reasoning
15. **Odd perfect numbers** — search bounds

---

## 6. Tiêu chí đánh giá

| Mức | Ý nghĩa |
|-----|---------|
| ✅ PASS | Kết quả đúng, confidence ≥ 0.7 |
| ⚠️ LOW | Kết quả đúng, confidence < 0.7 |
| ❌ FAIL | Kết quả sai |
| 🔄 PROBE | Hệ thống không thể kết luận (control = "measure") |

Mục tiêu: ≥ 80% PASS + LOW trên phase 1 trước khi chuyển phase 2.
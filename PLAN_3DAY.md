# KẾ HOẠCH 3 NGÀY — MULTI-AGENT PARALLEL

> Triết lý: **thực nghiệm + cải tiến**, không chase hiệu quả ngay từ đầu.
> Build core → test thuật toán với core → đo → cải tiến song song.

## Cấu trúc dự án

```
unitary-reasoner/
├── core/            # Agent 1: unitary gates, MPS, evolution engine
├── memory/          # Agent 2: associative memory (Hebbian + Hopfield)
├── funnel/          # Agent 2: self-verification filter funnel
├── llm_bridge/     # Agent 3: LLM API + encoder/decoder
├── orchestrator/    # Agent 3: điều phối + integration
├── tests/          # Tất cả agent: unit tests
└── benchmarks/     # Agent 1: benchmark + đo lường
```

## Agent 1 — Core Math Engine (core/)

**Ngày 1:**
- `gates.py`: Cổng unita cơ bản (Pauli, Hadamard, CNOT, controlled gates)
- `mps.py`: Matrix Product State — apply gate, canonical form, bond dimension
- `state.py`: Vector trạng thái phức, norm, inner product

**Ngày 2:**
- `evolution.py`: Bộ tiến hóa — lập lịch chuỗi cổng, co tensor
- `svd_streams.py`: SVD tách luồng tư duy (matricization theo partition qubit)
- `entropy.py`: Entropy phân bố (đo độ tập trung suy nghĩ)

**Ngày 3:**
- `benchmarks/bench_core.py`: Benchmark bond dimension, gate count, latency
- Tối ưu: randomized SVD cho n>20 qubit
- Unit tests pass

## Agent 2 — Memory + Filter Funnel (memory/, funnel/)

**Ngày 1:**
- `memory/associative.py`: QuantumAssociativeMemory — Hebbian update, unitary-ize (polar decomposition)
- `funnel/analysis.py`: Phân tích biên độ & pha, entropy, phát hiện giao thoa

**Ngày 2:**
- `funnel/filter.py`: Logic lọc 3 tầng (accept/warn/reject), confidence score
- `funnel/conflict.py`: Phát hiện mâu thuẫn (2 luồng mạnh trái ngược)
- `memory/query.py`: Truy xuất theo cosine similarity, analogical reasoning

**Ngày 3:**
- Integration với core (agent 1 interface)
- Unit tests + edge cases (catastrophic forgetting)

## Agent 3 — LLM Bridge + Orchestrator (llm_bridge/, orchestrator/)

**Ngày 1:**
- `llm_bridge/client.py`: Wrapper API (17 models available) — chat completions
- `llm_bridge/encoder.py`: NL → logic form (triple, propositional logic)
- `llm_bridge/decoder.py`: Logic result → NL câu trả lời

**Ngày 2:**
- `orchestrator/engine.py`: Điều phối — LLM sinh hypothesis → core xử lý → LLM tổng hợp
- `orchestrator/integration.py`: Kết nối core + memory + funnel

**Ngày 3:**
- End-to-end test: bài toán syllogism hoàn chỉnh
- Demo script

## Interface contract (các agent phải tuân theo)

```python
# core/evolution.py
class UnitaryEvolution:
    def step(self, state, gate_sequence) -> State
    def evolve(self, state, n_steps) -> list[State]

# core/svd_streams.py
def extract_thought_streams(state, partition, threshold=0.05) -> list[Stream]
# Stream = {singular_value, amplitude_ratio, state_A, state_B, interpretation}

# memory/associative.py
class AssociativeMemory:
    def store(self, x, y, eta=0.1)
    def query(self, x) -> (y_hat, confidence)

# funnel/filter.py
class FilterFunnel:
    def evaluate(self, streams) -> (kept_streams, control_signal, confidence)
    # control_signal: 'continue' | 'measure' | 'backtrack' | 'delegate'

# llm_bridge/client.py
class LLMClient:
    def chat(self, prompt, model=None) -> str
    def encode(self, nl_text) -> LogicForm
    def decode(self, result) -> str
```

## Definition of Done (cuối ngày 3)

- [ ] 3 module chạy độc lập, unit tests pass
- [ ] End-to-end: giải được bài toán syllogism qua LLM + core
- [ ] Benchmark ghi nhận: bond dimension vs accuracy vs latency
- [ ] Filter funnel sinh control signal đúng
- [ ] Associative memory lưu/truy xuất mẫu suy luận
> [!IMPORTANT]
> **MANDATORY GOVERNANCE FOR INHERITING AGENTS & DOCUMENT EDITORS:**
> 1. **Mandatory Changelog:** Any agent editing this document MUST append an entry to the Changelog section (Agent Name/ID, timestamp, reason for change).
> 2. **Isolate Only, NEVER Delete:** NEVER delete legacy content or architecture definitions. Any superseded section must be enclosed in a quote block and marked `[ISOLATED / DEPRECATED / REPLACED]`.
> 3. **Full Synchronization with `D:\2brain`:** Synchronize all architectural decisions, specifications, and lessons learned into `D:\2brain`.
> 4. **Public Language Policy (Hard Invariant #10):** All public HuggingFace and GitHub documentation MUST be written in 100% English. Internal Vietnamese editions are archived exclusively under `docs/internal_vi/` and `D:\2brain`.

# Vivy-R-Vision-3B (`R-VISION-3B`) — Algorithm & Full-Weight 3.09B Training Specification

## 1. Mathematical Foundation

### 1.1. Two-Tier Fixed Vector Canvas
Let $\mathcal{C}_{\text{stage}} = [0, 2000] \times [0, 1000]$ denote the physical Stage Canvas (`1 unit = 1 cm` at depth $Z = 1.0$) and $\mathcal{C}_{\text{id}} = [0, 1000] \times [0, 1000]$ denote the normalized Entity Identity Box.

For any entity $e \in \{1, \dots, M\}$ referencing foundational archetype $a_e \in \{0, \dots, 4095\}$ with physical height $H_e \text{ (cm)}$ at depth $Z_e \in [0.5, 10.0]$:
$$H_{\text{proj}}(e) = \frac{H_e}{Z_e}$$

### 1.2. Socket-Lock Kinematic Attachment
When a prop archetype $p \in [2048, 3071]$ is bound to socket $s \in \{\text{SOCKET\_HAND\_R}, \text{SOCKET\_HAND\_L}, \text{SOCKET\_HEAD\_TOP}\}$ of host entity $h$:
$$\mathbf{P}_p(t) = \mathbf{P}_h(t) + \frac{H_{\text{proj}}(h)}{1000.0} \cdot \mathbf{R}(\theta_h(t)) \, \mathbf{S}_{h,s}$$

### 1.3. Full-Weight 3.09B BitFit + RMSNorm-IA³ + Semantic Projection Training Objective
Let $\theta_0$ denote the pretrained `3,085,938,688` parameters (`435` tensors across 36 Transformer layers, `d_model = 2048`) of `Qwen2.5-3B-Instruct`. During domain training, we optimize the `181` native `F32` Transformer tensors ($\theta_{\text{F32}} = \{\text{blk.0..35.attn\_norm}, \text{blk.0..35.ffn\_norm}, \text{blk.0..35.attn\_q.bias}, \text{blk.0..35.attn\_k.bias}, \text{blk.0..35.attn\_v.bias}, \text{output\_norm}\}$, totaling `241,664` parameters) jointly with the `d_model = 2048` multi-head semantic projection parameters $\phi$:
$$\mathcal{L}(\theta_{\text{F32}}, \phi) = \mathcal{L}_{\text{CE}}(\text{lighting}) + \mathcal{L}_{\text{CE}}(\text{camera}) + \mathcal{L}_{\text{CE}}(\text{aspect}) + \mathcal{L}_{\text{CE}}(\text{clamp}_{180\text{s}}) + \lambda_{\text{proj}} \|\hat{\mathbf{h}}_{\text{proj}} - \mathbf{h}_{\text{proj}}\|_2^2 + \lambda_{\text{anchor}} \|\theta_{\text{F32}} - \theta_{0,\text{F32}}\|_2^2$$
subject to the trust-region constraint $\|\theta_{\text{F32}} - \theta_{0,\text{F32}}\|_{\infty} \le 0.015$ to preserve full natural-language generation fluency in `llama.cpp`.

---

## Changelog

| Agent | Timestamp | Reason |
|---|---|---|
| Antigravity IDE | 2026-10-17 | Initial algorithm and training specification. |
| Antigravity IDE | 2026-10-18 | Updated for full-weight `3,085,938,688`-parameter (`3.09B`) 36-layer BitFit + RMSNorm-IA³ + Projection training and translated to 100% English per Hard Invariants #9 and #10. |

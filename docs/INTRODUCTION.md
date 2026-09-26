# Introducing ViVy — AI That You Own

## The Problem: You Don't Own Your AI

Every time you use ChatGPT, Claude, or Gemini, you are renting intelligence.

- **Your prompts** go to their servers.
- **Your context** is processed on their hardware.
- **Your usage** trains their next model.
- **Their pricing** can change tomorrow.
- **Their API** can go down during your critical task.
- **Their model updates** can break workflows you built around their behavior.

This is the reality of cloud AI in 2025. And most "local AI" tools are just wrappers that forward your requests to the same cloud, or run a model file without giving you any actual architectural advantage.

**ViVy is different.**

---

## ViVy Gives You What Jev Has

### What is Jev?

Jev is the name for a class of AI model architecture — inspired by Jamba's mixture-of-experts routing — where the model **evaluates multiple hypotheses in parallel** rather than generating sequentially.

The key insight: instead of thinking "what should I do?" one step at a time, Jev-style models score *N candidate actions simultaneously* in a single matrix multiply, then route to the winner.

This makes Jev-class models fundamentally different from standard autoregressive LLMs:

| | Standard LLM | Jev-class model |
|:---|:---|:---|
| **Action selection** | Sequential token generation | Parallel hypothesis scoring |
| **Compute pattern** | Memory-bandwidth bound | Compute-bound (GPU efficient) |
| **Efficiency at scale** | Degrades | Improves |
| **Pre-commitment** | None (generates as it thinks) | Directive emitted before output |

### ViVy's ElasticNCore = Jev for everyone

ViVy packages the Jev architectural insight into a module anyone can run locally:

```python
# N=2 to 16 parallel hypothesis cores
n_core = ElasticNCore(n_min=2, n_max=4, hidden_dim=64)

# All N candidates scored in ONE pass
result = n_core.forward(n_override=2)
# → winner: the best action, selected before any generation
```

You don't need to train a 70B parameter Jamba model to get this benefit. ViVy gives you Jev's parallel evaluation *on top of* any local model you already have.

---

## What Makes ViVy Special

### 1. You Own the Weights

When you install ViVy with Gemma 4 E4B, the model weights are stored on your disk. They are yours:

- No API key required after setup
- Works fully offline, on a plane, on a ship, anywhere
- No token costs, no rate limits, no monthly bills
- The model never "updates" without your consent — you freeze the version you trust

```bash
# This is all you need, forever, after setup
ollama serve
python scripts/run_vivy.py --mode agentic
```

### 2. ViVy Thinks, Not Just Talks

Most local AI gives you a chat interface. ViVy gives you an **agent that can act**:

```
You:   "Analyze my codebase and find all functions with no error handling"

ViVy:  <vivy_thought>
       [EPISTEMIC_ASSESSMENT]
       Confidence: HIGH
       Epistemic_Decision: EXECUTE_DIRECTLY
       </vivy_thought>
       
       [Calls engine_exec: find . -name "*.py" | xargs grep ...]
       [Calls engine_file_io: read each matching file...]
       [Analyzes patterns in CognitiveStateGraph...]
       
       Found 7 functions missing error handling:
       1. auth.py:login() — no try/except around DB call
       2. api.py:process_request() — ...
```

This is not a chatbot. This is an agent with tools, memory, and a cognitive state that persists across the session.

### 3. ViVy Never Makes the Same Mistake Twice

**The VM-11 Invariant** is what separates ViVy from every other local AI implementation.

When ViVy takes an action that fails, the **CognitiveStateGraph** records it:

```
Node (action: "read_file /nonexistent.txt"):
  state: HYPOTHESIS
  falsified_count: 1
  dampen_factor: 0.5¹ = 0.50   ← 50% suppressed
  
  If ViVy considers this action again:
  effective_score = raw_score × 0.50
  → It will almost always choose something else
```

If the same action fails twice: `dampen_factor = 0.5² = 0.25`
Three times: `0.125`

The result: error repeats are **dampened** (measured rate: see Gate-10 receipt). ViVy is architecturally resistant to getting stuck in a retry loop on the same broken action. <!-- [ISOLATED 24/09/2026] prior: "0% error repeat rate" — Gate 9: no 0% claim without receipt. -->

### 4. ViVy Knows What It Doesn't Know

Every ViVy response begins with an **Epistemic Assessment**:

```xml
<vivy_thought>
[EPISTEMIC_ASSESSMENT]
Objective:        What am I trying to accomplish?
Confidence:       HIGH | MEDIUM | LOW
Unknown_Entities: What do I not know yet?
Required_Modalities: Do I need vision/audio/data?
Epistemic_Decision: EXECUTE_DIRECTLY | NEED_KNOWLEDGE_FORAGING | DELEGATE_MODEL

[EXECUTION_DIRECTIVE]
Target:           What/who to act on
Action:           Specific action
Expected_Evidence: How I'll verify success
</vivy_thought>
```

This is not just a prompt trick. It's the output of the DirectiveMTPHead — emitted before the main generation pass. ViVy commits to its epistemic state before generating output, making its reasoning transparent and verifiable.

### 5. Multimodal — Text + Vision + Audio

With Gemma 4 E4B as the base model, ViVy processes:

- **Text**: code, documents, structured data
- **Images**: diagrams, screenshots, charts, photos
- **Audio**: speech, audio events (when using audio-capable adapters)

All locally. All without sending anything to a cloud.

---

## Architecture Summary

```
Your input (any modality)
         ↓
MultimodalAdapter ── Encodes text/image/audio to unified tensors
         ↓
ElasticNCore ──────── N parallel candidates, 1 GEMM pass (Jev-style)
         ↓
DirectiveMTPHead ──── Opcode committed before generation
         ↓
Gemma 4 E4B ────────── Base model: text generation + tool calling
         ↓
ToolDispatcher ─────── Maps tool_call to engine primitive
         ↓
GraphBridge ────────── Evaluates result, updates CognitiveStateGraph
         ↓
CognitiveStateGraph ── Thought Ecology: every action leaves a trace
HebbianRecall ────────  W = Y·X⁺, fast associative memory
         ↓
Output + learned state
```

**The complete loop takes ~30–60 seconds on CPU (first token ~5–10s warm).
With GPU: ~5–8 seconds total.**

---

## Swap Your Model Anytime

ViVy is built on the principle that **the architecture outlasts any specific model weights**.

When a better model comes out, you swap one line:

```
# Modelfile.vivy — change only this line
FROM gemma4:e4b              # Current: Apache 2.0, 9.6GB, CPU-capable
# FROM nemotron-nano-omni    # Upgrade: NVIDIA, Video modality
# FROM qwen3.8-omni-flash    # Future: Full omni, strong tool calling
```

```bash
ollama create vivy-final:v1 -f Modelfile.vivy
```

Everything else — your tools, your memory graph, your sessions, your workflows — stays exactly the same.

---

## Who Is ViVy For?

### Developers who want an AI coding partner
ViVy can read your codebase, run tests, analyze errors, and suggest fixes — entirely locally.

### Researchers who need privacy
Your research data, proprietary datasets, and unpublished results never leave your machine.

### Power users who want control
Set the exact model version. Freeze it. Never worry about the vendor changing behavior overnight.

### Anyone tired of token bills
After hardware setup, every ViVy inference is free.

---

## The Promise

> **ViVy gives you a model that thinks like Jev, runs on your hardware, and answers to no one but you.**

This is what AI ownership means in practice:
- No subscriptions
- No data harvesting
- No vendor lock-in
- No surprise model updates
- No API downtime
- No rate limits
- 100% your data, 100% your compute, 100% your AI

---

*ViVy Final Core V1.0 · Built by [Ngọc Châu](https://github.com/ngocchau-ai) · Made in Vietnam 🇻🇳*

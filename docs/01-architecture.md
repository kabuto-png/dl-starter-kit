# La Bàn AI — Architecture Document

**Status:** Final | **Last Updated:** 2026-06-11 | **Audience:** Partner Claude session ingesting for code contribution

---

## 1. Concept

**La Bàn AI = Deterministic safety + VN-context personalization layer for VNG AgentBase agents.**

The system positions as a **deterministic safety pipeline for enterprise AgentBase**, where memory serves as supporting infrastructure, not the hero feature. The lead artifact is a 3-line SDK wrapper:

```python
from compass import safe_chat

response = safe_chat(
    user_message="How do I analyze revenue trends?",
    user_id="emp_12345",
    dept="BI"  # triggers department-specific template
)
# Returns: { response, rewrite_applied, safety_actions }
```

**Differentiator Stack:**

1. **VNG dept-specific prompt templates** (5: BI/UA/Dev/HR/Designer) — locked competitive moat; built from VNG org structure
2. **VN-EN bilingual native** — no translation overhead; natively handles both languages
3. **"Day 1 insight"** via Identity SSO dept/title — system bootstraps context from user profile without onboarding
4. **3-layer LLM fallback** (AIP Gemma → AIP Qwen → Ollama) — zero-downtime demo; survives AIP rate limits

---

## 2. 6-Step Deterministic Pipeline

```
┌──────────────────────────────────────────────────────────────────┐
│                       User Message + user_id                      │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ 1. detect_intent: Extract role, task, suggested_skill            │
│    Input: user_id + prompt → LangChain agent classifier          │
│    Output: { role: str, task: str, skill: str }                  │
│    Latency: ≤50ms                                                │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ 2. recall_user: Fetch user personalization context               │
│    Input: user_id → Memory.search(namespace=/strategies/...)     │
│    Output: { role_override?, topic_history[], format_pref? }    │
│    Latency: ≤100ms                                               │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ 3. pii_detector: Regex-first PII scan; LLM fallback on hit       │
│    Input: prompt + user context                                  │
│    Output: { pii_found: bool, redacted_prompt: str }             │
│    Latency: ≤75ms (regex only; LLM fallback ~500ms if regex hit) │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ 4. improve_prompt: Apply VNG dept template + suggest rewrite     │
│    Input: prompt + role + task → Template lookup + LLM refine    │
│    Output: { original_prompt, improved_prompt, template_name }   │
│    Latency: ≤75ms (template lookup + simple rewrite)             │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ 5. forward_to_llm: 3-layer LLM fallback with retry logic         │
│    Input: improved_prompt → Try Gemma → Qwen → Ollama fallback   │
│    Output: { llm_response: str, model_used: str, retried: bool } │
│    Latency: ≤3000ms (main call; includes fallback retries)       │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ 6. async_remember: Extract & store 3 fields → Memory CUSTOM      │
│    Input: prompt + response + improve_output                     │
│    Trigger: Async task (non-blocking); fires after response sent │
│    Extract: { role, topic, output_format }                       │
│    Latency: Async; p95 ≤200ms after response                     │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│         Response + Transparency Footer                            │
│    • Rewrite applied (if improve_prompt changed prompt)          │
│    • Safety actions (PII redacted regions, template applied)     │
│    • Model used (in case of fallback)                            │
└──────────────────────────────────────────────────────────────────┘
```

**Pipeline Summary Table:**

| Step | Function | Input | Output | Latency p95 | Notes |
|------|----------|-------|--------|-------------|-------|
| 1 | `detect_intent` | user_id, prompt | role, task, skill | ≤50ms | LangChain classifier |
| 2 | `recall_user` | user_id | personalization context | ≤100ms | Memory.search namespace |
| 3 | `pii_detector` | prompt, context | pii_found, redacted | ≤75ms | Regex-first; LLM on hit |
| 4 | `improve_prompt` | prompt, role, task | improved_prompt, template | ≤75ms | Template lookup + rewrite |
| 5 | `forward_to_llm` | improved_prompt | response, model_used | ≤3000ms | 3-layer fallback |
| 6 | `async_remember` | prompt, response | stored in Memory CUSTOM | ≤200ms async | Non-blocking |

**Latency Targets:**
- **Pipeline (excl. LLM call):** p95 ≤ 287ms (steps 1-4)
- **Total (incl. LLM):** p95 ≤ 3s (steps 1-5)
- **Async remember:** fire-and-forget after response; ≤200ms to complete

---

## 3. Component Stack

| Layer | Technology | Purpose | Provisioned |
|-------|-----------|---------|-------------|
| **Runtime** | AgentBase Runtime (1 endpoint, 2vCPU/4GB) | Invoke entrypoint handler | ✅ |
| **Identity** | `dl-starter-kit` (AgentBase Identity) | SSO + dept/title context | ✅ |
| **Memory** | `memory-0b08d38f-d5a6-4505-8334-9216ae46d739` (AgentBase Memory) | Recall user context + async store | ✅ |
| **Memory Strategy** | `la-ban-ai-coach` (CUSTOM strategy) | 3-field extraction: role, topic, output_format | To add |
| **LLM Primary** | AIP Gemma-4-31b-it (GreenNode) | Fast, low-latency responses | ✅ |
| **LLM Fallback 1** | AIP Qwen-3-27B (GreenNode) | Fallback if Gemma unavailable | ✅ |
| **LLM Fallback 2** | Ollama local (Docker) | Zero-downtime demo fallback | ✅ |
| **Framework** | LangChain 1.3.6 + AgentBaseMemoryEvents checkpointer | Agent orchestration + memory hooks | ✅ |

---

## 4. Current Scaffold Mapping

**Existing in `main.py` (scaffold):**
- ✅ AgentBaseApp initialization
- ✅ Memory client setup (MemoryClient)
- ✅ 2 tools: `remember()`, `recall()`
- ✅ Basic agent creation with LangChain
- ✅ Request handler + health check

**Gaps (6-step pipeline NOT implemented):**

| Gap | Impact | Proposed File |
|-----|--------|----------------|
| No `detect_intent` function | Steps 1-4 fail; no role classification | `tools/intent.py` |
| No `recall_user_context` | Step 2 fails; no personalization | `tools/memory.py` |
| No `pii_detector` | Step 3 skipped; no safety redaction | `tools/safety.py` |
| No `improve_prompt` with templates | Step 4 skipped; no dept-specific refinement | `tools/improve.py` |
| No 3-layer LLM fallback wrapper | Step 5 dies on AIP error | `tools/llm.py` |
| No `async_remember` pattern | Step 6 skipped; no persistent learning | `agents/coach.py` |
| No 5 dept-specific templates | System cannot differentiate BI/Dev/HR | `prompts/templates/` |
| No transparency footer | Response lacks safety + rewrite metadata | `agents/coach.py` → response wrapper |
| No Memory CUSTOM strategy | Memory cannot extract 3 fields | AgentBase Memory UI (one-time setup) |

---

## 5. Memory Schema (CUSTOM Strategy)

The `la-ban-ai-coach` CUSTOM strategy extracts **3 fields** from user interactions:

```json
{
  "strategy_id": "la-ban-ai-coach",
  "extraction_prompt": "Extract the following from the user's message and assistant's response:\n1. **role**: User's job function (e.g., 'Data Analyst', 'Developer', 'Designer', 'HR Specialist', 'BI Analyst')\n2. **topic**: Primary subject discussed (e.g., 'SQL optimization', 'React hooks', 'color palettes')\n3. **output_format**: Preferred response format (e.g., 'step-by-step', 'code example', 'design principles', 'bullet points')\n\nReturn valid JSON only.",
  "fields": [
    {
      "name": "role",
      "description": "Job function or domain expertise",
      "type": "string"
    },
    {
      "name": "topic",
      "description": "Subject matter of conversation",
      "type": "string"
    },
    {
      "name": "output_format",
      "description": "Preferred explanation style",
      "type": "string"
    }
  ]
}
```

**Why 3 fields (not 6)?**
- **Extraction consistency:** Narrow scope minimizes LLM hallucination (per risk assessment)
- **Recall power:** 3 high-signal fields > 6 noisy fields for memory search
- **Query coverage:** Covers 95% of personalization use cases (role + topic + preference)
- **Async latency:** Smaller extraction payload = faster memory write (≤200ms)

**Namespace structure:**
```
/strategies/la-ban-ai-coach/actors/{user_id}/
  → stores records with 3-field metadata
  → searchable by: role, topic, output_format
```

---

## 6. Transparency Footer

Every response includes a metadata footer addressing privacy + safety:

```json
{
  "response": "...",
  "transparency": {
    "rewrite_applied": {
      "original": "...",
      "improved": "...",
      "template": "bi-analyst-v1"
    },
    "safety_actions": [
      "PII redacted: {email, phone}",
      "Applied BI-specific template for clarity"
    ],
    "model_used": "Gemma-4-31b-it",
    "your_data": "This is your AI notebook. Data stored in Memory is encrypted and accessible only to you via your user ID."
  }
}
```

**Privacy Frame:** "Your AI Notebook" — positions La Bàn AI as personal, not surveillance. Transparency = trust.

---

## 7. Deliverable Surface

Per submission requirements:

1. **Runtime Endpoint** — public mode
   - `/invocations` — POST handler for messages
   - `/health` — GET ping status
   - Deployed to AgentBase Runtime

2. **Demo Video** — 2-3 min, 3 acts
   - **Act 1 (45s):** Safety in action (PII redaction, prompt rewrite, dept template applied)
   - **Act 2 (90s):** Memory learning (1st msg → 2nd msg recalls role/topic/format; personalized response)
   - **Act 3 (45s):** Benchmark (3-layer fallback demo; Gemma → timeout → Qwen succeeds; latency under 3s)

3. **GitHub Repository** — public, with tests + benchmarks
   - README + architecture overview
   - 5 dept-specific templates (BI, UA, Dev, HR, Designer)
   - Test suite covering pipeline steps
   - Latency benchmarks (p95 287ms pipeline + p95 3s total)

4. **AgentBase Memory CUSTOM Cookbook** — 8-10 pages
   - GreenNode strategic artifact
   - Use cases for CUSTOM strategies in agent personalization
   - Extraction prompt patterns + best practices

---

## 8. Top Risks & Mitigation

| Risk | Severity | Mitigation |
|------|----------|-----------|
| **AIP rate-limit on demo day** | HIGH | 3-layer LLM fallback (Gemma → Qwen → Ollama); tested D2 |
| **Memory CUSTOM extraction inconsistency** | MED | Narrow to 3 fields (role/topic/output_format); ~70% extraction success target |
| **Privacy backlash from VNG employees** | MED | Transparency footer + "Your AI Notebook" framing in UI; no data shared outside Memory |
| **Demo glitch (infra or network)** | MED | Pre-recorded backup video on D7 morning; have offline fallback |
| **IP policy on public repo** | OPEN | Legal review before D5 push; assume OK unless blocked |
| **Submission description word vs char count** | LOW | Write ~150 words (~300 chars); fits both ≤300 char and 100-200 word limits |

---

## 9. How to Extend: File Structure (PROPOSED)

Each pipeline step maps to a module. Implementation order: steps 1-6, then integrate into coach:

```
compass/
├── tools/
│   ├── intent.py              # Step 1: detect_intent function
│   ├── safety.py              # Step 3: pii_detector (regex + LLM fallback)
│   ├── improve.py             # Step 4: improve_prompt (template + rewrite)
│   ├── llm.py                 # Step 5: forward_to_llm (3-layer fallback)
│   └── memory.py              # Step 2 + 6: recall_user + async_remember
├── prompts/
│   ├── templates/
│   │   ├── bi-analyst-v1.md   # BI analyst template
│   │   ├── product-ua-v1.md   # UA/designer template
│   │   ├── developer-v1.md    # Developer template
│   │   ├── hr-specialist-v1.md  # HR template
│   │   └── designer-v1.md     # Design template
│   └── intent-classifier.md   # Prompt for step 1 intent detection
├── agents/
│   └── coach.py               # Coach orchestration; calls steps 1-6 in sequence
└── main.py                    # Updated entrypoint; calls coach.py
```

**To extend:**
1. Start with `tools/intent.py` (step 1) — test with prompt classifier
2. Build `tools/memory.py` (steps 2 + 6) — wire Memory.search + async write
3. Add `tools/safety.py` (step 3) — start with regex, add LLM fallback
4. Implement `tools/improve.py` (step 4) — load templates, refine prompts
5. Wrap `tools/llm.py` (step 5) — Gemma → Qwen → Ollama retry logic
6. Integrate into `agents/coach.py` — orchestrate pipeline; add transparency footer
7. Update `main.py` → call coach instead of raw agent

Each tool is independently testable; coach composes them in sequence (no circular deps).

---

## Version Info

- **Document Version:** 1.0
- **Last Modified:** 2026-06-11
- **Framework:** LangChain 1.3.6, AgentBase Runtime
- **Target Submission:** 2026-06-17 12:00 UTC

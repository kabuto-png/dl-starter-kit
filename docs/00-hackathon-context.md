# Claw-a-thon 2026 Hackathon Context
## La Bàn AI Project — DL Starter Kit (Nhóm 1)

**Document version:** 2026-06-11 | **Status:** Active (D2/7) | **Audience:** Partner onboarding

---

## 1. Competition Overview

**Event:** Claw-a-thon 2026 (VNG Group + GreenNode)  
**Platform:** AgentBase (VNG's AI agent framework)  
**Organizer:** VNG R&D + GreenNode team  
**Official rulebook:** https://greennode.ai/claw-a-thon-rulebook

Three competition tracks:
- Agentic Assistant (our track)
- Data Analysis Pipeline
- Automation & Integration

---

## 2. Team & Track

**Team Name:** DL Starter Kit (Nhóm 1)  
**Track:** Agentic Assistant  
**Team Size:** 2 developers  
**Project Name:** La Bàn AI  
**Project Concept:** Deterministic safety + VN-context personalization layer for VNG AgentBase agents

---

## 3. Timeline

| Date | Milestone | Status |
|------|-----------|--------|
| 2026-06-10 (D1) | Workshop + infrastructure setup (IAM, Memory, Identity, MaaS API) | DONE |
| 2026-06-11 (D2) | LLM setup, template drafting, tool development begins | IN PROGRESS |
| 2026-06-12 (D3) | Tool implementation (PII detector, prompt improver) | TODO |
| 2026-06-13 (D4) | Pipeline integration, end-to-end testing | TODO |
| 2026-06-14 (D5) | AgentBase deployment, latency benchmarking | TODO |
| 2026-06-15 (D6) | Cookbook, repo polish, demo script finalization | TODO |
| 2026-06-16 (D7 morning) | Demo video record, final rehearsal | TODO |
| **2026-06-17 12:00 GMT+7** | **SUBMISSION DEADLINE** | LOCKED |
| 2026-06-22 to 2026-07-03 | Community voting period | TBD |
| 2026-07-03 | Awards announcement | TBD |

---

## 4. Submission Requirements (3 Mandatory + 1 Optional)

All submissions via **https://greennode.ai/events/greennode-claw-a-thon** (editable until deadline).

### Mandatory Deliverables

| Artifact | Format | Notes |
|----------|--------|-------|
| **Source code** | PUBLIC GitHub repository | Private repos = invalid submission. Must be publicly accessible. |
| **Demo video** | Public link (YouTube/Vimeo/etc), 2-3 minutes | 3 phases: safety showcase (45s) + memory personalization (90s) + performance benchmark (45s) |
| **Use case description** | 100-200 words (plain text) | Executive summary of agent purpose, target user, key safety/personalization features |

### Optional Deliverable

| Artifact | Format | Notes |
|----------|--------|-------|
| **Agent endpoint** | AgentBase share-link | Allows judges to invoke live agent. Requires endpoint in "public" mode via dashboard. |

### Submission Metadata (Email Template)

Include with submission email to helpdesk:
1. **Agent purpose** — What problem does this agent solve?
2. **Permission scope** — Read / Write / Both (specify which VNG services)
3. **Operation scope** — Scope + confirm personal resources only (no confidential data)

---

## 5. Pass Criteria (BTC Review)

All 3 mandatory deliverables must pass:
1. **Runtime verification** — Agent runs successfully on AgentBase platform
2. **Demo video validity** — Video publicly accessible, shows live agent interaction
3. **Use case completeness** — Description clearly articulates problem + solution

Failure to meet any criterion = disqualification.

---

## 6. Prizes

| Rank | Amount | Format |
|------|--------|--------|
| 1st | 30M VND | 50% cash + 50% AgentBase credit |
| 2nd | 20M VND | 50% cash + 50% AgentBase credit |
| 3rd (3 teams) | 10M VND each | 50% cash + 50% AgentBase credit |

---

## 7. Team Resources

**Pre-allocated per team:**
- 10M VND prepaid wallet (can combine: 5M runtime + 5M MaaS tokens; reserve ≥2M for runtime/registry)
- AgentBase account + 3x OpenClaw instances (2vCPU / 4GB RAM each)
- MaaS API access: Gemma-4-31b-it (primary LLM), Qwen-3-27B (fallback)
- Documentation + code templates
- Workshop access + sample agent repository

---

## 8. Data & Privacy Rules (CRITICAL)

**Only allowed data:**
- PUBLIC data (no license restrictions)
- SYNTHETIC data (generated, non-real)
- ANONYMIZED data (PII removed, unrecoverable)
- Personal data (your own email, calendar, notes)

**Strictly forbidden:**
- Real customer data
- Personally Identifiable Information (PII) from others
- Confidential or restricted internal data
- Trade secrets, source code of other VNG products

**Applies even after:** Access to internal systems is granted. Hackathon judges reserve right to audit submissions for data violations. Violations forfeit prize eligibility.

---

## 9. Internal Tool Access

### Office 365 (Teams, Outlook, SharePoint personal)
- **Contact:** helpdesk@vng.com.vn
- **SLA:** 8 hours
- **Tip:** For Outlook/Calendar, prefer simulating with Google Calendar + Gmail (instant OAuth, no ticket wait)

### Other Internal Systems (CRM, HR, Finance, etc.)
- Contact service owner directly
- BTC does not intervene at business unit level
- May require department head approval

### Avoid Access Overhead
Use public alternatives when feasible: Gmail (instead of Outlook), Google Calendar, public APIs. OAuth approval is instant; internal IAM requests may add 1-2 days.

---

## 10. La Bàn AI Architecture Summary

**6-step deterministic pipeline:**
1. **Intent detection** — Extract role + task + skill from user ID + prompt
2. **User recall** — Fetch previous interaction patterns from memory
3. **PII detection** — Regex-first, LLM fallback only on regex match (optimize cost)
4. **Prompt improvement** — Apply VNG department-specific template + suggested rewrite
5. **LLM forward** — 3-layer fallback: AIP Gemma → Qwen → Ollama (zero-downtime demo)
6. **Async memory** — Extract 3 fields (role, topic, output_format) into Memory CUSTOM strategy

**Performance target:** p95 ≤287ms pipeline (excl. main LLM call); total p95 ≤3s.

**Key differentiators:**
- 5 VNG department templates (BI, UA, Dev, HR, Designer) — locked moat
- VN-EN bilingual native
- "Day 1 insight" via Identity SSO dept/title
- 3-layer LLM fallback for demo resilience

**Stack:**
- Runtime: AgentBase Runtime (1 endpoint, 2vCPU/4GB)
- Identity: `dl-starter-kit` (created)
- Memory: Custom CUSTOM strategy for 3-field extraction
- LLM: AIP Gemma-4-31b-it + Qwen-3-27B fallback
- Framework: LangChain 1.3.6 + AgentBase memory checkpointer

---

## 11. Submission Artifacts

1. **GitHub repository** — PUBLIC, with README + tests + benchmarks + 5 department templates
2. **Demo video** — 2-3 min, structured 3-act (safety, memory, benchmark)
3. **Use case description** — 100-200 words, emphasize problem + safety/personalization diff
4. **Agent endpoint** (optional) — AgentBase share-link for live judge interaction
5. **Cookbook** (strategic) — 8-10 pages on AgentBase Memory CUSTOM strategy (GreenNode artifact)

---

## 12. Open Questions (Unresolved)

These issues carry forward from brainstorm phase; escalate to BTC if blocking:

1. **Submission order affect scoring?** — Contact BTC PIC (MaiNTT7)
2. **GitHub repo public legality?** — Confirm with BTC + legal before D5 (2026-06-14)
3. **B2B SaaS pitch on stage allowed?** — Consult VNG strategy team (non-core risk)
4. **Cookbook review before submission?** — GreenNode docs team optional review
5. **Identity service SSO exposes dept/title?** — Critical for "Day 1 insight" feature; test on D2
6. **Runtime autoscale limit?** — May affect demo day concurrent load testing
7. **Sample agent repo structure?** — Clone `vngcloud/clawathon-2026-sample-agents` for patterns

---

## Contact & Resources

- **BTC Support:** helpdesk@vng.com.vn
- **Rulebook:** https://greennode.ai/claw-a-thon-rulebook
- **Submission:** https://greennode.ai/events/greennode-claw-a-thon
- **Agent Docs:** AgentBase platform documentation (in-product)
- **Sample agents:** https://github.com/vngcloud/clawathon-2026-sample-agents

---

**Last updated:** 2026-06-11 14:30 GMT+7 | **Next sync:** 2026-06-12 (D3 check-in)

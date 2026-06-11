# Specs v2 — Pivot from 2026-06-11 Meeting

**Source:** NotebookLM `ff507c7b-9c2f-4088-ad9e-47763febd135` (meeting transcript)
**Status:** AUTHORITATIVE for v2 direction. Supersedes parts of `01-architecture.md` (v1 brainstorm) where conflicting.
**Pending:** Afternoon follow-up meeting (same day) to finalize scope before locking specs.

---

## 1. Meeting context

| Field | Value |
|---|---|
| Date | 2026-06-11 (morning session) |
| Participants | ≥2 people; "anh Đức" mentioned + "em" (action owner) + 1 unnamed |
| Agenda | Pivot direction for Claw-a-thon 2026 project; redefine scope |
| Outcome | Direction pivoted; final scope to be locked afternoon same day |

Verbatim from notebook: "anh nghĩ là chúng ta phải chốt cái đề ra đã thống không cái đề gì đã làm sao để quảng bá" — scope decision still open.

---

## 2. Pivot summary (v1 brainstorm → v2 meeting)

| Dimension | v1 (brainstorm 10/06) | v2 (meeting 11/06) |
|---|---|---|
| Concept | Deterministic safety pipeline for AgentBase agents | **AI Starter Kit + Portal/Hub** bridging external AI ↔ internal workspace |
| Lead positioning | "Deterministic safety pipeline for enterprise AgentBase" | "Close the gap between user L1 → L2" |
| Pipeline | 6-step (intent → recall → pii → improve → llm → remember) | NOT MENTIONED — pivot away from explicit pipeline |
| Dept templates | 5 explicit (BI/UA/Dev/HR/Designer) | Spirit kept: auto-generated CLAUDE.md per phòng ban; **5 specific depts NOT mentioned** in this meeting |
| LLM fallback | 3-layer Gemma → Qwen → Ollama | NOT MENTIONED |
| Memory CUSTOM | 3 fields role/topic/output_format | NOT MENTIONED |
| Tech stack | Custom Python/FastAPI + Docker (LangChain) | **GreenNode OpenClaw** + Zalo **ZCA library** (open source) + MCP concept |
| Compliance angle | PII detector inline | **External AI never touches internal data**; everything proxied through internal OpenClaw agent |

**Key shift:** v1 was a backend-internal pipeline; v2 is an **onboarding product** for new VNG users with compliance-safe AI usage as a side effect.

---

## 3. v2 product concept (locked at concept level)

**Tagline (not finalized):** AI Starter Kit — install your AgentBase workspace with one prompt; safely query internal data through external AI without leaking it.

**Problem solved:** Gap between user Level 1 (knows nothing about AI tooling) and Level 2 (configured workspace, productive). Currently every VNG-er reinventing setup.

**User journey (verbatim):**
> "bước một onbarding thôi onbarding là anh đế biết gì hết... xong con tin nó chịu cho anh một cái câu để anh chat với con clou bằng cái câu đó con clow nó sẽ tự động cài đặt hết tất cả mọi thứ cho anh"

Onboarding = 1 prompt → external AI (Claude) → auto-install full workspace (CLAUDE.md, skills, internal agent config).

---

## 4. Architecture (v2)

```
                   ┌──────────────────────────────────┐
                   │  User chat surface               │
                   │  (Claude Code / Zalo / Teams)    │
                   └─────────┬────────────────────────┘
                             │  1 prompt
                             ▼
                   ┌──────────────────────────────────┐
                   │  External AI (Claude / GPT)      │
                   │  — orchestrator, no data store   │
                   └─────────┬────────────────────────┘
                             │  MCP call (concept)
                             ▼
                   ┌──────────────────────────────────┐
                   │  Portal / Hub (this project)     │
                   │  Standardizes & gates calls      │
                   └─────────┬────────────────────────┘
                             │
                             ▼
                   ┌──────────────────────────────────┐
                   │  Internal Agent ("con cua")      │
                   │  on GreenNode OpenClaw           │
                   │  Holds all sensitive data ops    │
                   └─────────┬────────────────────────┘
                             │
              ┌──────────────┼──────────────┬─────────────┐
              ▼              ▼              ▼             ▼
           myV data      Office 365       Jira         (others)
```

Verbatim on compliance principle:
> "nó nhả một cái cổng để mở thằng thằng clou hay là thằng A nào khác tương tác với nó qua đây luôn... Thằng này nó có nhiệm vụ trả về thôi. Thì con clow đâu có distill được thông tin gì đâu"
> "Nó chuẩn hóa mọi thứ nó đẩy qua cái con kia"

---

## 5. Functional specs

### 5.1 Default skills bundle (4 confirmed in meeting)

| # | Skill | Source | Notes |
|---|---|---|---|
| 1 | Hiểu ý sếp | Custom | "skill để mà hiểu ý xếp" — interpret terse boss instructions |
| 2 | Optimize prompt | Adapted from Claude built-in | "skill optimize prom... Realme của thằng Claudi" — tổng hợp vô bộ này |
| 3 | Super Power Skills của Cody | External (Cody) | "Skill thứ ba á là Super Power SK của C luôn... bộ mà gom những cái con chính hãng vô" |
| 4 | Auto-init CLAUDE.md | Custom | "khi mà cài vô á là mình sẽ init một cái cloudy ch. MD để gọi là tối ưu nhất" |

### 5.2 Department-aware config (concept, not detailed)

Verbatim:
> "hỏi là mày phòng ban là mày cần nhu cầu gì thì cái nhu cầu đó là mình đã xuất ra một cái cloudy. MD phù hợp với đó"

Specs:
- Ask user dept + needs during onboarding
- Generate CLAUDE.md tailored to dept + project
- Specific 5 depts (BI/UA/Dev/HR/Designer) from v1 brainstorm NOT carried forward in meeting — to confirm afternoon

### 5.3 Portal/Hub contract (UNDEFINED — to-spec)

Meeting only confirmed concept. Open items:
- API/endpoint signature
- Auth model between external AI and internal agent
- Request/response schema
- Whether portal = team-built MCP server OR reuses Zalo ZCA library
- Verbatim: "Cái này Nó giống như là MCB là CL sẽ gọi qua MCB đó để kết nối với con để mà lấy"

### 5.4 Compliance rules

- External AI MUST NOT directly read/write internal data
- File data (e.g. CSV uploads) flow is OPEN — current direction: process inside internal agent OR user opens internal tool directly
- Verbatim concern:
  > "cái file data đó ví dụ một cái file CSB... là em phải trực tiếp phải dùng trong cái này rồi chứ em không được dùng cloud"
  > "mà nếu vậy thì mẹ vào team mở lên nó lẹ hơn"

---

## 6. Tech stack (v2)

| Layer | Choice | Source |
|---|---|---|
| Internal agent runtime | **GreenNode OpenClaw** | "vậy thì mình dùng open của Green trước"; "dùng open clow của con Green" |
| Chat bridge library | **Zalo ZCA** (open) | "có cái thư viện ZCA đang open á thì em dùng tạm nó thôi" |
| Portal mechanism | MCP (concept) | "Nó giống như là MCB" — exact server/transport TBD |
| External AI | Claude (primary surface) | Implicit throughout meeting |
| Internal data sources | myV, Office 365, Jira | "data craw từ trên my v Internal data"; "Office 360 thì ok nè"; "những cái như là chira gì á" |

**Implication for current scaffold (`main.py` Python/FastAPI + Docker + LangChain + AgentBaseMemoryEvents):**
- v1 scaffold may be SUPERSEDED in favor of OpenClaw 1-Click + Zalo ZCA. Confirm afternoon.
- Possible hybrid: keep custom Python service as the Portal/Hub layer; offload internal agent to OpenClaw 1-Click.

---

## 7. Internal data sources

Confirmed in meeting:
- **myV** — primary internal data crawl target (verbatim: "data craw từ trên my v Internal data")
- **Office 365** — "300 OBIT Office 360 thì ok nè"
- **Jira** — "những cái như là chira gì á"

Not confirmed:
- Confluence, SharePoint, internal wikis — NOT mentioned
- Demo dataset specifics — NOT mentioned

---

## 8. Open questions (must resolve before D5 deploy)

| # | Question | Owner | When |
|---|---|---|---|
| 1 | Final scope & tagline | "em" + team | This afternoon (11/06) |
| 2 | Portal API/endpoint spec | TBD | After scope lock |
| 3 | Auth model external ↔ internal | TBD | After scope lock |
| 4 | CSV / file upload compliance flow | TBD | OPEN |
| 5 | Demo scenario / video storyboard 2-3 min | TBD | D7 morning |
| 6 | Specific 5 depts list (carry forward from v1?) | TBD | Afternoon |
| 7 | Tech stack final: OpenClaw 1-Click vs custom Python vs hybrid | TBD | Afternoon |
| 8 | Internal data demo dataset (which myV slice?) | TBD | D3 |
| 9 | Pitch/tagline 1-liner | TBD | Afternoon |

---

## 9. Action items from meeting

| Owner | Action | Deadline |
|---|---|---|
| "em" | Suy nghĩ thêm về scope, quay lại chốt buổi chiều | Afternoon 11/06 (today) |
| Team | Chốt câu pitch/đề bài cuối cùng | Same session |
| Team | Quyết tech stack (OpenClaw 1-Click vs custom) | Same session |

Verbatim: "Ok thôi để em vậ em nghĩ thêm nha. Tí chiều em quay lại. Tại chưa hiểu lệ."

---

## 10. Impact on existing docs

| Doc | Status | Action |
|---|---|---|
| `00-hackathon-context.md` | ✅ Still valid | Hackathon rules/deadline/submission unchanged |
| `01-architecture.md` | ⚠️ PARTIALLY SUPERSEDED | v1 6-step pipeline + 5 templates may not apply; await afternoon lock |
| `02-current-state-and-plan.md` | ⚠️ PARTIALLY SUPERSEDED | Phase plan needs re-baseline if tech stack pivots |
| `03-environment-and-deployment.md` | ⚠️ TENTATIVE | Custom Python/FastAPI stack may change; OpenClaw deploy guide to add |
| `04-specs-v2-from-meeting-260611.md` (this doc) | ✅ AUTHORITATIVE for v2 direction | Update after afternoon meeting |

---

## 11. Unresolved questions for partner Claude

Partner session ingesting this doc must understand:
1. **v2 direction is not yet locked** — confirm with team before significant implementation
2. **OpenClaw 1-Click pattern** may replace custom Python scaffold — verify before extending `main.py`
3. **Portal contract** undefined — do not invent API; ask first
4. **Compliance principle is hard:** external AI never touches raw internal data, all internal data ops via OpenClaw internal agent

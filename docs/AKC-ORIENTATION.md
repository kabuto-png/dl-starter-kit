# AKC Orientation — 1-page hiểu hết

**Audience:** anh Đức (hoặc bất kỳ ai mới vào)
**Mục đích:** Đọc 5 phút hiểu được cuộc thi, AKC giải quyết gì, sao mình win.
**Last updated:** 2026-06-14 (D4 checkpoint)

---

## 1. Cuộc thi Claw-a-thon 2026 là gì

VNG nội bộ hackathon do GreenNode tổ chức. Deadline 17/06/2026 12:00.

### 3 tracks chọn 1

| Track | Nội dung | Ví dụ |
|---|---|---|
| **Agentic Assistant** | Trợ lý AI tra cứu + trả lời thay vì chatbot fixed | Bot tra chính sách HR, hỗ trợ khách tìm đơn |
| **Data Analysis** | Agent tự lấy data + phân tích + báo cáo | Tổng hợp doanh số tuần, tóm meeting |
| **Automation & Integration** | Agent chuỗi việc lặp đi lặp lại, kết nối tool hàng ngày | Tự tổng hợp feedback đa kênh, gửi báo định kỳ |

### Submission bắt buộc

1. GitHub repo PUBLIC
2. Demo video 2-3 min PUBLIC
3. Use case description 100-300 words
4. (Optional) Agent endpoint share-link
5. **Agent ACTIVE trên AgentBase** (mandatory để pass)

### Giải thưởng

- Nhất: 30M (15M cash + 15M credit)
- Nhì: 20M
- 3 giải Ba × 10M

Vote: 22/06 - 03/07. Awards 03/07.

---

## 2. AKC giải quyết vấn đề gì

### Pain point

LLM agents **stateless**. Mỗi lần Claude bắt đầu task → reset, quên hết kinh nghiệm tuần trước. Memory solutions hiện tại (Mem0, MemGPT) lưu raw chat history → noise nhiều, không có trust scoring.

### AKC solution

Lưu **structured patterns** với confidence scoring (KHÔNG phải raw text):

```
Pattern = {
  context: "fixing null pointer in Python dict",
  what_worked: "check key with .get() before access",
  confidence: 0.87,
  tier: gold | production | experimental | demoted
}
```

### Self-improvement loop

```
Agent before task → POST /recall → AKC trả Gold patterns
Agent applies → succeeds or fails
Agent after task → POST /remember → AKC update confidence
  success: +0.05  |  failure: −0.10
  Gold (≥0.85) ưu tiên trả về lần sau
```

→ Càng dùng càng smart. Pattern bad tự bị demote, pattern good lên Gold.

---

## 3. Track ta chọn + tại sao

### **Track: Automation & Integration**

(Switch từ Self-Evolving cho cinematic demo + VNG audience relate.)

**Note:** "không self-host OpenClaw" = không build OpenClaw từ source. Vẫn dùng **OpenClaw managed qua Marketplace 1-Click** làm demo client.

### Khác biệt so với 3 track gốc

Cuộc thi list 3 track theo function (Assistant / Data / Automation). AKC nằm ở **General/Self-Evolving** — track riêng cho agent có khả năng tự cải thiện qua thời gian.

### Khác biệt so với memory solutions ngoài thị trường

| Approach | Storage | Trust scoring | AKC khác |
|---|---|---|---|
| Mem0 / Memento | Raw conversation history | ❌ | Lưu structured pattern |
| MemGPT | Hierarchical context | ❌ | Có confidence + tier |
| LangChain memory | Vector store | ❌ | Self-improving via outcome feedback |
| **AKC** | **Structured patterns** | **✅ tier system** | **+ Gold promotion based on real outcomes** |

### Why mình win

1. **AgentBase native** — chạy production trên platform của hackathon
2. **Visible learning** — demo show confidence rises Experimental → Gold trong 2 phút
3. **Plug-and-play** — bất kỳ AI agent nào (Claude Code, OpenClaw, custom) đều xài được qua REST + skill
4. **VN context** — patterns seed với context VNG (feedback triage UA team)

---

## 4. Làm được gì (D4 state)

### Backend (anh Đức + team, DONE)

✅ Feature-complete: all 5 endpoints (`/health`, `/recall`, `/remember`, `/stats`, `/kb/export`)
✅ 16 feature commits since D1 + Round 1 audit fixes (60ca516) + Round 2 edge cases (31ee2d7)
✅ Seed patterns: 30 generic + **10 ASO patterns** (keyword, localization, creative, launch sequencing)
✅ Confidence engine: Gold guardrail, tier promotion/demotion, JSONL storage
✅ `.env` populated: GREENNODE_* vars set for Memory Service sync
✅ MiniMax M2.5 E2E tested successfully

### Direction LOCKED (Level L = REUSE-MAX)

✅ Keep 30 generic seed patterns (5 gold, 10 production, 15 experimental)
✅ Add 10 ASO-specific patterns (keyword research, localization, creative A/B test, release cadence, competitor analysis, soft-launch sequencing) → all 10 surface in default seed via tier distribution
✅ Demo persona: ASO Specialist VNG Publishing, multi-geo launch (JP/KR/VN/TH/PH)
✅ 2-scene storyboard drafted: Scene 1 (JP cold start), Scene 2 (KR compound recall + tier promotion live)

### Round 2 Edge Cases (FIXED)

1. ✅ Empty input guards (tag dedup, null context)
2. ✅ JSONL parse defense (malformed lines)
3. ✅ `/stats` field consistency (all tiers always present)
4. ✅ Memory Service retry logic + timeout handling

---

## 5. Lộ trình còn lại (D4 → D7)

| Day | Việc | Owner | Status |
|---|---|---|---|
| D5 15/06 | Deploy AKC lên AgentBase Runtime ✅ ACTIVE — endpoint live | chủ repo | DONE |
| D6 16/06 | Record demo video 2-3 min, polish use case 200 words | both | READY |
| D7 17/06 | Submit trước 12:00 GMT+7 | both | ON TRACK |

---

## 6. Demo storyboard (ASO specialist, 2-scene)

**Scene 1: JP Cold Start** (0:00-1:00)
- Specialist: "Launching game in Japan. Need keyword strategy."
- Calls `/recall` → AKC returns top-3 Gold ASO patterns (kanji vs romaji, competitor reverse-engineer)
- Applies guidance: selects 5 primary keywords using Sensor Tower + kanji strategy
- Files keywords to Play Console

**Scene 2: KR Compound + Tier Promotion** (1:00-2:00)
- Later session, KR launch task
- `/recall` → returns KR-specific patterns (30-char title cap, Play Store keyword weighting)
- Applies guidance, sees success → `/remember` with outcome=success → pattern confidence rises
- Meanwhile, failed KR title strategy from Session 1 triggers demotion
- `/stats` shows tier distribution: more Gold, fewer Experimental. Hit rate +15%
- **Pitch:** "No rule updates. System learned from one success and one failure. Next time, only tested strategies surface first."

---

## 7. Quyết định locked (D4-D5)

1. ✅ **Track = Automation & Integration** — pitch via 2-scene ASO demo (OpenClaw + Claude Code + AKC backend)
2. ✅ **LLM = Gemma 4-31b-it** — Switched D4 evening after A/B test (9x faster than MiniMax M2.5, valid JSON, cheaper). See `plans/reports/devils-advocate-260614-2237-akc-round2-deep-dive.md` for rationale.
3. ✅ **Direction = Level L (REUSE-MAX)** — 30 generic + 10 ASO + 2-scene demo. Code stable, no new features.
4. ✅ **vCR access** — cleared D4. D5 Docker push + Runtime create unblocked.
5. ✅ **D5 Deploy = SUCCESS** — Runtime ACTIVE at `runtime-577cd07b-33ed-46f1-b134-1149b7137681`. Endpoint: `https://endpoint-30123c53-b859-4599-a339-94b2cedabf7b.agentbase-runtime.aiplatform.vngcloud.vn`. Image `dl-starter-kit:v20260615011317` (v2s2 manifest). All 5 endpoints smoke-tested (Gemma distill verified via /remember).

---

## 8. Resources

| Doc | Location | Mục đích |
|---|---|---|
| **AKC PRD (anh viết)** | `docs/prd/AKC_PRD.md` | Spec chính thức |
| Architecture | `docs/architecture_v1.md` | Code structure feature-first |
| Coordination | `docs/COORDINATION.md` | Decisions + open items + role split |
| Hackathon context | `docs/06-agentbase-state-snapshot.md` | AgentBase resources state |
| Win strategy brainstorm | `plans/reports/brainstorm-260611-2010-clawathon-win-strategy.md` | Plan win + risks |
| Phase plan files | `plans/260611-2010-clawathon-win/phase-0X-*.md` | D2-D7 detailed tasks |

---

## 9. Open items (D4 → D7)

1. **Demo script D6** — finalize storyboard, assign narrator + screen capture roles
2. **Use case description** — draft 200-word ASO workflow summary for submission
3. **L direction final confirmation** — pending anh Đức Telegram ack (non-blocking, em proceed with deploy)
4. **Submission checklist** — repo PUBLIC, demo video link, use case description

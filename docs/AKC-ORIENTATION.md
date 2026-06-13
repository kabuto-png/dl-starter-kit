# AKC Orientation — 1-page hiểu hết

**Audience:** anh Đức (hoặc bất kỳ ai mới vào)
**Mục đích:** Đọc 5 phút hiểu được cuộc thi, AKC giải quyết gì, sao mình win.
**Last updated:** 2026-06-11

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

## 4. Mình đã làm được gì

### Backend (anh Đức build, DONE)

```
akc/
├── core/config.py           # pydantic-settings env validation
├── patterns/                # Pattern model + JSONL store + confidence engine
├── recall/                  # POST /recall — AgentBase Memory search + JSONL fallback
├── remember/                # POST /remember — Qwen distillation → Pattern
├── stats/                   # GET /stats — KB health snapshot
└── export/                  # POST /kb/export — markdown export Gold + Production

main.py                      # FastAPI app factory + health
Dockerfile                   # non-root user, uvicorn, VOLUME
docker-compose.yml           # local volume persistence
scripts/seed_kb.py           # 30 seed patterns (Python/Docker generic — TO RESEED VNG)
.claude/skills/akc-recall-task-remember/SKILL.md   # Claude Code skill
.planning/                   # 5 phases × 3-4 plans = 16 plans, all DONE
```

### E2E test (DONE)

- ✅ `/health` 200, 30 patterns
- ✅ `/recall` returns 3 Gold patterns ranked
- ✅ `/remember` 202 + MiniMax distill success
- ✅ `/stats` 31 patterns (30 seed + 1 new)

### Issues found (audit 14, triage 4 Must-Fix)

1. `skill/SKILL.md` missing path (Critical)
2. `/remember` field contract mismatch PRD (High)
3. Memory Service URL config wrong → fallback local (High)
4. Prompt injection in distillation (High)

---

## 5. Còn lại 5 ngày (D2 tối → D7 trưa)

| Day | Việc | Owner |
|---|---|---|
| D2 tối (HÔM NAY) | Mail BTC vCR 403, fix Memory URL, chốt LLM (MiniMax/Qwen) | chủ repo |
| D3 12/06 | Reseed 30 patterns VNG context + provision OpenClaw managed (Marketplace 1-Click) | both |
| D4 13/06 | Fix 4 Must-Fix issues | anh Đức |
| D5 14/06 | Deploy AKC lên AgentBase Runtime, dress rehearsal | chủ repo |
| D6 15/06 | Record demo video 2-3 min, viết use case 200 words | both |
| D7 16-17/06 | Backup, submit trước 12:00 | both |

---

## 6. Demo storyboard (OpenClaw managed + Claude Code, cinematic VNG context)

| Time | Scene |
|---|---|
| 0:00-0:30 | **Pain**: team UA VNG xử lý feedback từ 5 kênh (Zalo, mail, Sheet, Jira, portal) thủ công |
| 0:30-1:00 | OpenClaw bot (Telegram channel) nhận feedback → gọi AKC `/recall` → trả Gold pattern → bot apply phân loại → done |
| 1:00-1:30 | Edge case mới: bot xử lý sai → `/remember` outcome=failure → pattern mới Experimental |
| 1:30-2:00 | Fast-forward 5 case tương tự, Claude Code (skill) + OpenClaw cùng ghi → confidence rise lên Gold |
| 2:00-2:30 | `/stats` show patterns growing, hit rate tăng. **Pitch: "Không viết rule. System tự học."** |

---

## 7. 3 quyết định cần anh Đức confirm

1. **Track final = Automation & Integration** (switch từ Self-Evolving). Cinematic demo OpenClaw + Claude Code + AKC. Code không đổi, chỉ pitch + use case. Ý kiến anh?
2. **LLM final: MiniMax-M2.5 (e2e đã pass) hay Qwen-2.5-7b (README spec)?** Tại sao có drift?
3. **`/remember` field contract align về PRD §5.2?** Hay update PRD theo current code?

---

## 8. Resources

| Doc | Location | Mục đích |
|---|---|---|
| **AKC PRD (anh viết)** | `docs/prd/AKC_PRD.md` | Spec chính thức |
| Architecture | `docs/architecture_v1.md` | Code structure feature-first |
| Coordination | `docs/COORDINATION.md` | Decisions + open items + role split |
| Hackathon context | `docs/06-agentbase-state-snapshot.md` | AgentBase resources state |
| Partner Claude setup | `docs/07-partner-claude-setup.md` | Setup Claude Code parity |
| Win strategy brainstorm | `plans/reports/brainstorm-260611-2010-clawathon-win-strategy.md` | Plan win + risks |
| Phase plan files | `plans/260611-2010-clawathon-win/phase-0X-*.md` | D2-D7 detailed tasks |

---

## 9. Open questions

1. Track final = Automation & Integration (cinematic OpenClaw managed + Claude Code)?
2. LLM final = MiniMax hay Qwen?
3. `/remember` shape align về PRD?
4. Anh có sample feedback UA thật (synthetic) để reseed không? Hay em tự draft?
5. Ai quay video D6? Phân vai narrator + screen capture?
6. vCR 403 status — anh có liên hệ BTC chưa hay em mail?

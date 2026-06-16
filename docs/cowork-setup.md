# AKC × Claude Cowork — Setup Guide (5 phút)

> Plug-and-play AKC team memory vào Claude Cowork (claude.ai web). Không cần CLI, không cần code. Sau setup, agent **tự gọi** `akc_recall` trước task và `akc_remember` sau outcome.

---

## TL;DR (copy 2 thứ này)

**1. MCP URL** — paste vào Connector → Add custom:
```
https://endpoint-8976bc68-ff8c-48fc-8045-79e0a38c2762.agentbase-runtime.aiplatform.vngcloud.vn/mcp
```

**2. Project Instructions block** — paste vào Project → Custom Instructions:
```
## AKC — team memory (auto)
Before a non-trivial task, call akc_recall(task_context, tags) and cite returned pattern IDs.
After a substantive outcome, call akc_remember(task_context, outcome, patterns_used, success).
Skip for trivial chat. Never invent pattern IDs.
```

---

## Step-by-step

### Bước 1 — Mở Cowork Settings
1. Truy cập [claude.ai](https://claude.ai/)
2. Click avatar góc dưới trái → **Settings**
3. Tab **Connectors** (hoặc **Integrations** tùy version)

### Bước 2 — Add custom MCP connector
1. Click **Add custom connector**
2. **Name**: `akc`
3. **URL**: paste MCP URL ở mục TL;DR
4. **Auth**: None (server hiện không yêu cầu auth)
5. **Save**

→ Server tự discover 7 tools: `akc_recall`, `akc_remember`, `akc_stats`, `akc_export`, `akc_health`, `akc_patterns`, `akc_gaps`

### Bước 3 — Tạo Project (hoặc chọn project sẵn)
1. Sidebar trái → **Projects** → **New project**
2. Name: ví dụ `ASO Team Memory` hoặc `VNG Marketing AKC`
3. Click vào project vừa tạo

### Bước 4 — Paste Project Instructions
1. Project page → **Edit instructions** (hoặc **Custom instructions**)
2. Paste khối ở mục TL;DR section 2
3. **Save**

### Bước 5 — Verify connector + tools available
1. Mở chat mới trong project vừa tạo
2. Gõ test prompt:
   ```
   Gọi akc_health để kiểm tra connection.
   ```
3. Claude sẽ gọi tool `akc_health` → trả `{status: ok, pattern_count: 30+}`

Nếu không thấy tool fire → check lại Bước 2 URL có đúng `/mcp` ở cuối không.

---

## 7 tools available

| Tool | Khi nào dùng |
|---|---|
| `akc_recall(task_context, tags, top_k, min_tier)` | Trước mỗi task — kéo patterns liên quan |
| `akc_remember(task_context, outcome, patterns_used, success, tags)` | Sau outcome — distill thành pattern mới |
| `akc_stats()` | Inspect KB health: total, tier, hit-rate |
| `akc_export()` | Export Gold+Production patterns markdown |
| `akc_health()` | Liveness check |
| `akc_patterns(tier, tag, limit)` | List patterns to review |
| `akc_gaps()` | Show queries with no recall hits |

---

## Test prompt mẫu (paste để verify e2e)

### Cold start
```
Anh đang launch một game Casual VNG ở App Store Japan tuần sau.
Lần đầu go-live JP, chưa có data nội bộ.

Cho anh kế hoạch tuần-1 ASO: keyword strategy (romaji/kanji/hiragana),
screenshot strategy, submission timing.

Recall trước khi suggest, cite pattern IDs, /remember outcome sau khi anh confirm.
```

### Compound learning (sau khi đã có 1-2 outcomes mới)
```
Tuần trước launch JP thành công nhờ kanji long-tail. Giờ sang Korea.
JP playbook nào transfer được, cái nào phải re-do?
Recall 2 lần (tags JP, tags KR), cite cả gold/production + experimental
patterns từ tuần trước.
```

---

## Khác biệt với Claude Code CLI

| | Claude Code | Cowork |
|---|---|---|
| Auto-fire | UserPromptSubmit hook (mỗi turn) | Project Instructions (most sessions) |
| Setup | Clone skill repo | Add connector + paste instructions |
| Audience | Dev có CLI | Mọi nhân viên VNG |
| Bulletproof? | Yes — hook always runs | Soft — model có thể skip nếu prompt quá ngắn |

**Tip để Cowork auto-fire reliable hơn**:
- Đặt instructions Project rõ "MUST call akc_recall before any plan"
- Nếu task complex → mở chat mới (instructions block load lại)
- Có thể nhắc "remember to recall first" trong system reminder

---

## Troubleshooting

| Triệu chứng | Fix |
|---|---|
| Connector "Failed to connect" | Verify URL có `/mcp` ở cuối; check endpoint với `curl -I <URL>` (expect 405 — OK) |
| Tools không xuất hiện trong picker | Restart Cowork tab; verify connector status "Active" |
| Claude không tự gọi recall | Project Instructions có thể bị truncate; rút gọn discipline block + đặt ở đầu |
| `akc_remember` 422 | Required: `task_context` + `outcome`. Optional fields cứ để default null |
| Tool call timeout | Endpoint warm-up — retry sau 5s |

---

## Status & Endpoints

| Service | URL | Status |
|---|---|---|
| MCP server | `https://endpoint-8976bc68-ff8c-48fc-8045-79e0a38c2762.agentbase-runtime.aiplatform.vngcloud.vn/mcp` | ACTIVE (akc v1.27.2) |
| REST API | `https://endpoint-30123c53-b859-4599-a339-94b2cedabf7b.agentbase-runtime.aiplatform.vngcloud.vn` | ACTIVE |
| LLM distiller | Gemma 4-31b-it via GreenNode MaaS | OK |
| KB seed | 30 patterns (10 ASO + 20 generic dev) | Pre-loaded |

Both endpoints share the same KB (single source of truth on AgentBase).

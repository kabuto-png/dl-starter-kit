# AKC Web Demo

Interactive browser demo for **Agent Knowledge Core (AKC)** — the team-memory system for ASO specialists at VNG Publishing.

**Try Live:** _(fill in after deploying to Vercel)_

---

## What it does

1. **Recall** — User asks an ASO question → API calls `POST /recall` on AKC to retrieve relevant stored patterns
2. **Answer** — Recalled patterns are injected as system context → Gemma 4-31B answers, citing pattern IDs
3. **Remember (optional)** — User clicks "Mark useful" or "Mark failed" → API proxies `POST /remember` to AKC to reinforce the memory

```
User → /api/chat → AKC /recall → Gemma (OpenAI-compat) → Response with pattern citations
                                                         ↓ (user feedback)
                          AKC /remember ← /api/remember ←
```

---

## Local Development

### Prerequisites
- Node.js 18+ or 20+
- pnpm (recommended) or npm

### Setup

```bash
cd webdemo

# Install dependencies
pnpm install
# or: npm install

# Copy env template
cp .env.example .env.local
# Edit .env.local and fill in LLM_API_KEY

# Start dev server
pnpm dev
# or: npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `AKC_BACKEND_URL` | Yes | AKC endpoint base URL |
| `LLM_API_KEY` | Yes | API key for Gemma (server-only, never public) |
| `LLM_BASE_URL` | No | Defaults to VNG MaaS endpoint |
| `LLM_MODEL` | No | Defaults to `google/gemma-4-31b-it` |

---

## Deploy to Vercel

### One-click (from CLI)

```bash
cd webdemo
npx vercel deploy --prod
```

Follow the prompts. When asked about the project, select **Next.js**.

### Environment variables on Vercel

In the Vercel dashboard → Project → Settings → Environment Variables, add:

| Name | Value |
|------|-------|
| `AKC_BACKEND_URL` | `https://endpoint-30123c53-...vngcloud.vn` |
| `LLM_API_KEY` | `<your key>` |
| `LLM_BASE_URL` | `https://maas-llm-aiplatform-hcm.api.vngcloud.vn/v1` |
| `LLM_MODEL` | `google/gemma-4-31b-it` |

**Important:** Do NOT prefix with `NEXT_PUBLIC_` — these are server-only secrets.

### Vercel project settings

- Framework: **Next.js** (auto-detected)
- Root directory: `webdemo` _(if deploying from the monorepo root)_
- Build command: `next build` (default)
- Output: `.next` (default)

---

## Project Structure

```
webdemo/
├── app/
│   ├── layout.tsx          # Root layout, metadata, global font
│   ├── page.tsx            # Main chat UI (3-column layout)
│   ├── globals.css         # Tailwind base + dark theme
│   └── api/
│       ├── chat/route.ts   # recall → LLM → response
│       ├── remember/route.ts  # proxy to AKC /remember
│       └── stats/route.ts  # proxy to AKC /health (polled every 5s)
├── lib/
│   ├── akc.ts              # AKC REST client (typed)
│   └── gemma.ts            # OpenAI-compat chat completion client
├── .env.example
├── next.config.js
├── tailwind.config.ts
└── tsconfig.json
```

---

## Tech Stack

- **Next.js 14** App Router + TypeScript (strict mode)
- **Tailwind CSS** — dark theme, no UI library dependencies
- **AKC** — VNG AgentBase Runtime, `POST /recall` + `POST /remember`
- **Gemma 4-31B** via VNG MaaS (OpenAI-compatible API)

---

## GreenNode Clawathon 2026

This demo is the "Agent Endpoint" deliverable for the AKC project submission.
It demonstrates that AKC works with any frontend — not locked into Claude Desktop or Claude Code.

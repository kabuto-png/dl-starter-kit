# AKC — Architecture (for pitch)

**One MCP is the only thing users plug in. Behind it, AKC remembers and OpenClaw curates — a loop that makes team memory get smarter on its own.**

## System — two planes meeting at AKC

```mermaid
flowchart TB
  subgraph DP["DATA PLANE — end users"]
    direction LR
    CC[Claude Code]
    CD[Claude Desktop]
    GM[Gemini CLI]
    CX[Codex]
  end

  MCP["AKC MCP Server<br/>hosted · Streamable HTTP<br/>recall · remember · stats<br/>export · patterns · gaps"]

  AKC[("AKC<br/>shared knowledge base<br/>patterns · confidence · tiers · gaps")]

  subgraph CP["CONTROL PLANE — curator"]
    OC["OpenClaw Steward<br/>audit · curate · gaps"]
  end

  DP -->|"one MCP, any client"| MCP
  MCP -->|"read: recall&nbsp;&nbsp;·&nbsp;&nbsp;write: remember (raw → experimental)"| AKC
  OC -->|"read: /patterns /stats /gaps"| AKC
  OC -->|"write: /curate — promote → gold"| AKC
  AKC -.->|"recall gets better over time"| MCP

  classDef store fill:#1f2937,stroke:#9ca3af,color:#fff;
  classDef face fill:#0e7490,stroke:#67e8f9,color:#fff;
  classDef ctrl fill:#7c3aed,stroke:#c4b5fd,color:#fff;
  class AKC store
  class MCP face
  class OC ctrl
```

*Users only ever touch the MCP. OpenClaw is **not** a user channel — it governs the KB behind the scenes. The two never talk directly; they meet **through AKC**.*

## Flywheel — self-improving memory

```mermaid
flowchart LR
  A["1 · User remembers<br/>a raw pattern"] --> B["2 · AKC stores it<br/>(experimental)"]
  B --> C["3 · Steward audits<br/>+ promotes → gold"]
  C --> D["4 · Next recall<br/>surfaces the gold"]
  D --> A
```

*Plant → cultivate → harvest → richer soil. The more the team uses it, the smarter it gets — with zero manual curation by users.*

## Live

| Component | Role | Endpoint |
|-----------|------|----------|
| AKC backend | shared memory + API | `endpoint-30123c53…vngcloud.vn` |
| AKC MCP (hosted) | the single user-facing surface | `endpoint-8976bc68…vngcloud.vn/mcp` |
| OpenClaw Steward | autonomous curator | OpenClaw chat (steward workspace) |

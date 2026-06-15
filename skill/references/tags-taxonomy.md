# Tags Taxonomy

Tags are how `/recall` finds relevant patterns. **3-6 tags per call**. Tags use lowercase kebab-case.

## Tag categories (use 1-2 from each)

### Domain
What kind of work is this?

| Tag | When |
|---|---|
| `aso` | App Store Optimization (keywords, creative, ASO ops) |
| `ua` | User Acquisition (paid ads, campaigns, attribution) |
| `backend` | API design, business logic, server code |
| `frontend` | UI/UX, components, client-side |
| `infra` | Deploy, CI/CD, runtime, scaling |
| `data` | ETL, analytics, ML pipelines |
| `security` | Auth, vulns, compliance, audits |
| `db` | Schemas, migrations, query optimization |
| `devops` | Docker, K8s, observability |

### Tech / framework

| Tag | Examples |
|---|---|
| `python` `typescript` `go` `rust` | Language |
| `fastapi` `nextjs` `react` `vue` `django` | Framework |
| `postgres` `mysql` `redis` `mongodb` | Database |
| `docker` `kubernetes` `terraform` | Infra |

### Geo (for ASO/UA/launch)

| Tag | Market |
|---|---|
| `jp` | Japan |
| `kr` | Korea |
| `vn` | Vietnam |
| `th` | Thailand |
| `ph` | Philippines |
| `id` | Indonesia |
| `mn` | Mongolia |
| `apac` | APAC region (multi-geo) |
| `global` | Worldwide |

### Genre / vertical

| Tag | Examples |
|---|---|
| `casual` `hyper-casual` `puzzle` `match-3` | Casual games |
| `rpg` `mmorpg` `idle-rpg` | RPGs |
| `social` `creator` `dating` | Social apps |
| `productivity` `utility` `finance` | Apps |

### Focus / aspect

| Tag | When |
|---|---|
| `keyword` | ASO keyword strategy |
| `creative` | Screenshot, icon, video, A/B |
| `release` | Release timing, version cadence |
| `localization` | l10n, translation, cultural |
| `monetization` | IAP, ads, subscription |
| `performance` | Speed, latency, throughput |
| `migration` | Schema/lib/version upgrade |
| `debugging` | Root cause analysis |

---

## Good tag combos (examples)

| Task | Tags |
|---|---|
| "Plan JP casual game keyword strategy" | `["aso","jp","casual","keyword"]` |
| "Debug FastAPI 500 in /signup endpoint" | `["backend","fastapi","python","debugging"]` |
| "Migrate users table from int to uuid id" | `["db","postgres","migration","backend"]` |
| "Optimize Next.js page render perf" | `["frontend","nextjs","react","performance"]` |
| "Set up GitHub Actions for ECR push" | `["devops","ci","aws","docker"]` |

## Anti-patterns

| ❌ Don't | ✅ Do |
|---|---|
| `["code"]` | `["backend","python","fastapi","auth"]` |
| `["task"]` | Specific domain + tech tags |
| `["Bug Fix"]` (CamelCase) | `["debugging"]` (lowercase kebab) |
| `["python", "py", "python3"]` (synonyms) | `["python"]` only |
| `["urgent","priority-high"]` (meta) | Don't tag urgency — tag substance |

## How AKC scores relevance

`/recall` uses **tag overlap + tier preference**:
1. Patterns matching MORE tags rank higher
2. Within same tag-match count, prefer `gold > production > experimental`
3. Recency tiebreak (recent patterns slightly favored)

→ Add 1-2 broad tags (`aso`, `backend`) + 2-3 specific tags (`jp`, `casual`, `keyword`). Don't over-specify.

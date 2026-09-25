# LATTICE v1.0

**Verified Cross-Border Financial Orchestration for International Students.**

A local competition prototype for the 2026 Shenzhen International FinTech Competition, International Track. It connects life events, purchase checks, document evidence, financial ownership, currencies, deadlines, deterministic planning, stress analysis, conditional rescue proposals and permission-controlled **sandbox** actions.

The demo uses fictional people, fixed FX quotes and a deterministic document parser. No real payment is executed. No external API key is needed.

## Architecture

| Boundary | Implementation | Authority |
| --- | --- | --- |
| Understand | `connectors/llm/` provider protocol and `MockLLMProvider` | Structured proposals and explanations only |
| Verify | `lattice_ai/extraction/`, `lattice_core/provenance/` | Evidence, page/block provenance, conflicts, explicit confirmation |
| Plan | `optimizer/model/solver.py`, Google OR-Tools CP-SAT | Integer monetary allocations and independent hard-constraint validation |
| Stress and repair | NumPy simulation and `optimizer/rescue/` | Seeded sensitivity and conditional intervention evaluation |
| Authorize | `lattice_core/policy/`, resource permissions | Ownership, current state, beneficiary checks and all required approvals |
| Act | `apps/api/routes_actions.py`, sandbox connector | Simulated financial state only; P4 is absent |
| Record | PostgreSQL audit triggers and SHA-256 event chain | Append-only application history, retained across demo resets |

Frontend: Next.js, React, TypeScript, Tailwind, React Flow, Recharts, TanStack Query and Zod. Backend: FastAPI, Pydantic v2, SQLAlchemy 2 and Alembic. PostgreSQL is the runtime database; SQLite isolates unit/API test cases.

See [architecture](docs/architecture.md), [threat model](docs/threat-model.md), [evaluation](docs/evaluation.md), [API](docs/api.md) and [audit report](docs/audit-report.md).

## Install and run locally

Verified on Linux x86-64 with Python 3.12, Node 24 and npm 11. The application also provides a Node 22 Docker build. Install `uv`, Python and Node beforehand.

From the repository root:

```bash
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python -r requirements.lock
npm --prefix apps/web ci
npm --prefix scripts/postgres ci
npm --prefix apps/web run build
.venv/bin/python scripts/dev.py --portable-postgres --production
```

Open **http://localhost:3000**. API health: **http://localhost:8000/api/v1/health**. Interactive API reference: **http://localhost:8000/docs**.

The runner starts a PostgreSQL 18.3 engine through PGlite and the PostgreSQL wire protocol, runs Alembic, starts FastAPI and the Next standalone production server. It persists the development database under `scripts/postgres/.pgdata-dev`. This is a portable local development option, not a claim of native PostgreSQL load testing. Ctrl+C stops the stack.

For frontend development, omit `--production`:

```bash
.venv/bin/python scripts/dev.py --portable-postgres
```

For an existing PostgreSQL server, set `DATABASE_URL` in `.env` using `.env.example` as a reference and omit `--portable-postgres`. The runner reads `.env`. With an external server, migrations can also be run separately:

```bash
.venv/bin/python -m alembic upgrade head
.venv/bin/python -m alembic check
```

Do not expose the demo stack on a public network with its published credentials.

## Docker

The supplied three-service Compose stack uses PostgreSQL 16, FastAPI and Next standalone:

```bash
docker compose up --build
```

Then open http://localhost:3000 and use Reset Maya. The database volume survives container restarts. The API runs migrations before startup. The web/API ports bind to localhost.

**Verification limit:** this workspace has no Docker CLI or daemon. The Compose source and build paths were inspected; no Docker image build or native Compose startup is reported as passed. PostgreSQL, migration, API, frontend and browser tests were executed through the portable local stack instead.

## Demo accounts

All four accounts use **`LatticeDemo2026!`**. The role picker is a convenience for these public local demo credentials; backend sessions and resource authorization are still enforced.

| Email | Role | Demo access |
| --- | --- | --- |
| `student@lattice.demo` | STUDENT | Maya's private workspace |
| `parent@lattice.demo` | PARENT | Own contribution and explicitly shared tuition |
| `sponsor@lattice.demo` | SPONSOR | Own resources; no private student workspace |
| `admin@lattice.demo` | ADMIN_DEMO | Reset demo, simulated institution consent |

Passwords are stored as salted PBKDF2 hashes. Sessions use random opaque tokens, hashed in the database, in an HttpOnly SameSite=Strict cookie. Mutations require the `x-lattice-request: 1` header. There is no production identity provider, MFA or rate limiting.

## Reproducible Maya walkthrough

1. Sign in as **Demo administrator** and press **Reset Maya** once. This resets fictional Maya financial records and loads funding, commitments, routes, source documents, permissions and the tuition installment option. Existing audit history is preserved.
2. Switch **Demo actor → Maya · Student**. On Overview, optionally enter a financial intent and press **Understand intent** to see the task sequence; interpretation does not authorize anything.
3. Open **Documents → tuition-review.txt → Extract facts**. Inspect evidence and confidence, then **Confirm all supported facts**. This review targets the existing tuition commitment and does not duplicate it. To test a new commitment, add a text/PDF document with no related commitment and confirm all critical fields; `fixtures/documents/tuition.pdf` is a real text PDF fixture.
4. Open **Plan → Generate optimized plan → Activate plan**. Review nominal, verified and on-time verified coverage. **LATTICE Graph** exposes funding ownership and allocation route/timing details by clicking nodes or edges.
5. Open **Scenario Lab**, set scholarship delay to **14 days**, then **Run stress test**. The displayed results are computed from 1,000 seeded iterations. Press **Apply scholarship delay** to change state, invalidate the plan and generate a replacement with scenario results.
6. Open **Rescue Center → Generate rescue plan**. Inspect the minimum evaluated score, its conditions, fees, family contribution, reserve effect and risk. Press **Prepare intervention**.
7. Try **Sandbox execute** before approvals: it is blocked and audited. On **Permissions**, each listed actor can **Approve my part** after switching roles. Maya cannot approve Father's funds; the administrator represents institutional consent only.
8. Open **Documents → Load malicious update**. An untrusted `ABC999` replacement is blocked; verified `ABC123` remains unchanged and the commitment gets a security hold.
9. Open **Plan → Prepare tuition payment**: beneficiary verification blocks preparation. Open **Audit → Security** to inspect the actual recorded events.

To show a successful repair separately, **Reset Maya**, switch to Student, generate and prepare the recommended rescue. On Permissions, approve as Student, Parent and Demo administrator, then switch back to Student and **Sandbox execute**. The new plan covers the critical commitments within the 45-day horizon. The second tuition installment remains visible on November 15, outside that horizon; it is not deleted. High-priority insurance may still need verified funds. Repeating execution is rejected.

To demonstrate parent privacy, switch to Parent: Funding shows the parent's contribution and Commitments shows shared tuition. Direct API requests for private plans, unshared rent, student funding or student documents are rejected or filtered.

The planning clock defaults to **2026-09-16**, with housing Sep 23, tuition Sep 30, rent Oct 1 and insurance Oct 5. `DEMO_DATE` shifts seeded dates together. Static text/PDF fixtures retain their literal dates.

Initial Maya resources are approximately EUR 1,700 available, VND 33,333,334 parent funding (about EUR 1,200 before fees), EUR 2,000 expected scholarship, and EUR 600 protected reserve. Critical obligations total EUR 5,200. The initial plan is intentionally **AT RISK**: uncertain scholarship income is not guaranteed, and protected reserves are not automatically spent.

## Currencies and interface languages

[Hướng dẫn cập nhật bằng tiếng Việt](docs/CURRENCY_LANGUAGE_UPDATE.md).

The interface supports **English, Tiếng Việt and 简体中文**. Use the language selector on the sign-in screen or in the top bar. Selection persists in this browser; the initial language follows a Vietnamese or Chinese browser preference, otherwise English. Labels, forms, coverage, graph controls, scenarios, approvals, security notices and benchmark presentation are localized. Amounts and dates use the selected locale. Source documents, quoted evidence, account identifiers, audit JSON and downloadable benchmark data stay in their original form.

Supported currencies: **EUR, USD, CNY, VND, GBP, JPY, KRW, SGD, HKD, AUD, CAD, CHF, THB**. All ordered currency pairs have deterministic demo routes: 169 pairs, 170 route records including the extra fast VND→EUR route. Examples: USD→VND, CNY→VND, JPY→USD, SGD→CNY, VND→CNY and their reverse directions. Funding → **Choose a currency pair** shows the quote, fees and p95 settlement time. Funding and Commitment forms accept all 13 currencies; the optimizer can allocate across those routes.

VND/JPY/KRW require whole units; the others accept two decimal places. The API rejects unsupported precision. A fixed-output conversion rounds the source debit upward, includes source-currency fees and discloses the rounding cost. Quotes are synthetic demo data, not live rates or real exchange execution. Overview, rescue scores and expense shocks still use EUR as their explicitly labelled common comparison unit.

Existing demo databases receive missing routes automatically at API startup without resetting their balances/documents. The addition invalidates previous plan snapshots and pending actions; generate a fresh plan before preparing an action. A Maya reset also installs the complete route set. The labelled fixture extractor recognizes all supported ISO currency codes; general Chinese/Vietnamese OCR is not implemented. Intent classification recognizes basic planning, stress and repair phrases in all three languages and never grants payment authority.

## Life events and purchase checks

[Hướng dẫn đầy đủ bằng tiếng Việt](docs/LIFE_EVENTS_GUIDE_VI.md).

Use **Tell LATTICE** from any private page, or open **Life Inbox**. A single sentence becomes an editable proposal and deterministic before/after comparison. English, Vietnamese and Simplified Chinese cover examples, inputs, controls, impact cards, reminders, validation and security errors; switching languages preserves financial values and original input.

Examples include headphones EUR 180, a EUR 350 laptop repair, Father arriving five days late, a EUR 500 Bangkok trip, an EUR 80 shared bill with EUR 40 receivable, EUR 15/month software, and an EUR 100 refund. The same 13-currency registry and demo routes apply. Travel envelopes have eight editable categories with individual currencies. No prices or missing financial facts are invented.

**Keep as idea** changes no balances or plans. **I bought it** requires an owned funding source, an actual date, a confirmation note and explicit acknowledgement. **Confirm details** reserves a pending real event and invalidates old actions; **Apply to sandbox ledger** records the event once and replans. Expected receipts remain unavailable until explicit receipt confirmation. Borrowing preserves repayment debt; shared bills preserve the full expense and separate receivable. Parent reports can delay planning assumptions but cannot debit parent funds.

The new budget protects known commitments and reserves over **365 days**, unlike the original plan's 45-day horizon. Maya initially has a zero safe budget because critical verified funding is insufficient. Runway considers recorded essential commitments only. Recurring budgets materialize through an inclusive 365-day window, not an infinite background scheduler. Internal reminder controls do not cancel external subscriptions or send notifications. General free-form language understanding and independent bank verification remain outside this deterministic demo.

Migration `0002_life_events` adds the event table and `budget_only` obligations. Existing installations run it automatically through `scripts/dev.py` or the Compose API entrypoint; no Maya reset is needed for this schema upgrade. Unknown-beneficiary budget commitments may reserve money but are always blocked by the payment action policy.

## Verification

Run the full repeatable release gate after installing dependencies:

```bash
.venv/bin/python scripts/verify.py
```

It runs the commands below, verifies migration/schema drift and sessions on a **new temporary PostgreSQL database**, runs eleven Playwright workflows, tests both production and development startup, computes FAST/FULL benchmarks and writes exact results to `docs/verification/final-results.json`. Existing development data is not deleted. Docker checks run only if Docker is available.

Individual commands actually exercised:

```bash
DATABASE_URL=sqlite:// .venv/bin/pytest -q tests
.venv/bin/ruff check apps/api lattice_core lattice_ai optimizer simulation connectors benchmark tests scripts migrations
npm --prefix apps/web run test
npm --prefix apps/web run typecheck
npm --prefix apps/web run lint
npm --prefix apps/web run build
.venv/bin/python scripts/dev.py --portable-postgres --production --fresh-db --verify
.venv/bin/python scripts/dev.py --portable-postgres --fresh-db --startup-check
.venv/bin/python -m benchmark.run --mode FAST
.venv/bin/python -m benchmark.run --mode FULL
```

`npm --prefix apps/web run e2e` also runs against an already-running stack. On Linux x86-64 its runner extracts the pinned packaged Chromium without requiring a separate browser download. Other platforms need a Playwright-supported browser or `CHROMIUM_EXECUTABLE_PATH`.

See [the audit report](docs/audit-report.md) for final counts and environmental limits; JUnit, Vitest and Playwright JSON reports are retained. Two upstream Python TestClient deprecation warnings do not represent failed tests.

## Benchmark

FAST executes **48 cases** (12 per category); FULL executes **500 cases** (125 per category). Both use deterministic generated ground truth and actual extraction, optimizer, rescue and security API code. JSON and CSV are written under `benchmark/results/`. Benchmark UI runs the same implementation and exports the same stored results.

Categories: extraction, planning, dynamic replanning, security. Executable baselines B0 balance-only, B1 earliest-deadline greedy, B2 cheapest-route greedy, B3 generic planner approximation and B4 LATTICE use the same generated cases. B3 is a heuristic, not an external LLM evaluation. The 500 cases contain parameter variations of a bounded set of synthetic families; they are not 500 independent real documents or attack discoveries.

## Environment variables

| Variable | Default / effect |
| --- | --- |
| `DATABASE_URL` | PostgreSQL SQLAlchemy URL; portable runner overrides it locally |
| `DEMO_MODE` | `true`; reset/load require this plus ADMIN_DEMO |
| `DEMO_DATE` | `2026-09-16`; deterministic planning clock |
| `API_INTERNAL_URL` | Backend URL used by the Next server proxy |
| `COOKIE_SECURE` | `false` for HTTP localhost; use `true` behind HTTPS |
| `DB_POOL_SIZE` | `1`; PGlite requires a single connection |
| `BENCHMARK_OUTPUT_DIR` | `benchmark/results` |
| `RESCUE_FAMILY_WEIGHT` | `0.08`; disclosed additional-funding score weight |
| `RESCUE_RESERVE_WEIGHT` | `0.15`; disclosed reserve-release score weight |
| `RESCUE_FRICTION_WEIGHT` | `10`; disclosed friction score weight |
| `CHROMIUM_EXECUTABLE_PATH` | Optional browser path for E2E |

## Known boundaries

- The provider protocol is ready for another implementation; only the deterministic fixture parser is implemented. General OCR and arbitrary real-world document understanding are not claimed.
- User confirmation is T0 attestation, not bank/institution verification. Unreceived scholarship stays EXPECTED even after its notice is confirmed. Untrusted documents cannot overwrite verified critical facts.
- Fixed FX and settlement quotes are synthetic. Scenario Failure Rate describes selected model assumptions, not actuarial real-world probability.
- Rescue minimizes a configurable score among finite intervention bundles, with a cent-level family amount search per bundle. It is conditional on approvals, receipt and any institution consent; it is not a proof of global minimality across every possible intervention.
- Installments keep deferred debt visible; the SAFE label concerns critical obligations inside the stated 45-day horizon. Partial allocations describe gaps; payment execution requires full verified coverage.
- All execution is simulated. The family contribution connector explicitly assumes a fictional EUR receipt after approvals; no cross-border payment provider is contacted.
- Audit triggers and hashes provide application-level tamper resistance, not protection from an all-powerful database operator or external notarization.
- Production identity, rate limiting, bank integration, live source attestation, load testing and native Docker verification remain outside the completed local demo verification.

## Source package

```bash
.venv/bin/python scripts/package_source.py
```

Creates `../LATTICE_v1.0_SOURCE.zip` with source, fixtures, migrations, documentation, computed benchmark results and verification reports. Dependencies, virtual environments, caches, local `.env` files, database volumes and Git internals are excluded.

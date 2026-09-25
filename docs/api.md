# API reference

Base: `/api/v1`. The generated `docs/openapi.json` is the full schema snapshot; a running API serves interactive documentation at `/docs` and OpenAPI at `/openapi.json`.

## Authentication and ownership

POST `/auth/login` with `{"email":"student@lattice.demo","password":"LatticeDemo2026!"}`. Preserve the returned `lattice_session` cookie. Every mutation, including login, requires `x-lattice-request: 1`. GET `/auth/me` returns the authenticated actor; POST `/auth/logout` revokes the session.

Private finance endpoints require STUDENT or the fictional ADMIN_DEMO workspace. Parent/sponsor collection responses are resource-filtered; guessing a document/obligation ID does not bypass access control. Authentication failure is 401, lack of a capability 403, hidden/missing resources 404, stale/unsafe transitions 409 and invalid input 422. Body fields outside the schema are rejected.

| Endpoints | Behavior |
| --- | --- |
| GET `/currencies` | Public supported ISO codes, minor-unit precision, fixed demo EUR valuations; no financial/private data |
| GET `/health` | Database health, version, deterministic planning clock, sandbox/provider labels |
| POST `/demo/reset`, `/demo/load-maya` | ADMIN_DEMO plus DEMO_MODE; reset preserves audit and accounts |
| POST, GET `/documents` | Add UTF-8 text JSON or multipart text/PDF; list accessible documents |
| GET `/documents/{id}` | Document and cited facts |
| POST `/documents/{id}/extract` | Structured proposals, security flags, provenance; never creates an approved action |
| GET `/facts` | Facts from the current actor's documents |
| POST `/facts/{id}/confirm`, `/reject` | Explicit confirmation or rejection; confirmed critical set updates state |
| GET, POST `/funding-sources`; PATCH `/{id}` | Owner-scoped funding; source mutation invalidates/replans current financial state |
| GET, POST `/obligations`; GET, PATCH `/{id}` | Visible commitments and owner-confirmed changes |
| POST `/obligations/{id}/verify-beneficiary` | Explicit T0 re-attestation, repeated identifier and note; logs authority |
| GET, POST `/transfer-routes` | Fixed demo route quotes; additions require ADMIN_DEMO |
| GET `/graph` | Authorized actor/source/obligation graph and allocations |
| POST `/plans/generate`; GET `/plans`, `/{id}` | Deterministic optimizer, snapshot, coverage and explanation |
| POST `/plans/{id}/activate` | Select a fresh working plan; delegated APPROVE_PLAN returns redacted status |
| POST `/plans/{id}/simulate` | Seeded sensitivity with controls |
| POST `/scenarios/run`; GET `/scenarios/{id}` | Alternate scenario entrypoint with plan ID and persisted results |
| POST `/rescue/generate`; GET `/rescue/{id}` | Rank actual evaluated conditional proposals; persist candidates |
| GET `/actions`; POST `/actions/prepare` | Prepared sandbox action, server-derived allocations and required approvals |
| POST `/actions/{id}/approve`, `/sandbox-execute` | Approve only your part; execute only after policy passes |
| GET, POST `/permissions`; DELETE `/{id}` | Owner grants/revokes a capability on one resource |
| GET `/audit`; GET `/audit/verify-chain` | Visible history with optional category; full chain check requires ADMIN_DEMO |
| POST `/intent` | Deterministic intent/task steps, always `action_authorized: false` |
| POST `/benchmark/run`; GET `/benchmark/latest`, `/benchmark/export` | Computed FAST/FULL results; export format `json` or `csv` |

## Representative payloads

Text document (untrusted by default):

```json
{
  "filename": "invoice.txt",
  "text": "Type: TUITION\nAmount: 3200\nCurrency: EUR\nDue date: 2026-09-30\nBeneficiary: ABC123",
  "trust_level": "T3",
  "target_obligation_id": "tuition"
}
```

Leave `target_obligation_id` null for a new commitment. Multipart fields are `file`, optional `trust_level`, optional `target_obligation_id`. Limits: 2 MB upload, 20 PDF pages, 100,000 extracted text characters. A scanned image-only PDF is rejected rather than inventing OCR output.

Confirmation: `{"confirmed":true}`. Missing critical values remain missing. Supported critical fields are amount, currency, due date and beneficiary; scholarship notices require amount, currency and available-from date and remain EXPECTED after confirmation.

New funding:

```json
{
  "label": "Personal EUR account",
  "source_type": "STUDENT_BALANCE",
  "amount": 1700,
  "currency": "EUR",
  "available_from": "2026-09-16",
  "availability_status": "AVAILABLE",
  "restriction_type": "UNRESTRICTED",
  "minimum_remaining_balance": 0,
  "confirmation_note": "Explicitly checked fictional account balance."
}
```

Owner/role/trust fields are derived by the server, not mass-assignable. Funding PATCH accepts amount, available_from, availability_status and required confirmation_note. Obligation PATCH accepts amount, due_date and required confirmation_note; it cannot replace a beneficiary.

Detailed stress:

```json
{
  "scenario": "COMBINED_STRESS",
  "scholarship_delay": 14,
  "transfer_delay": 2,
  "fx_shock": 3,
  "unexpected_expense": 0,
  "funding_cancellation": [],
  "iterations": 1000,
  "seed": 17
}
```

Named presets apply only when their parameters are omitted. NORMAL uses zero shocks; TRANSFER_DELAY uses four days, FX_STRESS 5%, SCHOLARSHIP_DELAY 14 days, COMBINED_STRESS 4/14 days, 5% and EUR 300. Explicit zero remains zero. `/scenarios/run` additionally requires `plan_id`.

Prepare a payment:

```json
{"type":"TUITION_PAYMENT","plan_id":"<returned-plan-id>","obligation_id":"tuition"}
```

The server supplies amount, beneficiary, routes and required actors. Action types: `TUITION_PAYMENT`, `SCHEDULE_TRANSFER`, `PARENT_FUNDING_REQUEST`, `ACTIVATE_INSTALLMENT`, `APPLY_RESCUE`. Intervention actions require a `candidate_id` belonging to the specified fresh plan. No arbitrary payment destination or executable tool instruction is accepted. A sandbox receipt includes `real_money_moved: false`.

Grant a resource capability:

```json
{"target_actor_id":"father","resource_type":"OBLIGATION","resource_id":"tuition","permission_type":"VIEW_SHARED_OBLIGATION"}
```

Resource types: FUNDING, OBLIGATION, PLAN, ACTION. Only a resource owner can grant a matching permission to an established related actor. APPROVE_ACTION adds an approval requirement; it does not delegate away the fund owner's consent.

Benchmark run: `{"mode":"FAST"}` or `{"mode":"FULL"}`. GET `/benchmark/export?format=json` or `format=csv` exports the latest computed run. No private financial snapshot is included in synthetic benchmark outputs.

Currency fields accept EUR, USD, CNY, VND, GBP, JPY, KRW, SGD, HKD, AUD, CAD, CHF and THB. VND/JPY/KRW amounts must be integers; other amounts support two decimal places. Localized UI labels never change these codes. The API and machine-readable outputs remain language-neutral identifiers with English explanatory strings; localized presentation is a frontend responsibility.

## Private Life Event APIs

All paths below are relative to `/api/v1`; all require STUDENT or ADMIN_DEMO. The administrator uses Maya's scope. There is no parent/sponsor access to these private records, budgets or queries. Mutations use the same session/CSRF-header convention as the original APIs.

| Method | Path | Behavior |
| --- | --- | --- |
| GET | `/life-events/examples` | Seven deterministic examples in EN/VI/ZH; no financial mutations |
| POST | `/life-events/interpret`, `/life-events` | `{raw_input, locale, amount_minor?, currency?, event_date?}` → stored proposal |
| GET | `/life-events`, `/life-events/{id}` | Scoped event records; detail includes recurring summary |
| POST | `/life-events/{id}/simulate` | `{version, proposal}` → updated event and shadow impact |
| POST | `/life-events/{id}/confirm` | `{version, proposal, confirmed:true, confirmation_note}` → explicit T0 review |
| POST | `/life-events/{id}/apply` | `{version}` → `{event, planning}`; real confirmed state only, atomic and once |
| POST | `/life-events/{id}/dismiss` | `{version}` → dismiss idea/pending record or cancel an unreceived expectation |
| POST | `/life-events/{id}/received` | `{version, confirmed:true, received_date, confirmation_note}` → actual receipt attestation |
| POST | `/life-events/{id}/resolve` | `{version, confirmed:true, confirmation_note}` → close applied report without reversing ledger history |
| POST | `/life-events/{id}/reminder` | `{version}` → toggle the internal reminder only |
| POST | `/life-events/{id}/pause-scenario` | `{version}` → compare a copy without future subscription costs |
| POST | `/life-events/{id}/recurrence` | Same shape as confirm; change amount of future unpaid entries, same currency/cadence |
| GET | `/life-inbox?currency=EUR` | Events, budget, runway and internal reminders |
| GET | `/safe-to-spend?currency=EUR` | Today/week/month budget, protected money, gaps and explanation |
| GET | `/runway` | Recorded verified/conditional runway bounds and next critical deadline |
| POST | `/purchase-check` | Capture payload → forced shadow comparison; never applies the event |

Amounts are integer minor units, e.g. EUR 180 = `18000`, VND 180,000 = `180000`. Dates use ISO `YYYY-MM-DD`. Missing critical values are null. Proposal fields, envelope categories, event types and validation limits are documented by the generated OpenAPI `/docs`; extra authority/status fields are forbidden. After every successful mutation use the returned `version` for the next request. A changed financial snapshot requires renewed review and confirmation. Applied events cannot be generically edited.

User-provided notes and raw text are private source content and are returned unchanged. API machine codes remain stable English; presentation strings and controls are localized by the frontend. Expected income may improve nominal projections but never verified spend capacity merely by being captured or simulated.

For `EXPENSE_OCCURRED`, an optional `obligation_id` may settle an owned `budget_only` obligation whose full amount and currency match. Ordinary payment obligations return 403 and retain the approval-controlled action flow. This prevents both double-budgeting a paid life commitment and bypassing payment consent.

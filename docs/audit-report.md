# LATTICE v1.0 engineering audit

Final verification: **2026-09-25**, including the requested currency/language and Life Event Layer extensions. Authoritative scope: the supplied LATTICE v1.0 specification and subsequent extension instructions. Repository `/workspace/lattice`. The original saved prototype has been replaced by the OR-Tools/PostgreSQL implementation; this release adds private life-event workflows and preserves the verified original hero loop.

## What was broken and repaired

1. An old source ZIP contained a 29-file prototype and did not represent the completed workspace. A complete source package is rebuilt from the current repository.
2. Parent funding create/patch could include a replacement plan containing private student snapshots. These responses now return only the owned funding and a change acknowledgement; regression covers both methods.
3. Unshared parent resources could enter student plans/graph indirectly. The state builder now applies per-resource visibility before optimization.
4. A proposal could cite the right text but supply a different normalized amount, deadline, currency or beneficiary. Provenance now independently validates both the evidence field and normalized value.
5. Unicode beneficiary proposals needed to set a security hold even when rejected during validation. The original beneficiary is preserved and unsafe preparation remains blocked.
6. API/document money precision could admit sub-cent or fractional-VND values. They now fail validation before financial state promotion. Scholarship patches cannot make an unreceived notice PLANNED.
7. Session validation discarded timezone offsets. It now compares actual UTC instants; fresh PostgreSQL and proxy login persistence are tested.
8. Binary float sums could mark EUR .10 + .70 as underfunding an .80 obligation. Coverage now sums Decimal values before serialization.
9. Planned student money could appear liquid in safe-to-spend. Only already available, verified student funds enter this metric.
10. Route fee/min/max rounding and cross-currency objective precision needed conservative integer treatment. Fees round up, principal bounds use currency minor units and independent validation checks trust and route status as well as budgets/timing.
11. Reported route cost omitted FX markup. It now includes the explicit markup component and uses the label Estimated route cost.
12. Solver timeout/error results were incomplete. Failed solves now return a complete non-feasible result with no allocations; downstream stress handling is tested.
13. Installment feasibility originally omitted its fee. Fee obligations and deferred principal are preserved during evaluation and execution. Rescue now evaluates the applicable disclosed intervention families and retains every affected actor's consent.
14. APPROVE_PLAN and APPROVE_ACTION permission records needed actual behavior. Plan approval is now effective with redacted parent output; action delegation adds required consent, preserves fund owners and clears prior approvals when changed.
15. Concurrent financial mutations needed serialization before reading state. PostgreSQL advisory transaction locking and the demo ASGI mutation guard provide that boundary.
16. The initial migration depended on current Python models. It is now frozen explicit DDL; clean database upgrade and Alembic drift checking pass.
17. Demo resets could retain custom route data and change reproducibility. Unreferenced demo routes are reset while routes used by other retained plans are protected.
18. Named scenario selection had no preset effect. Omitted parameters now receive named shocks, while explicit user values including zero are respected.
19. Tuition payment UI used a hard-coded seeded ID. It now works for any confirmed tuition obligation. API regression covers new document → new obligation → approved sandbox payment.
20. Administrator document list entries could fail to open. Read authorization now matches the listed fictional demo documents; non-owned evidence remains read-only for that workflow.
21. Graph overlays/unused controls, scenario chart animation, missing errors, currency aggregation and inconsistent build/browser configuration were corrected. The eleven routes are checked at desktop and 390×844 mobile dimensions.
22. Benchmark security setup initially could fail during payment preparation without actually testing unauthorized execution. It now supplies sufficient test funding first, then attempts the unapproved action against actual APIs. Metrics are computed and exported, not constants.
23. Source formatting, portable lockfile paths, runtime benchmark dependencies, process-group cleanup, startup commands and documentation were reconciled with the executed stack.

24. Added a centralized 13-currency registry and 170 demo routes covering all 169 ordered pairs, including USD/CNY/VND. The initial pair matrix exposed source-cent versus whole-destination rounding failures; the optimizer now solves fixed-output quotes using the minimum rounded-up source debit, accounts for conversion residue, and passes every pair plus existing mathematical constraint regressions.
25. Replaced English-only presentation with persisted English/Vietnamese/Simplified Chinese selection, localized labels and financial formatting, self-hosted Chinese fonts, ISO-stable forms and translated policy messages. Evidence/account/audit payloads stay original. Browser checks cover every route and both new languages; screenshots were reviewed and remaining seeded-label/capture issues repaired.
26. A hypothetical purchase must not change the ledger. Interpretation and simulation now operate on proposals and copied state; browser tests verify unchanged balances and plans after saving an idea in all three languages. Actual events require explicit acknowledgement, an owned funding source where applicable, a confirmation note, fresh state and a separate atomic apply operation.
27. The original plan residual was not a sufficient everyday spending budget. The new budget protects verified commitments over 365 days, active allocations, fees, route timing and reserves. It excludes expected receipts and becomes zero when critical or high-priority verified funding is insufficient. The old plan residual is labelled **Unallocated in this plan**.
28. Shared bills and borrowing could misrepresent usable cash if receipts or repayment debt were omitted. Applying a shared bill debits the full expense and records its receivable separately. Borrowing records both received funds and repayment obligations atomically; expected receipts become available only after explicit T0 receipt confirmation. Replay is rejected.
29. Recorded actual expenses needed an explicit link when settling an existing budget obligation to avoid counting both the debit and unpaid bill. Full-amount, same-currency settlement is atomic and limited to owned `budget_only` obligations. Ordinary invoice/payment commitments remain subject to the original authorization workflow; the expense API cannot bypass it.
30. Missing or ambiguous amounts/dates, provider-supplied authority fields, client-cleared security flags, stale state, parent edits and cross-student access now have life-event regression coverage. Parent funding delay reports affect conservative planning assumptions without editing the parent's balance. Budget-only obligations cannot become payment destinations.
31. Recurring cost changes preserve paid history, reminders remain internal, and pausing a subscription is explicitly a simulation. Future debt remains visible in the finite budget horizon. Confirmation of a real event invalidates earlier plans/actions before it is applied.
32. The added real-expense browser test exposed a funding-selector accessibility lookup failure. An explicit accessible label repaired it. Earlier test-only failures were also corrected: the domain table expectation now includes `life_events`, and the frontend simulation mock preserves captured raw text. The full suite was rerun after repairs.

## Tests and commands actually executed

| Gate | Result |
| --- | --- |
| Backend dependency install: `uv pip install --python .venv/bin/python -r requirements.lock` | PASS |
| Frontend dependency install: `npm --prefix apps/web ci` | PASS |
| Portable PostgreSQL dependency install: `npm --prefix scripts/postgres ci` | PASS |
| `pytest -q tests` | **358 passed, 0 failed, 0 errors, 0 skipped** |
| Vitest / React Testing Library | **23 passed, 0 failed, 0 pending** |
| TypeScript `tsc --noEmit` | PASS |
| Ruff and ESLint | PASS |
| Next production build | PASS |
| Fresh PostgreSQL migration and `alembic check` | PASS, PostgreSQL 18.3 via PGlite |
| FastAPI, Next production and Next development startup | PASS |
| Direct API and Next-proxy login/me/logout | PASS on a fresh database |
| Playwright real HTTP/PostgreSQL | **11 passed, 0 failed, 0 skipped, 0 flaky** |
| FAST computed benchmark | **48 passed, 0 failed**, 4.988 seconds internal duration |
| FULL computed benchmark | **500 passed, 0 failed**, 48.769 seconds internal duration |
| Native Docker build/Compose runtime | **BLOCKED: Docker CLI/daemon unavailable** |

Exact commands, exit codes and timings are in `verification/final-results.json`; source reports are `pytest.xml`, `vitest.json` and `playwright.json`. This report does not add together benchmark cases and unit tests as independent evidence. Two upstream Python TestClient deprecation warnings remain; they are not failures. ESLint 9 emits an upstream support warning on install, while its configured lint check passes.

Eleven Playwright tests cover: the original five hero/privacy/routes/rescue/benchmark workflows; two Vietnamese and Chinese locale/currency/policy workflows; three mobile life-event purchase → computed impact → keep-idea workflows in EN/VI/ZH; and one actual shared EUR 80 expense followed by a separately confirmed EUR 40 receipt. The original eleven routes plus Life Inbox are covered across the browser suites. Screenshots in `screenshots/` were visually inspected, including the scenario before/after plot, graph inspector, repaired plan and Chinese life-event layout.

The release gate `.venv/bin/python scripts/verify.py` completed at **2026-09-25T10:55:33Z**. It passed ten configured checks; the additional Docker check was blocked, not passed. Backend/frontend/PostgreSQL dependency installation also passed. An initial offline npm installation failed because a package was absent from cache; normal `npm ci` succeeded. No failing or skipped test remains in the final reports. Benchmark IDs are `dc569435-96fe-4880-93ee-8e384174a94a` (FAST) and `b9860c99-d93b-490b-aeb5-f7085323cd22` (FULL).

## Competition evaluator view

| Required capability | Where it is actually demonstrated |
| --- | --- |
| Intent understanding and task planning | Overview intent parser and explicit task steps; labelled deterministic demo provider |
| Trustworthy facts | Documents evidence, confidence, page provenance and confirmation |
| Financial reasoning | OR-Tools plan, independent constraints and three coverage metrics |
| Cross-border relevance | 13 currencies, 169 ordered pairs, source/destination precision, route fees/FX/settlement |
| Permission control | Parent-filtered API, separate funding owners, required action approvals |
| Hallucination mitigation | Missing values stay unknown; normalized facts require valid citations |
| Prompt-injection defense | Malicious beneficiary fixture, blocked preparation, persisted security event |
| Measurable evaluation | Computed FAST/FULL runs, executable baselines and downloadable results |
| Usable product interface | Twelve connected routes in English/Vietnamese/Chinese, working forms, graph inspector, scenario controls and mobile life-event capture |
| Everyday financial impact | Private Life Inbox, purchase comparisons, actual ledger confirmation, recurring budgets, receipts and conservative runway |

**Judgment:** ready for the documented local competition sandbox demonstration. This judgment does not certify live financial use, production security, general-purpose AI extraction, real bank settlement or an unexecuted Docker deployment.

## Remaining known issues and security limits

- Native Docker/Compose was not available; PostgreSQL 16 in the Docker definition has not been runtime-tested here. The executed development engine is PostgreSQL 18.3 via PGlite.
- Local demo identity uses published passwords and no MFA/rate limiting. A public production deployment requires a separate security review and hardened identity/transport configuration.
- Text fixtures/PDFs are supported; no scanned OCR, real LLM, live FX, external bank verification or real-money action exists. T0 user attestation is not independent source attestation.
- Rescue is a finite conditional bundle search. Family receipt and institution acceptance are simulated. Future installment debt remains outside the displayed 45-day safety horizon.
- Synthetic benchmark variations do not establish real-world adversarial success rates or universal optimizer optimality. Timeout results are labelled conservatively.
- Audit immutability is application/database level; a privileged host/database operator remains trusted.
- Partial allocations explain gaps; sandbox payment execution requires a complete verified obligation. No generic partial settlement workflow is claimed.
- Dependency deprecation/support warnings require maintenance before long-term use; no production load or failover testing was performed.
- Life-event understanding is a bounded deterministic EN/VI/ZH parser, not general free-form model intelligence. Ambiguous facts require review; its confidence is a heuristic, not calibrated accuracy.
- The life budget and recurring schedule use a finite 365-day window; there is no background extension of that schedule. Runway uses recorded essential costs and explicitly cannot account for unreported living expenses.
- Personal expense and receipt confirmation is user attestation in a simulated ledger, not bank reconciliation. Internal reminders do not send external notifications or cancel subscriptions. Shared-bill receipts are tracked separately until confirmed.
- Life-event regressions are separate from FAST/FULL's existing synthetic families. Their passing results do not establish real-world language accuracy, fraud detection or universal financial safety.

## Extension implementation map

| Area | Implemented source |
| --- | --- |
| Domain and migration | `lattice_core/models.py`, frozen `migrations/versions/0002_life_events.py`; 17 tables total, new `life_events` plus obligation `budget_only` |
| Interpretation | `lattice_ai/life/interpretation.py`, trilingual examples and proposal-only provider interface |
| Financial logic | `lattice_core/life/` schemas, budget, copied-state effects, analysis, versioned service and inbox reminders |
| API | `apps/api/routes_life.py`; `/life-events`, interpret/simulate/confirm/apply/receipt/resolution controls, `/life-inbox`, `/purchase-check`, `/safe-to-spend`, `/runway` |
| UI | `apps/web/components/life/`, `apps/web/lib/life.ts`, global capture, `/life`, Overview summary and EN/VI/ZH catalog updates |
| Regression evidence | Four `tests/test_life_*.py` files, `apps/web/tests/life.test.tsx`, `apps/web/e2e/life.spec.ts` |

The endpoint payloads and all lifecycle routes are documented in `api.md`; the Vietnamese operating guide is `LIFE_EVENTS_GUIDE_VI.md`.

## Exact local startup and Maya procedure

After the README dependency installation and build:

```bash
cd /workspace/lattice
.venv/bin/python scripts/dev.py --portable-postgres --production
```

Open http://localhost:3000. Sign in as Demo administrator → **Reset Maya** → switch to Maya Student. Follow Documents → confirm facts → Plan → Graph → Scenario Lab (14-day scholarship delay) → apply delay → Rescue Center → prepare → observe approval block → Documents malicious update → payment preparation block → Audit Security. For a successful repair, reset and approve the proposed action as each required actor before executing as Student. All accounts use `LatticeDemo2026!`; emails are documented in README.

For the life-event extension, select Tiếng Việt or 简体中文 → **Tell LATTICE** → choose a purchase example → inspect the computed impact → **Keep as idea**. Life Inbox shows the record while balances and plans are unchanged. For a real expense, choose **I bought it**, an owned source, actual date, note and acknowledgement → confirm → apply to the sandbox ledger. The shared-bill example creates its expected reimbursement separately. Maya's initial safe budget is zero because verified funds do not cover all critical commitments; this is the intended conservative result.

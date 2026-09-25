# Threat model and observed controls

The threat model is an untrusted document, malicious financial instruction, tampered request or authenticated actor exceeding resource permissions. The demonstration is local, uses public fictional demo accounts and executes no real money. The database operator and host are trusted boundaries.

| Attempt | Implemented control | Actual regression coverage |
| --- | --- | --- |
| Direct prompt injection | Intent output has no financial capability; flagged instruction is review-only | `test_direct_injection_cannot_authorize` and benchmark security |
| PDF/text indirect injection | Output-only extraction, schema validation, citation validation; flags block promotion | `test_document_attacks_do_not_overwrite`, PDF API tests |
| Valid quote but forged normalized amount/date/currency/account | Independently compare normalized value to cited field and raw value | Parameterized provenance regression |
| Amount, due-date or conflicting document replacement | Existing verified obligation cannot be overwritten by document confirmation | API document attack cases |
| Beneficiary substitution or Unicode/homoglyph/zero-width spoof | Exact ASCII identifier validation; detected proposal sets a hold while retaining original beneficiary | API and Unicode security regressions |
| False scholarship or urgency | A confirmed notice remains EXPECTED; urgency grants no action authority | False-scholarship and injection cases |
| Fractional VND or sub-cent input | Currency minor-unit validation in forms/API and extracted-document promotion | Money precision and VND document regressions |
| Parent privilege escalation, unrelated student IDs | Per-resource owner/grant checks in API; private plans/scenarios/rescue denied | API isolation, graph filtering, actual browser HTTP tests |
| Leak in funding mutation result | Parent/sponsor response excludes private replacement-plan snapshots | Parent create/patch regression |
| Student sees unshared parent's finances via graph/plan | State builder respects explicit funding visibility | Unshared parent-source regression |
| Forged action amount or beneficiary | Request schemas forbid extra fields; server derives allocation/account from state | Mass-assignment/action payload tests |
| Execute without approval | Required actors, current state hash and action status checked server-side | API/Playwright negative execution and benchmark case |
| Delegation replaces owner approval | Base fund owners remain mandatory; grants/revokes clear approval set | Delegated approval regression |
| Stale or duplicate execution | Mutation invalidates plans/actions; unique executed state refuses replay | Successful multi-actor rescue/replay tests |
| Invalid route, overdraw, reserve spending, late arrival | Integer CP-SAT hard constraints plus separate validator | Deterministic optimizer adversarial cases |
| Session timezone offset | Compare actual UTC instants, preserving timezone offset | Four session expiry regressions plus fresh PostgreSQL login/me/logout |
| Audit mutation | Database triggers reject UPDATE/DELETE; hash chain verified | API tamper/reset test; PostgreSQL hero audit events |

## Evidence and trust

T0 is explicit user authority. T1 represents an institution/financial source verified by a trusted connector; no live T1 attestation connector is implemented. T2 is a user-provided trusted document; T3 unverified document/email; T4 open text. Upload API permits only T2–T4 and cannot self-promote a document to T0/T1. Demo routes use SOURCE_VERIFIED to mean a configured deterministic fixture, not live verification.

No evidence means no financial fact promotion. Unknown fields stay absent and are shown as missing rather than fabricated. Conflicted/unsafe facts cannot be confirmed through the generic confirmation endpoint. A beneficiary can only be explicitly re-attested through a separate endpoint requiring repeated matching identifiers and a confirmation note; the audit labels it user authority, not independent bank verification.

## Privacy boundaries

A parent initially sees only their VND source, shared tuition, own documents, own approval details and relevant own permission/action events. Student-only documents, balances, spending commitments, scenarios, plans and rescue results are not obtainable by guessing IDs. Student access to family funding also requires an explicit sharing permission. ADMIN_DEMO is intentionally privileged for fictional Maya setup and simulated institutional consent.

## Remaining limitations

- Demo passwords and actor-switch login are intentionally public. This is not production authentication. No MFA, throttling, password recovery, production identity provider or hardened account enrollment exists.
- Keyword injection detection is illustrative; security rests on capability separation and policy, not perfect classification. Tests cover known synthetic families, not every adversarial prompt or parser exploit.
- Text PDF extraction is not a full document isolation platform. Scanned PDFs are rejected with an OCR-unavailable message. A hostile public deployment needs parser resource isolation, request-size enforcement at a reverse proxy, rate limits and malware controls.
- T0 user confirmation can be mistaken or dishonest. No bank/institution independently attests entered balances or beneficiaries.
- Mock funding receipts and institution approval cannot establish real-world settlement or legal authorization. P4 does not exist.
- Hash chaining and application/database triggers do not stop a database administrator from disabling controls or rewriting history. There is no external timestamp or append-only third-party ledger.
- PostgreSQL mutations are serialized, but no production load, distributed failover or formal verification has been performed. Docker runtime could not be executed in this workspace.
- Two installed TestClient dependencies emit deprecation warnings; ESLint 9 emits an upstream support warning during install. Current tests and lint still execute. These require dependency maintenance before long-lived production use.

## Multilingual presentation and currency extension

Interface translations never mutate extracted evidence, beneficiaries, API enums or monetary values. Locale preference is not an authorization input. Deterministic injection heuristics include a bounded set of Vietnamese and Chinese phrases; this is not a claim of general multilingual attack detection. The structural extraction/approval boundary applies independently of language and heuristic matches. All supported currencies use central minor-unit validation and the optimizer independently checks conservation, source spending, timing, reserves and ownership.

## Life-event attack surface

- All LifeEvent, Life Inbox, safe-budget and runway routes call the private student authorization gate. Cross-student IDs return 404; parent and sponsor roles receive 403. Funding links are separately checked for scope and visibility. Spending another actor's funds is forbidden even when a contribution is shared.
- Provider output is validated against a strict schema without ownership/trust/action fields. Original detected security flags are retained server-side across edits. Document/account text cannot clear a verified beneficiary, promote a scholarship, invoke a tool or create an approved action.
- A monetary receipt is explicit user attestation, not external verification. A dishonest user can misstate their own finances under this prototype's T0 trust boundary; the UI and documentation disclose this. There is no independent bank reconciliation or real payment execution.
- Confirmed pending events invalidate old actions and enter conservative budget projections. Apply checks the event version, unchanged financial snapshot, source eligibility, route timing/fees and protected balances. Shared expenses and loans are atomic; receipt/application replay is rejected.
- Generic dismissal cannot reverse applied debits, delete a repayment, or cancel received money. Subscription price changes preserve paid rows; reminder toggles do not cancel merchant contracts. Account-unavailability reports retain bank amounts.
- `budget_only` obligations with unknown beneficiaries may reserve funds but can never prepare a payment. The source APIs cannot be used to turn this flag into payment authority.
- EN/VI/ZH detection is a bounded demonstration defense, not a guarantee that regex detects every malicious phrase. The security boundary is schema/capability separation and explicit policy, not detection confidence.
- The demo is serialized and intended for small student workspaces. No load/SLA claim is made for a large event history, many annual recurrences, or adversarial CPU exhaustion; production rate limits and quotas are not implemented.

- Explicit settlement of an existing life-budget obligation requires full matching amount/currency and remains atomic with the debit. Ordinary invoice/payment obligations cannot be settled through this shortcut; trying to use an expense attestation to bypass action approvals returns 403.

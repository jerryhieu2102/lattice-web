# Computed evaluation

`python -m benchmark.run --mode FAST|FULL` generates deterministic ground truth, calls the actual implementation, measures elapsed time with `perf_counter`, persists JSON/CSV and returns a nonzero exit code if any case fails. The Benchmark screen invokes the same runner through the API and shows the stored run ID, timestamp, mode, seed, cases, metrics and baselines. Before the first stored run, it shows an empty state.

## Dataset and oracle

FAST has 12 extraction, 12 planning, 12 replanning and 12 security cases (48). FULL has 125 of each (500). Seed defaults to 17. Generated monetary amounts and dates vary within synthetic families. This is not a real-world statistical sample; repeatability and regression value are the goals.

- Extraction uses independently generated labelled truth, including missing critical fields. The mock provider generates labelled documents from that truth, then the extraction parser proposes fields. A separate provenance validator checks quoted fields, raw values, page/block and normalized values. This fixture round trip measures the supported labelled format, not general OCR/LLM intelligence.
- Planning uses generated one-obligation states across insufficient/exact funding, multi-currency route conversion, fees, deadlines, scholarship delay, reserve protection, parent authority, uncertainty, trust, route minimums and source restrictions. An independent Decimal capacity oracle computes nominal and certain coverage without calling the optimizer. Broader multiple-obligation graphs and invariants are tested in pytest and Maya E2E.
- Replanning first computes a plan, delays scholarship arrival, confirms that nominal feasibility breaks, then calls the actual rescue planner. Recovery requires a feasible installment candidate, no additional family funds for this generated family, preserved original input and the disclosed institution fee. It measures conditional repair after simulated acceptance.
- Security uses original FastAPI routers, cookie authentication, policy and database operations in an isolated SQLite application. It does not replace the running server's dependency overrides. Each case resets fictional data and attempts a real unauthorized or malicious API operation. Playwright separately exercises PostgreSQL and HTTP transport.

## Metrics

| Group | Metric | Computation |
| --- | --- | --- |
| Extraction | Amount/Currency/Deadline/Beneficiary Accuracy | Fraction of cases where extracted value or absence equals generated truth |
| Extraction | Evidence Precision | Supported proposed evidence / all proposed evidence |
| Extraction | Unsupported Critical Fact Rate | Unsupported or unexpected critical proposals / critical proposals |
| Planning | Critical Obligation Coverage | Mean nominal coverage in generated critical cases, including infeasible cases |
| Planning | On-Time Coverage | Mean verified coverage arriving before deadline |
| Planning | Constraint Violations | Total independent validator violations |
| Planning | Mean Total Cost | Mean computed route fees, FX markup and rounding residue, demo EUR units |
| Replanning | Recovery Success Rate | Generated cases meeting stated conditional repair checks / cases |
| Replanning | Mean Intervention Cost | Mean explicit installment/direct intervention fee for selected repair |
| Replanning | Mean Replanning Time | Mean measured case duration including before/after optimization and repair search |
| Security | Unauthorized Action Rate | Successful unauthorized operations / unauthorized attempts |
| Security | Prompt Injection Success Rate | Injection attempts causing prohibited state effects / injection attempts |
| Security | Unsupported Critical Fact Rate | Unsupported promoted critical facts / proposed critical facts |
| Security | Unverified Beneficiary Auto-Change Count | Actual changed trusted beneficiaries caused by untrusted proposals |

A case can pass with less than 100% coverage when ground truth is insufficient funding. Passing means matching the expected outcome while obeying the constraints; it does not mean every generated student can pay every bill. Baseline violations are deliberately reported rather than hidden.

## Executable baselines

| Baseline | Behavior |
| --- | --- |
| B0 balance-only | Allocates aggregate resources without fees, trust, permissions or deadline policy |
| B1 earliest-deadline greedy | Orders obligations by due date and prefers fast routes; incomplete policy checks |
| B2 cheapest-route greedy | Orders route choices by quoted fixed fee; incomplete timing/policy checks |
| B3 generic planner approximation | Simple deterministic heuristic avoiding some restricted/unverified sources; no external model call |
| B4 full LATTICE | Actual OR-Tools plan, then independent validation |

These are transparent demo approximations, not claims about any commercial planner or language model. JSON contains per-case truth, measured result, pass/fail and time. CSV contains one row per case with the same run ID and detail JSON.

## Latest verified run

Read `benchmark/results/fast.json`, `full.json` and `docs/verification/final-results.json` for exact machine-readable run IDs and timings. The final audit on 2026-09-25 computed FAST 48/48 in 4.988 seconds and FULL 500/500 in 48.769 seconds, with zero failed cases. Times are environment-specific and exclude CLI import/startup overhead in the benchmark's internal duration.

## Scope of conclusions

The synthetic suite shows deterministic execution, known attack-family defenses, correctness for the generated oracle shape and regression consistency. It does not estimate real-world fraud detection quality, generalized document understanding, bank settlement probability, global rescue optimality or production concurrency. Scenario Failure Rate is a sensitivity result under chosen distributions; it is not a real-world probability.

## Currency and locale regressions

The separate pytest matrix exercises every one of the 169 ordered supported currency pairs, exact destination amounts, minor-unit conservation and the independent hard-constraint validator. API tests cover new-currency evidence, CNY-to-VND sandbox payment, required approvals, zero-decimal rejection and Vietnamese/Chinese intent/injection examples. These are regression tests, not extra FAST/FULL cases. Browser tests run all eleven routes in Vietnamese and Chinese at a 390-pixel mobile width, verify locale persistence, currency-pair selection, form ISO payloads, cross-currency optimization and unchanged security gates.

## Life Event Layer regressions

Life-event tests are separate from the unchanged FAST/FULL synthetic benchmark denominator. Pytest exercises EN/VI/ZH interpretation, null/ambiguous facts, monetary precision, capability rejection, expense confirmation/replay, expected receipts, atomic shared bills and debt, conservative family-delay projections, preserved reserves, account availability, recurring costs/paid history, private tenant access and reminder derivation. Frontend tests cover capture/inbox, language changes with preserved data, explicit acknowledgement and zero-decimal input validation. Browser tests exercise capture → real computed impact → keep idea in all three languages and a separate actual shared expense/receipt lifecycle over PostgreSQL. The reports record actual counts; no new language-understanding accuracy percentage is invented.

The complete release suite contains **358 backend tests, 23 frontend tests and 11 browser workflows**, all passing with zero skipped tests. Those counts include existing core/currency/localization regressions. Full matched settlement of a budget obligation is covered alongside rejection of an attempt to bypass ordinary payment approvals through an expense record.

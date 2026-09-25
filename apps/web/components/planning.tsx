"use client";
import { useI18n } from "@/lib/i18n/context";
import Link from "next/link";
import { useState } from "react";
import {
  ArrowRight,
  Play,
  ShieldCheck,
  RefreshCw,
  Clock3,
  LifeBuoy,
  Check,
} from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import { api } from "@/lib/api";
import { useData, useTask } from "@/lib/hooks";
import type {
  Actor,
  Notify,
  Plan,
  Funding,
  Scenario,
  Candidate,
  Route,
} from "@/lib/types";
import {
  Badge,
  Empty,
  Loading,
  PageHeader,
  Metric,
  CoverageTable,
  Notice,
} from "./ui";
import { ActionsPanel } from "./actions";
type Props = { actor: Actor; notify: Notify };
export function PlanPage({ actor, notify }: Props) {
  const { t, money, percent, label, date } = useI18n();

  const query = useData<Plan[]>("plans", "/plans");
  const funds = useData<Funding[]>("funding", "/funding-sources");
  const routes = useData<Route[]>("routes", "/transfer-routes");
  const { busy, run } = useTask(notify);
  const [version, setVersion] = useState("");
  const plan = query.data?.find((p) => p.id === version) || query.data?.[0];
  return (
    <>
      <PageHeader
        eyebrow={t("02 / DETERMINISTIC PLANNING")}
        title={t("A plan you can trace.")}
        description={t(
          "Every allocation follows funding, timing, reserve, and permission constraints.",
        )}
        action={
          <button
            className="button primary"
            disabled={busy}
            onClick={() =>
              run(
                () => api("/plans/generate", "POST"),
                "A new optimized plan is ready.",
              )
            }
          >
            <RefreshCw size={16} />
            {t("Generate optimized plan")}
          </button>
        }
      />
      {query.isPending ? (
        <Loading />
      ) : query.error ? (
        <Notice danger>{query.error.message}</Notice>
      ) : !plan ? (
        <Empty title={t("Generate your first plan")}>
          {t("Start with confirmed commitments and funding sources.")}
        </Empty>
      ) : (
        <>
          <div className="plan-bar">
            <div>
              <Badge value={plan.status} />
              <span>
                {t("Version")} {plan.version} ·{" "}
                {label(plan.summary.solver_status)} {t("· through")}{" "}
                {date(plan.summary.horizon_end)}
              </span>
            </div>
            <div className="toolbar">
              <select
                aria-label={t("Plan version")}
                value={plan.id}
                onChange={(e) => setVersion(e.target.value)}
              >
                {query.data?.map((p) => (
                  <option key={p.id} value={p.id}>
                    {t("Version")} {p.version} · {label(p.status)}
                  </option>
                ))}
              </select>
              <button
                className="button small"
                disabled={busy || plan.status === "STALE"}
                onClick={() =>
                  run(
                    () => api("/plans/" + plan.id + "/activate", "POST"),
                    "Working plan activated. Payment approval remains separate.",
                  )
                }
              >
                <Check size={14} />
                {t("Activate plan")}
              </button>
            </div>
          </div>
          {plan.status === "STALE" && (
            <Notice danger>
              {t(
                "This plan was invalidated by a financial or permission change. Review the newest version.",
              )}
            </Notice>
          )}
          <div className="metrics three">
            <Metric
              label={t("Estimated route cost")}
              value={money(plan.summary.total_estimated_cost)}
              detail={t("Deterministic demo quotes")}
            />
            <Metric
              label={t("Hard constraint violations")}
              value={String(plan.summary.constraint_violations)}
              detail={t("Checked independently after solving")}
            />
            <Metric
              label={t("Scenario failure rate")}
              value={
                plan.stress_failure_rate === null
                  ? t("Not run")
                  : percent(plan.stress_failure_rate)
              }
              detail={t("Sensitivity result, not real-world probability")}
            />
          </div>
          <section className="panel">
            <h2>{t("Coverage by commitment")}</h2>
            <CoverageTable coverage={plan.summary.coverage} />
          </section>
          <div className="allocation-grid">
            {plan.summary.coverage
              .filter((c) => c.in_horizon)
              .map((c) => (
                <section className="panel" key={c.obligation_id}>
                  <div className="panel-heading">
                    <div>
                      <span className="eyebrow">{date(c.due_date)}</span>
                      <h2>{t(c.label)}</h2>
                    </div>
                    <strong>{money(c.amount, c.currency)}</strong>
                  </div>
                  <div className="allocation-tree">
                    {plan.summary.allocations
                      .filter((a) => a.obligation_id === c.obligation_id)
                      .map((a, i) => (
                        <div className="allocation" key={i}>
                          <div className="allocation-point" />
                          <div>
                            <strong>
                              {t(
                                funds.data?.find(
                                  (f) => f.id === a.funding_source_id,
                                )?.label || a.funding_source_id,
                              )}
                            </strong>
                            <small>
                              {t(
                                routes.data?.find(
                                  (r) => r.id === a.transfer_route_id,
                                )?.provider_name || a.transfer_route_id,
                              )}
                            </small>
                            <small>
                              {t("Send")} {date(a.scheduled_date)}{" "}
                              {t("→ arrive")} {date(a.expected_arrival_date)}
                            </small>
                            <small>
                              {t("Source debit")}:{" "}
                              {money(
                                a.source_amount + a.estimated_fee,
                                a.source_currency,
                              )}{" "}
                              · {t("Fee")}:{" "}
                              {money(a.estimated_fee, a.source_currency)}
                            </small>
                            <small>
                              {t("Rounding cost (demo EUR)")}:{" "}
                              {money(a.estimated_rounding_cost_eur || 0)}
                            </small>
                          </div>
                          <div>
                            <strong>
                              {money(a.destination_amount, a.currency)}
                            </strong>
                            <Badge value={a.status} />
                          </div>
                        </div>
                      ))}
                    {c.shortfall > 0 && (
                      <div className="gap-row">
                        {t("Verified gap")}{" "}
                        <strong>{money(c.shortfall, c.currency)}</strong>
                      </div>
                    )}
                  </div>
                  {c.type === "TUITION" && (
                    <button
                      className="button full"
                      disabled={busy}
                      onClick={() =>
                        run(
                          () =>
                            api("/actions/prepare", "POST", {
                              type: "TUITION_PAYMENT",
                              plan_id: plan.id,
                              obligation_id: c.obligation_id,
                            }),
                          "Tuition payment prepared in the sandbox.",
                        )
                      }
                    >
                      <ShieldCheck size={15} />
                      {t("Prepare tuition payment")}
                    </button>
                  )}
                </section>
              ))}
          </div>
          <Notice>{t(plan.explanation)}</Notice>
        </>
      )}
      <ActionsPanel actor={actor} notify={notify} />
    </>
  );
}
export function ScenarioPage({ notify }: Props) {
  const { t, money, percent, number } = useI18n();

  const query = useData<Plan[]>("plans", "/plans");
  const funding = useData<Funding[]>("funding", "/funding-sources");
  const { busy, run } = useTask(notify);
  const [controls, setControls] = useState({
    scholarship_delay: 7,
    transfer_delay: 2,
    fx_shock: 3,
    unexpected_expense: 0,
  });
  const [result, setResult] = useState<Scenario | null>(null);
  const plan = query.data?.[0];
  const fields = [
    ["scholarship_delay", "Scholarship delay", 21, "days"],
    ["transfer_delay", "Transfer delay", 7, "days"],
    ["fx_shock", "FX shock", 10, "%"],
    ["unexpected_expense", "Unexpected expense", 2000, "EUR"],
  ] as const;
  async function test() {
    if (!plan) return;
    const r = await run(
      () =>
        api<Scenario>("/plans/" + plan.id + "/simulate", "POST", {
          ...controls,
          scenario: "COMBINED_STRESS",
          iterations: 1000,
          seed: 17,
        }),
      "1,000 deterministic scenario iterations computed.",
    );
    if (r) setResult(r);
  }
  async function delay() {
    const f = funding.data?.find((f) => f.id === "scholarship");
    if (!f) return;
    const d = new Date(f.available_from + "T00:00:00Z");
    d.setUTCDate(d.getUTCDate() + controls.scholarship_delay);
    await run(
      () =>
        api("/funding-sources/scholarship", "PATCH", {
          available_from: d.toISOString().slice(0, 10),
          confirmation_note: "Explicit sandbox scholarship delay event",
        }),
      "Plan invalidated. A new version and scenario comparison were generated.",
    );
  }
  const chart =
    result?.baseline_coverage
      .filter((c) => c.in_horizon)
      .map((c) => ({
        name: t(c.label),
        before: Math.round(c.nominal * 100),
        after: Math.round(
          (result.after_coverage.find(
            (a) => a.obligation_id === c.obligation_id,
          )?.on_time_nominal || 0) * 100,
        ),
      })) || [];
  return (
    <>
      <PageHeader
        eyebrow={t("03 / STRESS")}
        title={t("What if the timing changes?")}
        description={t(
          "Test a plan against delays, FX movement, and unexpected expenses before they happen.",
        )}
        action={
          <button
            className="button primary"
            onClick={test}
            disabled={busy || !plan}
          >
            <Play size={16} />
            {t("Run stress test")}
          </button>
        }
      />
      {!plan && (
        <Notice>
          {t("Generate a plan first.")}{" "}
          <Link href="/plan">
            {t("Open Plan")}
            <ArrowRight size={14} />
          </Link>
        </Notice>
      )}
      <div className="scenario-layout">
        <section className="panel scenario-controls">
          <span className="eyebrow">{t("SCENARIO PARAMETERS")}</span>
          <h2>
            {t("A little uncertainty.")}
            <br />
            {t("A different outcome.")}
          </h2>
          {fields.map(([key, title, max, unit]) => (
            <label className="slider" key={key}>
              <span>
                {t(title)}
                <strong>
                  {controls[key]} {t(unit)}
                </strong>
              </span>
              <input
                aria-label={t(title)}
                type="range"
                min="0"
                max={max}
                step={key === "unexpected_expense" ? 50 : 1}
                value={controls[key]}
                onChange={(e) =>
                  setControls({ ...controls, [key]: Number(e.target.value) })
                }
              />
              <small>
                <span>0 {t(unit)}</span>
                <span>
                  {max} {t(unit)}
                </span>
              </small>
            </label>
          ))}
          <div className="scenario-method">
            <ShieldCheck size={17} />
            <p>
              {t(
                "1,000 seeded iterations. Results measure failure under the selected assumptions, not actuarial probability.",
              )}
            </p>
          </div>
        </section>
        <div>
          <section className="panel scenario-chart">
            <div className="panel-heading">
              <div>
                <span className="eyebrow">{t("BEFORE / AFTER")}</span>
                <h2>{t("Can the forecast arrive on time?")}</h2>
              </div>
              <span className="count">{t("% covered")}</span>
            </div>
            {result ? (
              <>
                <div className="chart">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chart} barGap={6}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} />
                      <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                      <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
                      <Tooltip formatter={(v) => `${v}%`} />
                      <Legend />
                      <Bar
                        isAnimationActive={false}
                        dataKey="before"
                        name={t("Baseline nominal")}
                        fill="#bbd8cf"
                        radius={[4, 4, 0, 0]}
                      />
                      <Bar
                        isAnimationActive={false}
                        dataKey="after"
                        name={t("Stressed on-time forecast")}
                        fill="#267d67"
                        radius={[4, 4, 0, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <p className="caption">
                  {t(
                    "Forecast includes expected income; it does not certify verified coverage. The after bars apply the maximum selected shocks.",
                  )}
                </p>
              </>
            ) : (
              <Empty title={t("Run your first stress test")}>
                {t(
                  "Change the assumptions on the left, then compare the computed results here.",
                )}
              </Empty>
            )}
          </section>
          {result && (
            <div className="metrics three">
              <Metric
                label={t("Verified scenario failure")}
                value={percent(result.scenario_failure_rate)}
                detail={t("Includes existing verified shortfalls")}
              />
              <Metric
                label={t("Forecast failure")}
                value={percent(result.forecast_failure_rate)}
                detail={t("Assumes expected funds are received")}
              />
              <Metric
                label={t("95th percentile shortfall")}
                value={money(result.p95_shortfall_eur)}
                detail={`${number(result.iterations)} computed iterations`}
              />
            </div>
          )}
          <section className="apply-event">
            <div className="event-icon">
              <Clock3 />
            </div>
            <div>
              <span className="eyebrow">
                {t("TURN A SCENARIO INTO AN EVENT")}
              </span>
              <h2>{t("The scholarship is delayed.")}</h2>
              <p>
                {t(
                  `Apply a ${controls.scholarship_delay}-day delay to Maya’s financial state. The current plan will become stale and be recalculated.`,
                )}
              </p>
            </div>
            <button
              className="button"
              disabled={busy || !plan || !controls.scholarship_delay}
              onClick={delay}
            >
              {t("Apply scholarship delay")}
              <ArrowRight size={16} />
            </button>
          </section>
          <Link href="/rescue" className="text-link">
            {t("Find a minimal repair in Rescue Center")}
            <ArrowRight size={16} />
          </Link>
        </div>
      </div>
    </>
  );
}
export function RescuePage({ actor, notify }: Props) {
  const { t, money, percent, label } = useI18n();

  const { busy, run } = useTask(notify);
  const [result, setResult] = useState<{
    shortfall_eur: number;
    candidates: Candidate[];
    best_index: number | null;
  } | null>(null);
  async function generate() {
    const r = await run(
      () => api<typeof result>("/rescue/generate", "POST"),
      "Rescue alternatives evaluated using the optimizer.",
    );
    if (r) setResult(r);
  }
  return (
    <>
      <PageHeader
        eyebrow={t("04 / REPAIR")}
        title={t("The smallest change that helps.")}
        description={t(
          "Compare conditional repairs by financial cost, family contribution, reserve impact, and friction.",
        )}
        action={
          <button className="button primary" disabled={busy} onClick={generate}>
            <LifeBuoy size={16} />
            {t("Generate rescue plan")}
          </button>
        }
      />
      <Notice>
        {t(
          "Repairs are proposals until all affected actors approve. The best option is the lowest score among the evaluated bundles; it is not a promise of institutional acceptance.",
        )}
      </Notice>
      {!result ? (
        <Empty title={t("Explore a repair")}>
          {t(
            "Generate alternatives from the current plan. Installments are evaluated alongside additional funding and explicit reserve release.",
          )}
        </Empty>
      ) : (
        <>
          <div className="rescue-summary">
            <span>{t("Current verified critical gap")}</span>
            <strong>{money(result.shortfall_eur)}</strong>
            <small>
              {t(
                "Expected income cannot close this verified gap until received.",
              )}
            </small>
          </div>
          <div className="rescue-grid">
            {result.candidates.map((c, index) => (
              <article
                key={c.id}
                className={`panel rescue-card ${index === result.best_index ? "recommended" : ""}`}
              >
                <div className="card-top">
                  <span className="rank">0{index + 1}</span>
                  <Badge
                    value={c.feasible ? "CONDITIONAL_REPAIR" : "INFEASIBLE"}
                  />
                </div>
                {index === result.best_index && (
                  <div className="best-label">
                    <Check size={13} />
                    {t("MINIMUM EVALUATED SCORE")}
                  </div>
                )}
                <h2>{label(c.type)}</h2>
                <div className="rescue-cost">
                  {money(c.direct_cost_eur)}
                  <span>{t("direct fees")}</span>
                </div>
                <dl>
                  <div>
                    <dt>{t("Additional family funds")}</dt>
                    <dd>{money(c.family_contribution_eur)}</dd>
                  </div>
                  <div>
                    <dt>{t("Reserve released")}</dt>
                    <dd>{money(c.reserve_impact_eur)}</dd>
                  </div>
                  <div>
                    <dt>{t("People involved")}</dt>
                    <dd>{c.people_involved}</dd>
                  </div>
                  <div>
                    <dt>{t("Scenario failure rate")}</dt>
                    <dd>{percent(c.scenario_failure_rate)}</dd>
                  </div>
                  <div>
                    <dt>{t("Evaluation score")}</dt>
                    <dd>{c.score}</dd>
                  </div>
                </dl>
                <div className="assumptions">
                  {c.assumptions.map((a) => (
                    <p key={a}>
                      <ShieldCheck size={14} />
                      {t(a)}
                    </p>
                  ))}
                </div>
                <button
                  className="button full primary"
                  disabled={busy || !c.feasible}
                  onClick={() =>
                    run(
                      () =>
                        api("/actions/prepare", "POST", {
                          type: "APPLY_RESCUE",
                          plan_id: c.plan_id,
                          candidate_id: c.id,
                        }),
                      "Intervention prepared. Required approvals are listed below.",
                    )
                  }
                >
                  {t("Prepare intervention")}
                  <ArrowRight size={16} />
                </button>
              </article>
            ))}
          </div>
        </>
      )}
      <ActionsPanel actor={actor} notify={notify} />
    </>
  );
}

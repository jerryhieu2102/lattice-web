"use client";
import { useI18n } from "@/lib/i18n/context";
import Link from "next/link";
import { useState } from "react";
import { z } from "zod";
import {
  ArrowRight,
  Plus,
  ShieldCheck,
  Globe2,
  Clock3,
  LockKeyhole,
  Check,
} from "lucide-react";
import { api } from "@/lib/api";
import { useData, useTask } from "@/lib/hooks";
import type { Actor, Notify, Plan, Funding, Obligation } from "@/lib/types";
import {
  Badge,
  Empty,
  Loading,
  PageHeader,
  Metric,
  CoverageTable,
  Notice,
} from "./ui";
import { CurrencySelect, useCurrencies } from "@/lib/currencies";
import { TransferRoutes } from "./transfer-routes";
type Props = { actor: Actor; notify: Notify };
export function Overview({ notify }: Props) {
  const { t, money, percent, label } = useI18n();

  const currencyData = useCurrencies();
  const { demoEur } = currencyData;
  const plans = useData<Plan[]>("plans", "/plans");
  const funds = useData<Funding[]>("funding", "/funding-sources");
  const obligations = useData<Obligation[]>("obligations", "/obligations");
  const { busy, run } = useTask(notify);
  const [intent, setIntent] = useState<string | undefined>();
  const intentText =
    intent ?? t("Can my verified funds cover tuition and housing on time?");
  const [steps, setSteps] = useState<string[]>([]);
  if (
    plans.isPending ||
    funds.isPending ||
    obligations.isPending ||
    currencyData.isPending
  )
    return <Loading />;
  if (plans.error || funds.error || obligations.error || currencyData.error)
    return (
      <Notice danger>
        {
          (
            plans.error ||
            funds.error ||
            obligations.error ||
            currencyData.error
          )?.message
        }
      </Notice>
    );
  const plan = plans.data?.[0];
  const coverage = plan?.summary.coverage.filter((c) => c.in_horizon) || [];
  const amounts = coverage.reduce(
    (a, c) => a + demoEur(c.amount, c.currency),
    0,
  );
  const rate = (key: "nominal" | "verified" | "on_time_verified") =>
    amounts
      ? coverage.reduce(
          (a, c) => a + demoEur(c.amount, c.currency) * c[key],
          0,
        ) / amounts
      : 0;
  const safe = plan?.summary.verified_feasible && plan.status !== "STALE";
  const failed =
    !!plan &&
    !plan.summary.allocations.length &&
    coverage.some((c) => c.priority === "CRITICAL");
  return (
    <>
      <PageHeader
        eyebrow={t("FINANCIAL CLARITY, ACROSS BORDERS")}
        title={t("Your next commitments, accounted for.")}
        description={t(
          "A balance tells you what you have. LATTICE verifies what you can cover.",
        )}
        action={
          <button
            className="button primary"
            disabled={busy || !obligations.data?.length}
            onClick={() =>
              run(
                () => api("/plans/generate", "POST"),
                "Optimized plan generated from current evidence.",
              )
            }
          >
            <Globe2 size={16} />
            {plan ? t("Regenerate plan") : t("Generate optimized plan")}
          </button>
        }
      />
      <section className="overview-hero">
        <div>
          <div className="eyebrow">{t("FINANCIAL PLAN / NEXT 45 DAYS")}</div>
          <div className="hero-status">
            <span className={`large-dot ${safe ? "safe" : ""}`} />
            <h2>
              {!plan
                ? t("Ready to verify")
                : safe
                  ? t("Covered, with evidence.")
                  : t("Your plan needs attention.")}
            </h2>
          </div>
          <p>
            {!plan
              ? t(
                  "Start with your documents, then build a plan from verified facts.",
                )
              : t(
                  `${coverage.filter((c) => c.priority === "CRITICAL" && c.on_time_verified < 1).length} critical commitments have a verified coverage gap. Expected scholarship income is kept separate.`,
                )}
          </p>
          <div className="hero-links">
            <Link href="/plan">
              {t("Review plan")}
              <ArrowRight size={16} />
            </Link>
            <Link href="/rescue">
              {t("Explore a repair")}
              <ArrowRight size={16} />
            </Link>
          </div>
        </div>
        <div className="hero-aside">
          <ShieldCheck size={29} />
          <span>{t("PLAN STATUS")}</span>
          <strong>
            {!plan
              ? t("NOT GENERATED")
              : safe
                ? t("SAFE")
                : failed
                  ? t("FAILED")
                  : t("AT RISK")}
          </strong>
          <small>
            {plan
              ? t(
                  `Version ${plan.version} · ${label(plan.summary.solver_status)}`,
                )
              : t("Evidence → allocation → approval")}
          </small>
        </div>
      </section>
      <div className="metrics">
        <Metric
          label={t("Nominal coverage")}
          value={percent(rate("nominal"))}
          detail={t("Forecast allocations · demo EUR weights")}
        />
        <Metric
          label={t("Verified coverage")}
          value={percent(rate("verified"))}
          detail={t("Verified, authorized funding only")}
        />
        <Metric
          label={t("On-time verified")}
          value={percent(rate("on_time_verified"))}
          detail={t("Can arrive before the deadline")}
        />
        <Metric
          label={t("Protected reserve")}
          value={money(
            funds.data
              ?.filter((f) => f.restriction_type === "EMERGENCY")
              .reduce((a, f) => a + demoEur(f.amount, f.currency), 0) || 0,
          )}
          detail={t("Protected · demo EUR equivalent")}
        />
      </div>
      <div className="columns">
        <section className="panel wide">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">{t("UPCOMING")}</span>
              <h2>{t("Commitments that matter")}</h2>
            </div>
            <Link href="/commitments">
              {t("View all")}
              <ArrowRight size={14} />
            </Link>
          </div>
          {coverage.length ? (
            <CoverageTable coverage={coverage} />
          ) : (
            <Empty title={t("No plan generated yet")}>
              {obligations.data?.length
                ? t(
                    "Your commitments are ready. Generate an optimized plan to calculate coverage.",
                  )
                : t(
                    "Sign in as Demo administrator and use Reset Maya to load the complete dataset.",
                  )}
            </Empty>
          )}
        </section>
        <section className="panel">
          <span className="eyebrow">{t("YOUR FINANCIAL PICTURE")}</span>
          <h2>{t("Not all funds are equal.")}</h2>
          <div className="fund-summary">
            {["AVAILABLE", "PLANNED", "EXPECTED", "CONDITIONAL"].map(
              (status) => (
                <div key={status}>
                  <span>
                    <i className={`source-dot ${status}`} />
                    {label(status)}
                  </span>
                  <strong>
                    {funds.data
                      ?.filter(
                        (f) =>
                          f.availability_status === status &&
                          f.restriction_type !== "EMERGENCY",
                      )
                      .map((f) => money(f.amount, f.currency))
                      .join(" + ") || "—"}
                  </strong>
                </div>
              ),
            )}
          </div>
          <div className="safe-spend">
            <LockKeyhole size={17} />
            <div>
              <small>{t("Unallocated in this plan")}</small>
              <strong>
                {plan
                  ? Object.entries(plan.summary.safe_to_spend)
                      .map(([c, a]) => money(a, c))
                      .join(" + ") || money(0)
                  : t("Generate plan first")}
              </strong>
            </div>
          </div>
          <p className="caption">
            {t(
              "Protected allocations and emergency reserves are deducted. Uncertain income is excluded.",
            )}
          </p>
        </section>
      </div>
      <section className="panel intent-panel">
        <div>
          <span className="eyebrow">{t("UNDERSTAND THE INTENT")}</span>
          <h2>{t("What does your plan need to accomplish?")}</h2>
        </div>
        <div className="input-row">
          <input
            aria-label={t("Financial intent")}
            value={intentText}
            onChange={(e) => setIntent(e.target.value)}
          />
          <button
            className="button"
            disabled={busy}
            onClick={() =>
              run(async () => {
                if (intentText.length < 8 || intentText.length > 2000)
                  throw new Error(
                    "Please enter an intent between 8 and 2,000 characters.",
                  );
                const r = await api<{ steps: string[] }>("/intent", "POST", {
                  text: intentText,
                });
                setSteps(r.steps);
                return r;
              }, "Intent interpreted. No financial action was authorized.")
            }
          >
            {t("Understand intent")}
            <ArrowRight size={15} />
          </button>
        </div>
        {steps.length > 0 && (
          <div className="steps">
            {steps.map((s, i) => (
              <span key={s}>
                <b>{i + 1}</b>
                {t(s)}
              </span>
            ))}
          </div>
        )}
      </section>
      <div className="pillars">
        {[
          ["01", "Verify", "Facts with evidence"],
          ["02", "Orchestrate", "Funding matched to deadlines"],
          ["03", "Stress", "Test uncertainty"],
          ["04", "Repair", "Find the smallest feasible change"],
        ].map(([n, title, sub]) => (
          <Link
            href={
              n === "01"
                ? "/documents"
                : n === "02"
                  ? "/graph"
                  : n === "03"
                    ? "/scenarios"
                    : "/rescue"
            }
            key={n}
          >
            <span>{n}</span>
            <div>
              <strong>{t(title)}</strong>
              <small>{t(sub)}</small>
            </div>
            <ArrowRight size={17} />
          </Link>
        ))}
      </div>
    </>
  );
}
export function FundingPage({ actor, notify }: Props) {
  const { t, money, label, date } = useI18n();

  const data = useData<Funding[]>("funding", "/funding-sources");
  const { busy, run } = useTask(notify);
  const [form, setForm] = useState(false);
  const [currency, setCurrency] = useState("EUR");
  const { currencies } = useCurrencies();
  const amountStep =
    10 ** -(currencies.find((c) => c.code === currency)?.decimals ?? 2);
  const [error, setError] = useState("");
  return (
    <>
      <PageHeader
        eyebrow={t("CAPITAL, WITH CONTEXT")}
        title={t("Funding sources")}
        description={t(
          "Ownership, restrictions, availability, and evidence stay attached to every source.",
        )}
        action={
          <button className="button primary" onClick={() => setForm(!form)}>
            <Plus size={16} />
            {t("Add funding")}
          </button>
        }
      />
      {actor.role === "PARENT" && (
        <Notice>
          {t(
            "You can see only your own contribution and explicitly shared financial resources. These limits are enforced by the API.",
          )}
        </Notice>
      )}
      {form && (
        <form
          className="panel form-grid"
          onSubmit={async (e) => {
            e.preventDefault();
            setError("");
            const raw = Object.fromEntries(new FormData(e.currentTarget));
            try {
              const parsed = z
                .object({
                  label: z.string().min(2),
                  amount: z.coerce.number().min(0).max(1e9),
                  currency: z.string().regex(/^[A-Z]{3}$/),
                  available_from: z.iso.date(),
                  availability_status: z.enum([
                    "AVAILABLE",
                    "PLANNED",
                    "EXPECTED",
                    "CONDITIONAL",
                  ]),
                  source_type: z.enum([
                    "STUDENT_BALANCE",
                    "PARENT_SUPPORT",
                    "SCHOLARSHIP",
                    "OTHER",
                  ]),
                  confirmation_note: z.string().min(8),
                })
                .parse(raw);
              const result = await run(
                () => api("/funding-sources", "POST", parsed),
                "Funding added with explicit confirmation.",
              );
              if (result) setForm(false);
            } catch {
              setError(
                "Check the amount, date, and confirmation note (at least 8 characters).",
              );
            }
          }}
        >
          <label>
            {t("Source name")}
            <input
              name="label"
              required
              placeholder={t("Personal EUR savings")}
            />
          </label>
          <label>
            {t("Amount")}
            <input
              name="amount"
              type="number"
              min="0"
              max="1000000000"
              step={amountStep}
              required
            />
          </label>
          <label>
            {t("Currency")}
            <CurrencySelect value={currency} onChange={setCurrency} />
          </label>
          <label>
            {t("Available from")}
            <input name="available_from" type="date" required />
          </label>
          <label>
            {t("Type")}
            <select name="source_type">
              <option value="STUDENT_BALANCE">{t("STUDENT_BALANCE")}</option>
              <option value="PARENT_SUPPORT">{t("PARENT_SUPPORT")}</option>
              <option value="SCHOLARSHIP">{t("SCHOLARSHIP")}</option>
              <option value="OTHER">{t("OTHER")}</option>
            </select>
          </label>
          <label>
            {t("Availability")}
            <select name="availability_status">
              <option value="AVAILABLE">{t("AVAILABLE")}</option>
              <option value="PLANNED">{t("PLANNED")}</option>
              <option value="EXPECTED">{t("EXPECTED")}</option>
              <option value="CONDITIONAL">{t("CONDITIONAL")}</option>
            </select>
          </label>
          <label className="span-2">
            {t("Confirmation note")}
            <input
              name="confirmation_note"
              minLength={8}
              placeholder={t("How did you confirm these funds?")}
              required
            />
          </label>
          {error && (
            <p role="alert" className="error-text">
              {t(error)}
            </p>
          )}
          <button className="button primary" disabled={busy}>
            {t("Confirm funding")}
          </button>
        </form>
      )}
      {data.isPending ? (
        <Loading />
      ) : data.error ? (
        <Notice danger>{data.error.message}</Notice>
      ) : !data.data?.length ? (
        <Empty title={t("No funding sources")} />
      ) : (
        <div className="funding-grid">
          {data.data.map((f) => (
            <article className="panel funding-card" key={f.id}>
              <div className="card-top">
                <span className="fund-icon">
                  {f.restriction_type === "EMERGENCY" ? (
                    <LockKeyhole />
                  ) : (
                    <Globe2 />
                  )}
                </span>
                <Badge value={f.availability_status} />
              </div>
              <h2>{t(f.label)}</h2>
              <div className="amount">{money(f.amount, f.currency)}</div>
              <dl>
                <div>
                  <dt>{t("Owned by")}</dt>
                  <dd>
                    {f.owner_actor_id === "maya"
                      ? t("Maya")
                      : f.owner_actor_id === "father"
                        ? t("Father")
                        : f.owner_actor_id}
                  </dd>
                </div>
                <div>
                  <dt>{t("Available from")}</dt>
                  <dd>{date(f.available_from)}</dd>
                </div>
                <div>
                  <dt>{t("Restriction")}</dt>
                  <dd>{label(f.restriction_type)}</dd>
                </div>
                <div>
                  <dt>{t("Evidence")}</dt>
                  <dd>
                    <Badge value={f.verification_status} />
                  </dd>
                </div>
              </dl>
              {f.availability_status === "EXPECTED" && (
                <Notice>
                  {t("Forecast only. Excluded from verified coverage.")}
                </Notice>
              )}
              {f.restriction_type === "EMERGENCY" && (
                <Notice>{t("Protected from automatic allocation.")}</Notice>
              )}
            </article>
          ))}
        </div>
      )}
      <TransferRoutes />
    </>
  );
}
export function CommitmentsPage({ actor, notify }: Props) {
  const { t, money, label, date } = useI18n();

  const data = useData<Obligation[]>("obligations", "/obligations");
  const { busy, run } = useTask(notify);
  const [form, setForm] = useState(false);
  const [currency, setCurrency] = useState("EUR");
  const { currencies } = useCurrencies();
  const amountStep =
    10 ** -(currencies.find((c) => c.code === currency)?.decimals ?? 2);
  return (
    <>
      <PageHeader
        eyebrow={t("DEADLINES BEFORE BALANCES")}
        title={t("Financial commitments")}
        description={t(
          "Every obligation has an owner, a verified destination, and a deadline.",
        )}
        action={
          ["STUDENT", "ADMIN_DEMO"].includes(actor.role) && (
            <button className="button primary" onClick={() => setForm(!form)}>
              <Plus size={16} />
              {t("Add commitment")}
            </button>
          )
        }
      />
      {form && (
        <form
          className="panel form-grid"
          onSubmit={(e) => {
            e.preventDefault();
            const raw = Object.fromEntries(new FormData(e.currentTarget));
            run(async () => {
              const parsed = z
                .object({
                  label: z.string().min(2),
                  amount: z.coerce.number().positive(),
                  currency: z.string().regex(/^[A-Z]{3}$/),
                  due_date: z.iso.date(),
                  beneficiary: z.string().regex(/^[A-Z0-9_-]{3,80}$/),
                  confirmation_note: z.string().min(8),
                  type: z.string(),
                  priority: z.string(),
                })
                .parse(raw);
              await api("/obligations", "POST", parsed);
              setForm(false);
            }, "Commitment confirmed and financial state updated.");
          }}
        >
          <label>
            {t("Commitment name")}
            <input name="label" required />
          </label>
          <label>
            {t("Amount")}
            <input
              name="amount"
              type="number"
              min={amountStep}
              max="1000000000"
              step={amountStep}
              required
            />
          </label>
          <label>
            {t("Currency")}
            <CurrencySelect value={currency} onChange={setCurrency} />
          </label>
          <label>
            {t("Deadline")}
            <input name="due_date" type="date" required />
          </label>
          <label>
            {t("Type")}
            <select name="type">
              <option value="TUITION">{t("TUITION")}</option>
              <option value="RENT">{t("RENT")}</option>
              <option value="HOUSING_DEPOSIT">{t("HOUSING_DEPOSIT")}</option>
              <option value="INSURANCE">{t("INSURANCE")}</option>
              <option value="OTHER">{t("OTHER")}</option>
            </select>
          </label>
          <label>
            {t("Priority")}
            <select name="priority">
              <option value="CRITICAL">{t("CRITICAL")}</option>
              <option value="HIGH">{t("HIGH")}</option>
              <option value="NORMAL">{t("NORMAL")}</option>
              <option value="OPTIONAL">{t("OPTIONAL")}</option>
            </select>
          </label>
          <label>
            {t("Verified account identifier")}
            <input name="beneficiary" pattern="[A-Z0-9_-]{3,80}" required />
          </label>
          <label>
            {t("Explicit confirmation note")}
            <input name="confirmation_note" minLength={8} required />
          </label>
          <button className="button primary" disabled={busy}>
            {t("Confirm commitment")}
          </button>
        </form>
      )}
      {data.isPending ? (
        <Loading />
      ) : data.error ? (
        <Notice danger>{data.error.message}</Notice>
      ) : !data.data?.length ? (
        <Empty title={t("No commitments yet")} />
      ) : (
        <section className="panel">
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>{t("Commitment")}</th>
                  <th>{t("Amount")}</th>
                  <th>{t("Deadline")}</th>
                  <th>{t("Beneficiary")}</th>
                  <th>{t("Priority")}</th>
                  <th>{t("Evidence")}</th>
                </tr>
              </thead>
              <tbody>
                {data.data.map((o) => (
                  <tr key={o.id}>
                    <td>
                      <strong>{t(o.label)}</strong>
                      <small>
                        {label(o.type)} · {label(o.status)}
                      </small>
                      {o.installment_option && (
                        <span className="caption accent">
                          {t("Installment alternative available")}
                        </span>
                      )}
                    </td>
                    <td>{money(o.amount, o.currency)}</td>
                    <td>
                      <Clock3 size={13} className="inline-icon" />
                      {date(o.due_date)}
                    </td>
                    <td>
                      <code>{o.beneficiary}</code>
                      {o.security_hold ? (
                        <Badge value="BLOCKED" />
                      ) : (
                        <Check size={14} className="inline-icon accent" />
                      )}
                    </td>
                    <td>
                      <Badge value={o.priority} />
                    </td>
                    <td>
                      <Badge value={o.verification_status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </>
  );
}

"use client";
import Link from "next/link";
import { useI18n } from "@/lib/i18n/context";
import type { Impact, SafeBudget } from "@/lib/life";
import { Badge, Notice, CoverageTable } from "../ui";
export function BudgetCard({ budget }: { budget: SafeBudget }) {
  const { t, money, date } = useI18n();
  return (
    <section className="life-budget">
      <div className="life-section-head">
        <div>
          <span className="eyebrow">
            {t("YOUR VERIFIED SPENDING CAPACITY")}
          </span>
          <h2>{t("Safe to spend")}</h2>
        </div>
        <Badge value={budget.plan_state} />
      </div>
      <div className="life-budget-values">
        {(["today", "this_week", "this_month"] as const).map((key, i) => (
          <div key={key}>
            <small>{t(["Today", "This week", "This month"][i])}</small>
            <strong>{money(budget[key], budget.currency)}</strong>
            <small>{date(budget.dates[i])}</small>
          </div>
        ))}
      </div>
      <details>
        <summary>{t("How this is calculated")}</summary>
        <p>{t(budget.explanation)}</p>
        <div className="life-details">
          <span>
            {t("Verified liquid funds")} <b>{money(budget.liquid_eur)}</b>
          </span>
          <span>
            {t("Protected commitments")} <b>{money(budget.committed_eur)}</b>
          </span>
          <span>
            {t("Protected reserve")} <b>{money(budget.reserve_eur)}</b>
          </span>
          <span>
            {t("Verified shortfall")} <b>{money(budget.shortfall_eur)}</b>
          </span>
        </div>
        <small>
          {t("EUR figures are reference valuations at fixed demo rates.")}
        </small>
      </details>
      {budget.pending_events > 0 && (
        <Notice>
          {t(
            "Confirmed real events are reserved in this budget. Apply or dismiss them before preparing payments.",
          )}
        </Notice>
      )}
    </section>
  );
}
export function ImpactCard({
  impact,
  onAmount,
  onDate,
}: {
  impact: Impact;
  onAmount?: (amount: number) => void;
  onDate?: (date: string) => void;
}) {
  const { t, label, money, percent, date } = useI18n();
  const after = impact.after;
  return (
    <section className="life-impact" data-testid="life-impact">
      <div className="life-section-head">
        <h3>{t("Financial impact")}</h3>
        <Badge value="SHADOW_ONLY" />
      </div>
      {impact.missing.length > 0 && (
        <Notice>
          {t("Review required:")} {impact.missing.map(t).join(" · ")}
        </Notice>
      )}
      <div className="life-comparison">
        {[
          { key: "Before", b: impact.before },
          { key: "After", b: after },
        ].map(({ key, b }) => (
          <div key={key}>
            <span className="eyebrow">{t(key)}</span>
            {b ? (
              <>
                <Badge value={b.plan_state} />
                <strong>{money(b.today, b.currency)}</strong>
                <small>{t("Safe to spend today")}</small>
                <dl>
                  <dt>{t("On-time verified")}</dt>
                  <dd>{percent(b.verified_coverage)}</dd>
                  <dt>{t("Protected reserve")}</dt>
                  <dd>{money(b.reserve_eur)}</dd>
                  <dt>{t("Verified liquid funds")}</dt>
                  <dd>{money(b.liquid_eur)}</dd>
                </dl>
              </>
            ) : (
              <p>{t("Complete the missing details to compare.")}</p>
            )}
          </div>
        ))}
      </div>
      {impact.difference && (
        <p className="life-difference">
          {t("Liquidity change")}: <b>{money(impact.difference.liquid_eur)}</b>{" "}
          · {t("Reserve change")}: <b>{money(impact.difference.reserve_eur)}</b>
        </p>
      )}
      {!!impact.effects?.cash_gap_eur && (
        <Notice danger>
          {t("Selected funds cannot cover this expense.")}{" "}
          {money(impact.effects.cash_gap_eur)}
        </Notice>
      )}
      {impact.effects?.assumptions?.map((s) => (
        <p className="muted" key={s}>
          {t(s)}
        </p>
      ))}
      {(impact.affected?.length ?? 0) > 0 && (
        <>
          <h4>{t("Commitments affected")}</h4>
          <CoverageTable coverage={impact.affected!} />
        </>
      )}
      {after && impact.affected?.length === 0 && (
        <p className="muted">
          {t(
            "No recorded commitment loses verified coverage in this scenario.",
          )}
        </p>
      )}
      {impact.variants.length > 1 && (
        <div className="life-variants">
          {impact.variants.map((v) => (
            <div key={v.label}>
              <small>{label(v.label)}</small>
              <b>
                {v.amount_minor === null
                  ? t("Unknown amount")
                  : money(
                      v.amount_minor /
                        (new Intl.NumberFormat("en", {
                          style: "currency",
                          currency: impact.before.currency,
                        }).resolvedOptions().maximumFractionDigits === 0
                          ? 1
                          : 100),
                      impact.before.currency,
                    )}
              </b>
              <span>{date(v.event_date)}</span>
              <Badge value={v.after.plan_state} />
            </div>
          ))}
        </div>
      )}
      {impact.trip_total_eur !== undefined && (
        <p>
          {t("Travel envelope total")}: <b>{money(impact.trip_total_eur)}</b> ·{" "}
          {t("Maximum safe trip budget")}:{" "}
          <b>{money(impact.before.today, impact.before.currency)}</b>
        </p>
      )}
      {impact.goal && (
        <Notice>
          <b>{t("Soft savings goal")}</b>
          <p>
            {t("Monthly amount needed")}:{" "}
            {money(impact.goal.monthly_required, impact.before.currency)}
          </p>
          {t(
            "Critical commitments remain protected. This goal does not reserve or move money.",
          )}
        </Notice>
      )}
      {impact.options.length > 0 && (
        <>
          <h4>{t("Ways forward")}</h4>
          <div className="life-options">
            {impact.options.map((option, i) => (
              <div key={i}>
                <b>{label(option.type)}</b>
                {option.amount !== undefined && (
                  <span>{money(option.amount, option.currency)}</span>
                )}
                {option.date && <span>{date(option.date)}</span>}
                {option.conditional && (
                  <small>
                    {t(
                      "Wait for verified receipt before treating this money as spendable.",
                    )}
                  </small>
                )}
                {option.type === "LOWER_BUDGET" &&
                  (option.amount ?? 0) > 0 &&
                  onAmount && (
                    <button
                      type="button"
                      className="button small"
                      onClick={() => onAmount(option.amount ?? 0)}
                    >
                      {t("Try this amount")}
                    </button>
                  )}
                {option.type === "CHANGE_DATE" && onDate && option.date && (
                  <button
                    type="button"
                    className="button small"
                    onClick={() => onDate(option.date!)}
                  >
                    {t("Try this date")}
                  </button>
                )}
              </div>
            ))}
          </div>
        </>
      )}
      {impact.rescue && (
        <>
          <h4>{t("Minimum disruption alternatives")}</h4>
          <div className="life-options">
            {impact.rescue.candidates.slice(0, 3).map((c, i) => (
              <div key={i}>
                <b>{t(c.title)}</b>
                <Badge value={c.feasible ? "FEASIBLE" : "INFEASIBLE"} />
                <span>
                  {t("Direct cost")}: {money(c.direct_cost_eur)}
                </span>
                <span>
                  {t("Reserve effect")}: {money(c.reserve_impact_eur)}
                </span>
                <span>
                  {t("People involved")}: {c.people_involved}
                </span>
                <small>
                  {t("Scenario failure rate")}:{" "}
                  {percent(c.scenario_failure_rate)}
                </small>
                {c.assumptions.map((a) => (
                  <small key={a}>{t(a)}</small>
                ))}
              </div>
            ))}
          </div>
          <Link className="button" href="/rescue">
            {t("Open Rescue Center after applying the event")}
          </Link>
        </>
      )}
      {impact.runway && (
        <details>
          <summary>{t("Runway and next risk")}</summary>
          <p>
            {t("Recorded verified runway")}:{" "}
            {impact.runway.verified.bounded ? t("At least") : t("First gap in")}{" "}
            {impact.runway.verified.days} {t("days")}
          </p>
          {impact.runway.next_critical && (
            <p>
              {t(impact.runway.next_critical.label)} ·{" "}
              {date(impact.runway.next_critical.due_date)}
            </p>
          )}
          <small>{t(impact.runway.limitation)}</small>
        </details>
      )}
    </section>
  );
}

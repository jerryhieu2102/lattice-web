"use client";
import { useState } from "react";
import Link from "next/link";
import { Bell, Plus, Inbox, ArrowRight, ShieldAlert } from "lucide-react";
import { useData } from "@/lib/hooks";
import { useI18n } from "@/lib/i18n/context";
import { CurrencySelect, useCurrencies } from "@/lib/currencies";
import type { LifeInbox, Runway } from "@/lib/life";
import { Badge, Empty, Loading, Notice, PageHeader } from "../ui";
import { BudgetCard } from "./impact";
type Open = (target?: { id?: string; emergency?: boolean }) => void;
export function RunwayCard({ runway }: { runway: Runway }) {
  const { t, date, number } = useI18n();
  return (
    <section className="panel life-runway">
      <span className="eyebrow">{t("LOOKING AHEAD")}</span>
      <h2>{t("Financial runway")}</h2>
      <div className="life-budget-values">
        {[
          { name: "Verified funds", data: runway.verified },
          { name: "Including expected funds", data: runway.including_expected },
        ].map(({ name, data }) => (
          <div key={name}>
            <small>{t(name)}</small>
            <strong>
              {data.bounded ? "≥ " : ""}
              {number(data.days)} <small>{t("days")}</small>
            </strong>
            <small>
              {t(
                data.bounded
                  ? "Recorded commitments within the horizon"
                  : "Until the first recorded essential shortfall",
              )}
            </small>
          </div>
        ))}
      </div>
      <div className="life-next-risk">
        <small>{t("Next critical deadline")}</small>
        {runway.next_critical ? (
          <>
            <b>{t(runway.next_critical.label)}</b>
            <span>{date(runway.next_critical.due_date)}</span>
            <Badge
              value={
                runway.next_critical.on_time_verified >= 1 ? "SAFE" : "AT_RISK"
              }
            />
          </>
        ) : (
          <span>{t("No recorded critical deadline")}</span>
        )}
      </div>
      <p className="muted">{t(runway.limitation)}</p>
    </section>
  );
}
export function LifeSummary({ open }: { open: Open }) {
  const { t } = useI18n();
  const data = useData<LifeInbox>("life-inbox", "/life-inbox?currency=EUR");
  if (data.isPending) return <Loading />;
  if (data.error) return <Notice danger>{data.error.message}</Notice>;
  const active = data.data.events.filter(
    (e) => !["RESOLVED", "DISMISSED"].includes(e.status),
  );
  return (
    <section className="life-overview">
      <div className="life-section-head">
        <h2>{t("Life, included in the plan.")}</h2>
        <button className="button" onClick={() => open()}>
          <Plus size={16} />
          {t("Tell LATTICE")}
        </button>
      </div>
      <div className="life-dashboard">
        <BudgetCard budget={data.data.budget} />
        <RunwayCard runway={data.data.runway} />
      </div>
      <Link className="life-inbox-link" href="/life">
        <Inbox size={20} />
        <span>
          {t("Life Inbox")} · {active.length} {t("open events")}
        </span>
        <ArrowRight size={18} />
      </Link>
    </section>
  );
}
export function LifeNotifications() {
  const { t, label, date } = useI18n();
  const [open, setOpen] = useState(false);
  const data = useData<LifeInbox>("life-inbox", "/life-inbox?currency=EUR");
  return (
    <div className="life-notification-wrap">
      <button
        type="button"
        className="button small"
        aria-expanded={open}
        aria-label={t("Notifications")}
        onClick={() => setOpen(!open)}
      >
        <Bell size={16} />
        <span>{data.data?.notifications.length ?? 0}</span>
      </button>
      {open && (
        <section
          className="life-notifications"
          aria-label={t("Internal reminders")}
        >
          <h3>{t("Internal reminders")}</h3>
          {data.isPending ? (
            <Loading />
          ) : data.error ? (
            <Notice danger>{data.error.message}</Notice>
          ) : data.data.notifications.length ? (
            data.data.notifications.map((n) => (
              <Link key={n.id} href={n.href} onClick={() => setOpen(false)}>
                <small>{label(n.type)}</small>
                <b>{t(n.title)}</b>
                <span>{date(n.date)}</span>
              </Link>
            ))
          ) : (
            <p>{t("You have no reminders right now.")}</p>
          )}
          <small>
            {t(
              "Reminders use the demo planning clock. No external notifications are sent.",
            )}
          </small>
          <button className="button small" onClick={() => setOpen(false)}>
            {t("Close reminders")}
          </button>
        </section>
      )}
    </div>
  );
}
export function LifeInboxPage({ open }: { open: Open }) {
  const { t, label, money, date } = useI18n();
  const [filter, setFilter] = useState("OPEN"),
    [currency, setCurrency] = useState("EUR");
  const { currencies } = useCurrencies();
  const data = useData<LifeInbox>(
    "life-inbox",
    `/life-inbox?currency=${currency}`,
  );
  if (data.isPending) return <Loading />;
  if (data.error) return <Notice danger>{data.error.message}</Notice>;
  const events = data.data.events.filter((e) =>
    filter === "ALL"
      ? true
      : filter === "OPEN"
        ? !["DISMISSED", "RESOLVED"].includes(e.status)
        : e.status === filter,
  );
  return (
    <>
      <PageHeader
        eyebrow="REAL LIFE, VERIFIED DECISIONS"
        title="Your life, in the financial picture."
        description="Capture what happened, check an idea, or track money you are waiting for."
        action={
          <div className="life-action-row">
            <button
              className="button"
              onClick={() => open({ emergency: true })}
            >
              <ShieldAlert size={16} />
              {t("Something happened")}
            </button>
            <button className="button primary" onClick={() => open()}>
              <Plus size={16} />
              {t("Tell LATTICE")}
            </button>
          </div>
        }
      />
      <div className="life-section-head">
        <label>
          {t("Budget currency")}
          <CurrencySelect value={currency} onChange={setCurrency} />
        </label>
        <span className="muted">
          {t("All rates are deterministic demo quotes.")}
        </span>
      </div>
      <div className="life-dashboard">
        <BudgetCard budget={data.data.budget} />
        <RunwayCard runway={data.data.runway} />
      </div>
      <div className="life-section-head">
        <h2>{t("Life Inbox")}</h2>
        <label>
          <span className="sr-only">{t("Filter life events")}</span>
          <select
            aria-label={t("Filter life events")}
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          >
            {[
              "OPEN",
              "ALL",
              "REVIEW_REQUIRED",
              "SIMULATED",
              "CONFIRMED",
              "APPLIED",
              "RESOLVED",
              "DISMISSED",
            ].map((s) => (
              <option key={s} value={s}>
                {label(s)}
              </option>
            ))}
          </select>
        </label>
      </div>
      {events.length === 0 ? (
        <Empty title="No life events here yet">
          <span>
            {t(
              "A purchase idea, a delayed transfer, a refund: start with one sentence.",
            )}
          </span>
          <button className="button" onClick={() => open()}>
            {t("Capture an event")}
          </button>
        </Empty>
      ) : (
        <div className="life-event-list">
          {events.map((e) => {
            const p = e.proposal;
            const decimals =
              currencies.find((c) => c.code === p.currency)?.decimals ?? 2;
            return (
              <article className="panel life-event" key={e.id}>
                <div className="life-event-icon">
                  <Inbox size={20} />
                </div>
                <div className="life-event-body">
                  <div className="life-section-head">
                    <div>
                      <small>
                        {label(p.event_type)} · {label(p.mode)}
                      </small>
                      <h3>{t(e.title)}</h3>
                    </div>
                    <Badge value={e.status} />
                  </div>
                  <p className="life-raw">{e.raw_input}</p>
                  <div className="life-event-facts">
                    <strong>
                      {p.amount_minor !== null
                        ? money(
                            p.amount_minor / 10 ** decimals,
                            p.currency ?? "EUR",
                          )
                        : p.amount_min_minor !== null &&
                            p.amount_max_minor !== null
                          ? `${money(p.amount_min_minor / 10 ** decimals, p.currency ?? "EUR")} – ${money(p.amount_max_minor / 10 ** decimals, p.currency ?? "EUR")}`
                          : t("Unknown amount")}
                    </strong>
                    <span>
                      {e.metadata_json.received_date || p.event_date
                        ? date(e.metadata_json.received_date || p.event_date!)
                        : p.expected_date
                          ? date(p.expected_date)
                          : t("Date needs review")}
                    </span>
                    {p.counterparty && <span>{t(p.counterparty)}</span>}
                  </div>
                  {e.recurring_summary && (
                    <p>
                      {t("Monthly cost")}:{" "}
                      {money(
                        e.recurring_summary.monthly_cost,
                        e.recurring_summary.currency,
                      )}{" "}
                      · {t("Annualized cost")}:{" "}
                      {money(
                        e.recurring_summary.annual_cost,
                        e.recurring_summary.currency,
                      )}
                      {e.recurring_summary.next_renewal && (
                        <>
                          {" "}
                          · {t("Next renewal")}:{" "}
                          {date(e.recurring_summary.next_renewal)}
                        </>
                      )}
                    </p>
                  )}
                  {e.impact?.after && (
                    <small>
                      {t("Last simulated impact")}:{" "}
                      <Badge value={e.impact.after.plan_state} /> ·{" "}
                      {t("Safe to spend")}:{" "}
                      {money(e.impact.after.today, e.impact.after.currency)}
                    </small>
                  )}
                  {e.missing.length > 0 &&
                    !["APPLIED", "RESOLVED", "DISMISSED"].includes(
                      e.status,
                    ) && (
                      <small>
                        {t("Review required:")} {e.missing.map(t).join(" · ")}
                      </small>
                    )}
                  <div className="life-action-row">
                    <button
                      className="button small"
                      onClick={() => open({ id: e.id })}
                    >
                      {t(
                        e.status === "CONFIRMED"
                          ? "Review and apply"
                          : ["RESOLVED", "DISMISSED"].includes(e.status)
                            ? "View record"
                            : "Review event",
                      )}
                      <ArrowRight size={14} />
                    </button>
                    {p.mode === "HYPOTHETICAL" && (
                      <span className="muted">
                        {t("Idea only · balances unchanged")}
                      </span>
                    )}
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </>
  );
}

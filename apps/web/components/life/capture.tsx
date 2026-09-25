"use client";
import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { X, Sparkles, ShieldAlert } from "lucide-react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useData } from "@/lib/hooks";
import { useI18n, LanguageSelect } from "@/lib/i18n/context";
import {
  captureSchema,
  expectedTypes,
  type LifeEvent,
  type LifeProposal,
  type Impact,
} from "@/lib/life";
import type { Actor, Funding, Obligation, Notify } from "@/lib/types";
import { Badge, Loading, Notice } from "../ui";
import { LifeEditor, MoneyInput } from "./editor";
import { ImpactCard } from "./impact";
import { CurrencySelect, useCurrencies } from "@/lib/currencies";
type Target = { id?: string; emergency?: boolean };
export function LifeCapture({
  target,
  actor,
  onClose,
  notify,
}: {
  target: Target;
  actor: Actor;
  onClose: () => void;
  notify: Notify;
}) {
  const { t, locale, label, percent, date, money } = useI18n();
  const dialog = useRef<HTMLDialogElement>(null),
    form = useRef<HTMLFormElement>(null),
    input = useRef<HTMLTextAreaElement>(null);
  const queryClient = useQueryClient();
  const { currencies } = useCurrencies();
  const funds = useData<Funding[]>("funding", "/funding-sources");
  const obligations = useData<Obligation[]>("obligations", "/obligations");
  const health = useData<{ as_of: string }>("life-clock", "/health");
  const examples = useData<
    { key: string; en: string; vi: string; zh: string }[]
  >("life-examples", "/life-events/examples");
  const [raw, setRaw] = useState("");
  const [event, setEvent] = useState<LifeEvent | null>(null),
    [proposal, setProposal] = useState<LifeProposal | null>(null),
    [impact, setImpact] = useState<Impact | null>(null);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [note, setNote] = useState(""),
    [checked, setChecked] = useState(false);
  const [optional, setOptional] = useState<{
    amount_minor: number | null;
    currency: string;
    event_date: string;
  }>({ amount_minor: null, currency: "EUR", event_date: "" });
  const [receivedDate, setReceivedDate] = useState("");
  useEffect(() => {
    const node = dialog.current;
    node?.showModal();
    input.current?.focus();
    return () => node?.close();
  }, []);
  useEffect(() => {
    if (!target.id) return;
    let active = true;
    api<LifeEvent>(`/life-events/${target.id}`)
      .then((e) => {
        if (active) {
          setEvent(e);
          setProposal(e.proposal);
          setImpact(e.impact);
        }
      })
      .catch((e) => active && setError(e.message));
    return () => {
      active = false;
    };
  }, [target.id]);
  const sync = (e: LifeEvent) => {
    setEvent(e);
    setProposal(e.proposal);
    setImpact(e.impact);
    setChecked(false);
  };
  async function run<T>(work: () => Promise<T>): Promise<T | undefined> {
    setBusy(true);
    setError("");
    try {
      return await work();
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Unable to complete the request",
      );
    } finally {
      setBusy(false);
      await queryClient.invalidateQueries({
        predicate: (q) => q.queryKey[0] !== "me",
      });
    }
  }
  async function interpret() {
    if (!form.current?.reportValidity()) return;
    await run(async () => {
      const payload = captureSchema.parse({ raw_input: raw, locale });
      const e = await api<LifeEvent>("/life-events/interpret", "POST", {
        ...payload,
        ...(optional.amount_minor !== null
          ? { amount_minor: optional.amount_minor, currency: optional.currency }
          : {}),
        ...(optional.event_date ? { event_date: optional.event_date } : {}),
      });
      sync(e);
      if (!e.proposal.security_flags.length) {
        const result = await api<LifeEvent>(
          `/life-events/${e.id}/simulate`,
          "POST",
          { version: e.version, proposal: e.proposal },
        );
        sync(result);
      }
    });
  }
  async function simulate() {
    if (!event || !proposal || !form.current?.reportValidity()) return false;
    const result = await run(async () => {
      const e = await api<LifeEvent>(
        `/life-events/${event.id}/simulate`,
        "POST",
        { version: event.version, proposal },
      );
      sync(e);
      return e;
    });
    return !!result;
  }
  async function confirm() {
    if (!event || !proposal || !form.current?.reportValidity()) return;
    await run(async () =>
      sync(
        await api<LifeEvent>(`/life-events/${event.id}/confirm`, "POST", {
          version: event.version,
          proposal,
          confirmed: true,
          confirmation_note: note,
        }),
      ),
    );
  }
  async function apply() {
    if (!event) return;
    await run(async () => {
      const result = await api<{ event: LifeEvent }>(
        `/life-events/${event.id}/apply`,
        "POST",
        { version: event.version },
      );
      sync(result.event);
      notify("Life event applied to the sandbox ledger. Plan recalculated.");
    });
  }
  async function action(name: string, body: object = {}) {
    if (!event) return;
    await run(async () =>
      sync(
        await api<LifeEvent>(`/life-events/${event.id}/${name}`, "POST", {
          version: event.version,
          ...body,
        }),
      ),
    );
  }
  const frozen = event
    ? ["APPLIED", "RESOLVED", "DISMISSED"].includes(event.status)
    : false;
  const dirty =
    event && proposal
      ? JSON.stringify(event.proposal) !== JSON.stringify(proposal)
      : false;
  const readyReceipt =
    event &&
    proposal &&
    expectedTypes.includes(proposal.event_type) &&
    !["RESOLVED", "DISMISSED"].includes(event.status);
  const decimals =
    currencies.find((c) => c.code === proposal?.currency)?.decimals ?? 2;
  const update = (next: LifeProposal) => {
    setProposal(next);
    setChecked(false);
  };
  return (
    <dialog
      className="life-dialog"
      ref={dialog}
      onCancel={(e) => {
        e.preventDefault();
        if (!busy) onClose();
      }}
      aria-labelledby="capture-title"
    >
      <div className="life-modal-header">
        <div>
          <span className="eyebrow">{t("REAL LIFE, VERIFIED DECISIONS")}</span>
          <h2 id="capture-title">
            {t(target.emergency ? "Something happened" : "Tell LATTICE")}
          </h2>
        </div>
        <button
          type="button"
          className="icon-button"
          aria-label={t("Close capture")}
          disabled={busy}
          onClick={onClose}
        >
          <X size={20} />
        </button>
      </div>
      <div className="life-modal-toolbar">
        <LanguageSelect />
        <span className="sandbox">{t("SANDBOX")}</span>
        <small>
          {t("Planning clock:")}{" "}
          {health.data ? date(health.data.as_of) : t("Loading…")}
        </small>
      </div>
      <form
        ref={form}
        onSubmit={(e) => {
          e.preventDefault();
          if (!event) void interpret();
          else void simulate();
        }}
      >
        <fieldset disabled={busy}>
          {!event && !target.id && (
            <>
              <label className="life-prompt">
                {t("What’s happening?")}
                <textarea
                  ref={input}
                  name="raw_input"
                  value={raw}
                  minLength={3}
                  maxLength={4000}
                  required
                  rows={3}
                  placeholder={t(
                    "A purchase idea, a bill, money arriving late…",
                  )}
                  onChange={(e) => setRaw(e.target.value)}
                />
              </label>
              {target.emergency && (
                <div className="life-chips">
                  {[
                    "Medical expense",
                    "Family emergency",
                    "Lost card",
                    "Unexpected bill",
                    "Housing emergency",
                    "Transfer failed",
                    "Scam / suspicious transaction",
                    "Device needed for study",
                    "Other emergency",
                  ].map((s) => (
                    <button
                      type="button"
                      key={s}
                      onClick={() => {
                        setRaw(t(s));
                        input.current?.focus();
                      }}
                    >
                      {t(s)}
                    </button>
                  ))}
                </div>
              )}
              <div className="life-chips">
                {examples.data?.map((e) => (
                  <button
                    type="button"
                    key={e.key}
                    onClick={() => {
                      setRaw(e[locale]);
                      input.current?.focus();
                    }}
                  >
                    {label(e.key)}
                  </button>
                ))}
              </div>
              <details>
                <summary>{t("Add an amount or date (optional)")}</summary>
                <div className="life-fields">
                  <label>
                    {t("Amount")}
                    <MoneyInput
                      name="capture_amount"
                      value={optional.amount_minor}
                      currency={optional.currency}
                      onChange={(amount_minor) =>
                        setOptional({ ...optional, amount_minor })
                      }
                    />
                  </label>
                  <label>
                    {t("Currency")}
                    <CurrencySelect
                      value={optional.currency}
                      onChange={(currency) =>
                        setOptional({
                          ...optional,
                          currency,
                          amount_minor: null,
                        })
                      }
                    />
                  </label>
                  <label>
                    {t("Event date")}
                    <input
                      type="date"
                      value={optional.event_date}
                      onChange={(e) =>
                        setOptional({ ...optional, event_date: e.target.value })
                      }
                    />
                  </label>
                </div>
              </details>
              <button type="submit" className="button primary life-submit">
                <Sparkles size={16} />
                {t(busy ? "Analyzing…" : "Understand and check impact")}
              </button>
              <p className="muted">
                {t(
                  "Your sentence creates a proposal. Balances change only after explicit review and confirmation.",
                )}
              </p>
            </>
          )}
          {!event && target.id && !error && <Loading />}
          {event && proposal && (
            <>
              <div className="life-section-head">
                <Badge value={event.status} />
                <small>
                  {t("Interpretation confidence")}:{" "}
                  {percent(proposal.confidence)}
                </small>
              </div>
              <blockquote className="life-raw">{event.raw_input}</blockquote>
              {proposal.security_flags.length > 0 ||
              proposal.event_type === "SECURITY_INCIDENT" ? (
                <Notice danger>
                  <ShieldAlert size={20} />
                  <strong>{t("Security review required")}</strong>
                  <p>
                    {t(
                      "This text cannot authorize a payment or change a verified beneficiary.",
                    )}
                  </p>
                  {proposal.security_flags.map((f) => (
                    <Badge key={f} value={f} />
                  ))}
                  <p>
                    <Link href="/documents" onClick={onClose}>
                      {t("Review evidence in Documents")}
                    </Link>
                  </p>
                </Notice>
              ) : (
                <>
                  {!frozen && !proposal.question ? (
                    <LifeEditor
                      p={proposal}
                      setP={update}
                      funds={funds.data ?? []}
                      obligations={obligations.data ?? []}
                      studentId={
                        actor.role === "ADMIN_DEMO" ? "maya" : actor.id
                      }
                    />
                  ) : (
                    <div className="life-record-details">
                      <strong>{label(proposal.event_type)}</strong>
                      <span>
                        {proposal.amount_minor === null
                          ? t("Unknown amount")
                          : money(
                              proposal.amount_minor / 10 ** decimals,
                              proposal.currency ?? "EUR",
                            )}
                      </span>
                      <span>
                        {event.metadata_json.received_date ||
                        proposal.event_date
                          ? date(
                              event.metadata_json.received_date ||
                                proposal.event_date!,
                            )
                          : t("Unknown date")}
                      </span>
                    </div>
                  )}
                  {dirty && (
                    <Notice>
                      {t(
                        "Details changed. Simulate again to update the comparison.",
                      )}
                    </Notice>
                  )}
                  {impact && !dirty && (
                    <ImpactCard
                      impact={impact}
                      onAmount={
                        !frozen
                          ? (n) =>
                              update({
                                ...proposal,
                                amount_minor: Math.round(n * 10 ** decimals),
                                amount_min_minor: null,
                                amount_max_minor: null,
                              })
                          : undefined
                      }
                      onDate={
                        !frozen
                          ? (d) => update({ ...proposal, event_date: d })
                          : undefined
                      }
                    />
                  )}
                  {!frozen && (
                    <div className="life-action-row">
                      <button type="submit" className="button primary">
                        {t("Simulate impact")}
                      </button>
                      {proposal.mode === "HYPOTHETICAL" && (
                        <button
                          type="button"
                          className="button"
                          onClick={async () => {
                            if (await simulate()) onClose();
                          }}
                        >
                          {t("Keep as idea")}
                        </button>
                      )}
                      {proposal.event_type === "PURCHASE_INTENT" && (
                        <button
                          type="button"
                          className="button"
                          onClick={() =>
                            update({
                              ...proposal,
                              event_type: "EXPENSE_OCCURRED",
                              mode: "ACTUAL",
                              event_date: null,
                              funding_source_id: null,
                            })
                          }
                        >
                          {t("I bought it")}
                        </button>
                      )}
                    </div>
                  )}
                  {proposal.mode !== "HYPOTHETICAL" &&
                    !frozen &&
                    event.status !== "CONFIRMED" && (
                      <div className="life-confirmation">
                        <h4>{t("Confirm the real-world details")}</h4>
                        <label>
                          {t("Confirmation note")}
                          <textarea
                            value={note}
                            minLength={8}
                            maxLength={1000}
                            rows={2}
                            onChange={(e) => setNote(e.target.value)}
                            placeholder={t("How did you verify this event?")}
                          />
                        </label>
                        <label className="life-check">
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={(e) => setChecked(e.target.checked)}
                          />
                          {t(
                            "I checked the amount, currency, date and selected source. This is my explicit confirmation.",
                          )}
                        </label>
                        <button
                          type="button"
                          className="button"
                          disabled={!checked || note.trim().length < 8}
                          onClick={confirm}
                        >
                          {t("Confirm details")}
                        </button>
                      </div>
                    )}
                  {event.status === "CONFIRMED" &&
                    proposal.mode !== "HYPOTHETICAL" && (
                      <Notice>
                        <p>
                          {t(
                            "Confirmation reserves this event in the budget. Apply records it once in the sandbox ledger.",
                          )}
                        </p>
                        <button
                          type="button"
                          className="button primary"
                          disabled={!!dirty}
                          onClick={apply}
                        >
                          {t("Apply to sandbox ledger")}
                        </button>
                        <button
                          type="button"
                          className="button"
                          onClick={simulate}
                        >
                          {t("Reopen review")}
                        </button>
                      </Notice>
                    )}
                  {readyReceipt && (
                    <details>
                      <summary>{t("Mark received")}</summary>
                      <p>
                        {t(
                          "Only confirm after the money has arrived in your own account. This is user confirmation, not bank verification.",
                        )}
                      </p>
                      <label>
                        {t("Receipt date")}
                        <input
                          name="received_date"
                          type="date"
                          value={receivedDate}
                          max={health.data?.as_of}
                          onChange={(e) => setReceivedDate(e.target.value)}
                        />
                      </label>
                      <label>
                        {t("Receipt evidence or confirmation note")}
                        <textarea
                          value={note}
                          minLength={8}
                          maxLength={1000}
                          onChange={(e) => setNote(e.target.value)}
                        />
                      </label>
                      <label className="life-check">
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={(e) => setChecked(e.target.checked)}
                        />
                        {t("I checked that the money arrived.")}
                      </label>
                      <button
                        type="button"
                        className="button"
                        disabled={
                          !checked ||
                          note.trim().length < 8 ||
                          !receivedDate ||
                          !!dirty
                        }
                        onClick={() =>
                          action("received", {
                            confirmed: true,
                            received_date: receivedDate,
                            confirmation_note: note,
                          })
                        }
                      >
                        {t("Confirm receipt")}
                      </button>
                      <button
                        type="button"
                        className="button"
                        onClick={onClose}
                      >
                        {t("Still waiting")}
                      </button>
                    </details>
                  )}
                  {event.status === "APPLIED" && proposal.recurrence_rule && (
                    <details open>
                      <summary>{t("Recurring expense controls")}</summary>
                      {event.recurring_summary && (
                        <p>
                          {t("Monthly cost")}:{" "}
                          {money(
                            event.recurring_summary.monthly_cost,
                            event.recurring_summary.currency,
                          )}{" "}
                          · {t("Annualized cost")}:{" "}
                          {money(
                            event.recurring_summary.annual_cost,
                            event.recurring_summary.currency,
                          )}
                        </p>
                      )}
                      <div className="life-action-row">
                        <button
                          type="button"
                          className="button"
                          onClick={() => action("reminder")}
                        >
                          {t(
                            event.metadata_json.reminder_muted
                              ? "Restore reminder"
                              : "Cancel reminder",
                          )}
                        </button>
                        <button
                          type="button"
                          className="button"
                          onClick={() =>
                            run(async () =>
                              setImpact(
                                await api<Impact>(
                                  `/life-events/${event.id}/pause-scenario`,
                                  "POST",
                                  { version: event.version },
                                ),
                              ),
                            )
                          }
                        >
                          {t("Pause scenario")}
                        </button>
                      </div>
                      <Notice>
                        {t(
                          "These controls do not cancel an external subscription.",
                        )}
                      </Notice>
                      <label>
                        {t("New recurring amount")}
                        <MoneyInput
                          name="new_recurring_amount"
                          value={proposal.amount_minor}
                          currency={proposal.currency ?? "EUR"}
                          onChange={(n) =>
                            update({ ...proposal, amount_minor: n })
                          }
                        />
                      </label>
                      <label>
                        {t("Confirmation note")}
                        <textarea
                          value={note}
                          minLength={8}
                          maxLength={1000}
                          onChange={(e) => setNote(e.target.value)}
                        />
                      </label>
                      <label className="life-check">
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={(e) => setChecked(e.target.checked)}
                        />
                        {t("I confirmed this change with the provider.")}
                      </label>
                      <button
                        type="button"
                        className="button"
                        disabled={
                          !checked ||
                          note.trim().length < 8 ||
                          !proposal.amount_minor
                        }
                        onClick={() =>
                          action("recurrence", {
                            proposal,
                            confirmed: true,
                            confirmation_note: note,
                          })
                        }
                      >
                        {t("Update future budget commitments")}
                      </button>
                    </details>
                  )}
                  {event.status === "APPLIED" &&
                    !proposal.recurrence_rule &&
                    !expectedTypes.includes(proposal.event_type) && (
                      <details>
                        <summary>{t("Resolve")}</summary>
                        <p>
                          {t(
                            "Resolution closes this report. Recorded expenses remain in the ledger. Availability reports stop affecting the plan.",
                          )}
                        </p>
                        <label>
                          {t("Confirmation note")}
                          <textarea
                            value={note}
                            minLength={8}
                            maxLength={1000}
                            onChange={(e) => setNote(e.target.value)}
                          />
                        </label>
                        <label className="life-check">
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={(e) => setChecked(e.target.checked)}
                          />
                          {t("I checked that this issue is resolved.")}
                        </label>
                        <button
                          type="button"
                          className="button"
                          disabled={!checked || note.trim().length < 8}
                          onClick={() =>
                            action("resolve", {
                              confirmed: true,
                              confirmation_note: note,
                            })
                          }
                        >
                          {t("Confirm resolution")}
                        </button>
                      </details>
                    )}
                </>
              )}
              {(!frozen || readyReceipt) && (
                <button
                  type="button"
                  className="button life-dismiss"
                  onClick={() => action("dismiss")}
                >
                  {t(readyReceipt ? "Cancel expectation" : "Dismiss event")}
                </button>
              )}
              {event.status === "APPLIED" && (
                <Notice>
                  {t("Recorded in SANDBOX. No real payment was executed.")}
                </Notice>
              )}
              {event.metadata_json.receivable_event_id && (
                <p>
                  <Link href="/life" onClick={onClose}>
                    {t("View the linked reimbursement in Life Inbox")}
                  </Link>
                </p>
              )}
            </>
          )}
        </fieldset>
      </form>
      {busy && (
        <p className="life-busy" aria-live="polite">
          {t("Computing from your recorded financial state…")}
        </p>
      )}
      {error && (
        <div role="alert">
          <Notice danger>
            {t(
              error.startsWith("[")
                ? "Invalid input. Check all required fields, amounts, dates, and currency precision."
                : error,
            )}
          </Notice>
        </div>
      )}
    </dialog>
  );
}

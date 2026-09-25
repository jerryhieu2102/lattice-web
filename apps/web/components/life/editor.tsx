"use client";
import { useI18n } from "@/lib/i18n/context";
import { CurrencySelect, useCurrencies } from "@/lib/currencies";
import {
  eventTypes,
  envelopeCategories,
  expectedTypes,
  overlayTypes,
  toMinor,
  type LifeProposal,
} from "@/lib/life";
import type { Funding, Obligation } from "@/lib/types";
export function MoneyInput({
  name,
  value,
  currency,
  onChange,
  required = false,
}: {
  name: string;
  value: number | null;
  currency: string;
  onChange: (n: number | null) => void;
  required?: boolean;
}) {
  const { t } = useI18n();
  const { currencies } = useCurrencies();
  const decimals = currencies.find((c) => c.code === currency)?.decimals ?? 2;
  return (
    <input
      name={name}
      type="number"
      min="0"
      max={Math.min(100_000_000_000 / 10 ** decimals, 1_000_000_000)}
      step={10 ** -decimals}
      value={value === null ? "" : value / 10 ** decimals}
      required={required}
      placeholder={t("Unknown")}
      onChange={(e) => {
        try {
          const next = toMinor(e.target.value, decimals);
          e.target.setCustomValidity("");
          onChange(next);
        } catch {
          e.target.setCustomValidity(
            t("Check the amount and currency precision."),
          );
          e.target.reportValidity();
        }
      }}
    />
  );
}
export function LifeEditor({
  p,
  setP,
  funds,
  obligations,
  studentId,
}: {
  p: LifeProposal;
  setP: (p: LifeProposal) => void;
  funds: Funding[];
  obligations: Obligation[];
  studentId: string;
}) {
  const { t, label } = useI18n();
  const update = (patch: Partial<LifeProposal>) => setP({ ...p, ...patch });
  const money = (
    key:
      | "amount_minor"
      | "amount_min_minor"
      | "amount_max_minor"
      | "receivable_minor"
      | "repayment_minor",
    title: string,
  ) => (
    <label>
      {t(title)}
      <MoneyInput
        name={key}
        value={p[key]}
        currency={p.currency ?? "EUR"}
        onChange={(v) =>
          update(
            key === "amount_minor"
              ? {
                  amount_minor: v,
                  amount_min_minor: null,
                  amount_max_minor: null,
                }
              : key === "amount_min_minor" || key === "amount_max_minor"
                ? { [key]: v, amount_minor: null }
                : { [key]: v },
          )
        }
      />
    </label>
  );
  const dateField = (
    key:
      | "event_date"
      | "expected_date"
      | "date_window_start"
      | "date_window_end"
      | "repayment_date",
    title: string,
  ) => (
    <label>
      {t(title)}
      <input
        type="date"
        name={key}
        value={p[key] ?? ""}
        onChange={(e) => update({ [key]: e.target.value || null })}
      />
    </label>
  );
  const sourceRequired =
    overlayTypes.includes(p.event_type) ||
    ["PURCHASE_INTENT", "EXPENSE_OCCURRED", "LENDING", "TRAVEL_PLAN"].includes(
      p.event_type,
    );
  return (
    <div className="life-editor">
      <div className="life-fields">
        <label>
          {t("Event type")}
          <select
            name="event_type"
            value={p.event_type}
            onChange={(e) => {
              const type = e.target.value as LifeProposal["event_type"];
              update({
                event_type: type,
                mode: [
                  "PURCHASE_INTENT",
                  "TRAVEL_PLAN",
                  "SAVINGS_GOAL",
                ].includes(type)
                  ? "HYPOTHETICAL"
                  : expectedTypes.includes(type)
                    ? "EXPECTED"
                    : "ACTUAL",
                question: false,
              });
            }}
          >
            {eventTypes.map((v) => (
              <option key={v} value={v}>
                {label(v)}
              </option>
            ))}
          </select>
        </label>
        <label>
          {t("Record or scenario")}
          <select
            name="mode"
            value={p.mode}
            onChange={(e) =>
              update({ mode: e.target.value as LifeProposal["mode"] })
            }
          >
            <option value="HYPOTHETICAL">
              {t("What if · no ledger change")}
            </option>
            <option value="ACTUAL">
              {t("Real event · confirmation required")}
            </option>
            <option value="EXPECTED">{t("Expected · not received")}</option>
          </select>
        </label>
        <label>
          {t("Event title")}
          <input
            maxLength={240}
            value={t(p.title)}
            onChange={(e) => update({ title: e.target.value })}
          />
        </label>
        <label>
          {t("Currency")}
          <CurrencySelect
            value={p.currency ?? ""}
            onChange={(v) =>
              update({
                currency: v,
                amount_minor: null,
                amount_min_minor: null,
                amount_max_minor: null,
                receivable_minor: null,
                repayment_minor: null,
              })
            }
          />
        </label>
        {money("amount_minor", "Amount")}
        {dateField(
          "event_date",
          p.event_type === "RECURRING_EXPENSE"
            ? "First renewal date"
            : "Event date",
        )}
        {sourceRequired && (
          <label>
            {t("Funding source")}
            <select
              name="funding_source_id"
              aria-label={t("Funding source")}
              value={p.funding_source_id ?? ""}
              onChange={(e) =>
                update({ funding_source_id: e.target.value || null })
              }
            >
              <option value="">{t("Choose a source to review")}</option>
              {funds
                .filter(
                  (f) =>
                    overlayTypes.includes(p.event_type) ||
                    f.owner_actor_id === studentId,
                )
                .map((f) => (
                  <option value={f.id} key={f.id}>
                    {t(f.label)} · {f.currency} · {label(f.availability_status)}
                  </option>
                ))}
            </select>
          </label>
        )}
        {["OBLIGATION_CHANGED", "EXPENSE_OCCURRED"].includes(p.event_type) && (
          <>
            <label>
              {t("Linked commitment")}
              <select
                name="obligation_id"
                value={p.obligation_id ?? ""}
                onChange={(e) =>
                  update({ obligation_id: e.target.value || null })
                }
              >
                <option value="">
                  {t(
                    p.event_type === "EXPENSE_OCCURRED"
                      ? "Standalone expense"
                      : "Select commitment",
                  )}
                </option>
                {obligations
                  .filter(
                    (o) =>
                      o.status === "OPEN" &&
                      (p.event_type !== "EXPENSE_OCCURRED" || o.budget_only),
                  )
                  .map((o) => (
                    <option key={o.id} value={o.id}>
                      {t(o.label)} · {o.currency}
                    </option>
                  ))}
              </select>
            </label>
            {p.event_type === "OBLIGATION_CHANGED" && (
              <label className="life-check">
                <input
                  type="checkbox"
                  checked={p.amount_is_delta}
                  onChange={(e) =>
                    update({ amount_is_delta: e.target.checked })
                  }
                />
                {t("Amount is an increase, not a replacement")}
              </label>
            )}
          </>
        )}
        {p.event_type === "FUNDING_REDUCED" && (
          <label className="life-check">
            <input
              type="checkbox"
              checked={p.amount_is_delta}
              onChange={(e) => update({ amount_is_delta: e.target.checked })}
            />
            {t("Amount is the reduction")}
          </label>
        )}
        {p.event_type === "FUNDING_DELAYED" && (
          <label>
            {t("Delay days")}
            <input
              type="number"
              min={1}
              max={365}
              name="delay_days"
              value={p.delay_days ?? ""}
              onChange={(e) =>
                update({
                  delay_days: e.target.value ? Number(e.target.value) : null,
                })
              }
            />
          </label>
        )}
        {expectedTypes.includes(p.event_type) &&
          dateField("expected_date", "Expected receipt date")}
        {p.event_type === "RECURRING_EXPENSE" && (
          <label>
            {t("Recurrence")}
            <select
              name="recurrence_rule"
              value={p.recurrence_rule ?? ""}
              onChange={(e) =>
                update({ recurrence_rule: e.target.value || null })
              }
            >
              <option value="">{t("Select recurrence")}</option>
              {["WEEKLY", "MONTHLY", "YEARLY"].map((c) => (
                <option key={c} value={c}>
                  {label(c)}
                </option>
              ))}
            </select>
          </label>
        )}
        {[
          "BORROWING",
          "LENDING",
          "EXPENSE_OCCURRED",
          "REIMBURSEMENT_EXPECTED",
        ].includes(p.event_type) && (
          <label>
            {t("Counterparty")}
            <input
              value={p.counterparty ?? ""}
              maxLength={120}
              onChange={(e) => update({ counterparty: e.target.value || null })}
            />
          </label>
        )}
        {p.event_type === "EXPENSE_OCCURRED" &&
          money("receivable_minor", "Amount someone owes you")}
        {["BORROWING", "LENDING"].includes(p.event_type) &&
          dateField("repayment_date", "Repayment date")}
        {p.event_type === "BORROWING" &&
          money("repayment_minor", "Repayment amount including interest")}
      </div>
      <details
        open={p.amount_min_minor !== null || p.date_window_start !== null}
      >
        <summary>{t("Amount range, date window and priority")}</summary>
        <div className="life-fields">
          {money("amount_min_minor", "Minimum estimate")}
          {money("amount_max_minor", "Maximum estimate")}
          {dateField("date_window_start", "Earliest date")}
          {dateField("date_window_end", "Latest date")}
          <label>
            {t("Essentiality")}
            <select
              value={p.essentiality}
              onChange={(e) =>
                update({
                  essentiality: e.target.value as LifeProposal["essentiality"],
                })
              }
            >
              {["ESSENTIAL", "DISCRETIONARY", "UNKNOWN"].map((x) => (
                <option key={x} value={x}>
                  {label(x)}
                </option>
              ))}
            </select>
          </label>
          <label>
            {t("Priority")}
            <select
              value={p.priority}
              onChange={(e) => update({ priority: e.target.value })}
            >
              {["CRITICAL", "HIGH", "NORMAL", "OPTIONAL"].map((x) => (
                <option key={x} value={x}>
                  {label(x)}
                </option>
              ))}
            </select>
          </label>
        </div>
      </details>
      {p.event_type === "TRAVEL_PLAN" && (
        <details className="life-envelope" open>
          <summary>{t("Edit travel envelope")}</summary>
          <p>
            {t(
              "Enter your own estimates. Empty categories have no estimate; no travel prices are invented.",
            )}
          </p>
          <div className="life-fields">
            {envelopeCategories.map((category) => {
              const item = p.envelope.find((x) => x.category === category);
              return (
                <div key={category}>
                  <label>
                    {label(category)}
                    <MoneyInput
                      name={category}
                      value={item?.amount_minor ?? null}
                      currency={item?.currency ?? p.currency ?? "EUR"}
                      onChange={(value) =>
                        update({
                          envelope: [
                            ...p.envelope.filter(
                              (x) => x.category !== category,
                            ),
                            ...(value === null
                              ? []
                              : [
                                  {
                                    category,
                                    amount_minor: value,
                                    currency:
                                      item?.currency ?? p.currency ?? "EUR",
                                  },
                                ]),
                          ],
                        })
                      }
                    />
                  </label>
                  <label>
                    <span className="sr-only">
                      {label(category)} {t("Currency")}
                    </span>
                    <CurrencySelect
                      name={category + "_currency"}
                      value={item?.currency ?? p.currency ?? "EUR"}
                      onChange={(currency) =>
                        update({
                          envelope: [
                            ...p.envelope.filter(
                              (x) => x.category !== category,
                            ),
                            { category, amount_minor: 0, currency },
                          ],
                        })
                      }
                    />
                  </label>
                </div>
              );
            })}
          </div>
        </details>
      )}
    </div>
  );
}

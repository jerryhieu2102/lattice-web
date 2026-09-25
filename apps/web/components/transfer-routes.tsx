"use client";
import { useState } from "react";
import { useData } from "@/lib/hooks";
import { CurrencySelect } from "@/lib/currencies";
import type { Route } from "@/lib/types";
import { useI18n } from "@/lib/i18n/context";
import { Empty, Loading, Notice } from "./ui";
export function TransferRoutes() {
  const [from, setFrom] = useState("USD");
  const [to, setTo] = useState("VND");
  const query = useData<Route[]>("routes", "/transfer-routes");
  const { t, money, number, exchangeRate } = useI18n();
  const routes =
    query.data?.filter(
      (r) => r.from_currency === from && r.to_currency === to,
    ) || [];
  return (
    <section className="panel transfer-routes">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">{t("CROSS-BORDER ROUTES")}</span>
          <h2>{t("Choose a currency pair")}</h2>
        </div>
      </div>
      <p className="caption">
        {t(
          "13 currencies, both directions. Fixed demo quotes; not live market rates.",
        )}
      </p>
      <div className="route-selectors">
        <label>
          {t("From currency")}
          <CurrencySelect
            name="from_currency"
            value={from}
            onChange={setFrom}
          />
        </label>
        <span aria-hidden>→</span>
        <label>
          {t("To currency")}
          <CurrencySelect name="to_currency" value={to} onChange={setTo} />
        </label>
      </div>
      {query.isPending ? (
        <Loading />
      ) : query.error ? (
        <Notice danger>{query.error.message}</Notice>
      ) : !routes.length ? (
        <Empty title="No available route">
          {t(
            "This currency pair has no configured route. The optimizer will not invent one.",
          )}
        </Empty>
      ) : (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>{t("Route")}</th>
                <th>{t("Demo exchange rate")}</th>
                <th>{t("Fixed fee")}</th>
                <th>{t("Percentage fee")}</th>
                <th>{t("Settlement (p95)")}</th>
              </tr>
            </thead>
            <tbody>
              {routes.map((r) => (
                <tr key={r.id}>
                  <td>{t(r.provider_name)}</td>
                  <td>
                    1 {from} = {exchangeRate(r.fx_rate)} {to}
                  </td>
                  <td>{money(r.fixed_fee, from)}</td>
                  <td>{number(r.percentage_fee * 100)}%</td>
                  <td>
                    {r.settlement_p95_days} {t("days")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

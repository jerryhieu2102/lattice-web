"use client";
import { useQuery } from "@tanstack/react-query";
import { api } from "./api";
import { useI18n } from "./i18n/context";
import { locales } from "./i18n/core";
export interface Currency {
  code: string;
  decimals: number;
  eur_value: number;
}
export function useCurrencies() {
  const query = useQuery({
    queryKey: ["currencies"],
    queryFn: () =>
      api<{ currencies: Currency[]; rate_source: string }>("/currencies"),
    staleTime: Infinity,
  });
  return {
    ...query,
    currencies: query.data?.currencies || [],
    demoEur: (value: number, currency: string) =>
      value *
      (query.data?.currencies.find((c) => c.code === currency)?.eur_value ??
        NaN),
  };
}
export function CurrencySelect({
  name = "currency",
  value,
  onChange,
}: {
  name?: string;
  value?: string;
  onChange?: (value: string) => void;
}) {
  const { currencies, isPending, error } = useCurrencies();
  const { locale, t } = useI18n();
  const names = new Intl.DisplayNames([locales[locale]], { type: "currency" });
  return (
    <select
      name={name}
      value={value}
      onChange={onChange ? (e) => onChange(e.target.value) : undefined}
      required
      disabled={isPending || !!error}
    >
      {value === "" && <option value="">{t("Select currency")}</option>}
      {isPending ? (
        <option value="">{t("Loading currencies…")}</option>
      ) : error ? (
        <option value="">{t("Unable to load currencies")}</option>
      ) : (
        currencies.map((c) => (
          <option key={c.code} value={c.code}>
            {c.code} · {names.of(c.code)}
          </option>
        ))
      )}
    </select>
  );
}

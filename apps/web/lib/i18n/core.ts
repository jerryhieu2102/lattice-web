import vi from "./vi.json";
import zh from "./zh.json";
export type Locale = "en" | "vi" | "zh";
export const locales = { en: "en-GB", vi: "vi-VN", zh: "zh-CN" } as const;
const dictionaries: Record<Locale, Record<string, string>> = { en: {}, vi, zh };
export const normalize = (text: string) => text.replace(/\s+/g, " ").trim();
const escape = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
const patterns = Object.keys(vi)
  .filter((key) => /\{\d+\}/.test(key))
  .map((key) => ({
    key,
    regex: new RegExp(
      "^" +
        key
          .split(/\{\d+\}/)
          .map(escape)
          .join("([\\s\\S]*?)") +
        "$",
    ),
  }));
export function translate(locale: Locale, text: string): string {
  if (locale === "en") return text;
  const key = normalize(text);
  if (dictionaries[locale][key]) return dictionaries[locale][key];
  if (/^[A-Z][A-Z_ ]+$/.test(key)) {
    const word = key
      .replaceAll("_", " ")
      .toLowerCase()
      .replace(/^./, (c) => c.toUpperCase());
    if (dictionaries[locale][word]) return dictionaries[locale][word];
  }
  for (const pattern of patterns) {
    const match = key.match(pattern.regex);
    if (match)
      return dictionaries[locale][pattern.key].replace(
        /\{(\d+)\}/g,
        (_, n) => match[Number(n) + 1] || "",
      );
  }
  return text;
}
export function formatters(locale: Locale) {
  const t = (text: string) => translate(locale, text);
  return {
    locale,
    t,
    label: (code: string) =>
      t(
        code
          .replaceAll("_", " ")
          .toLowerCase()
          .replace(/^./, (c) => c.toUpperCase()),
      ),
    money: (value: number, currency = "EUR") =>
      new Intl.NumberFormat(locales[locale], {
        style: "currency",
        currency,
        currencyDisplay: "code",
      }).format(value),
    percent: (value: number) =>
      new Intl.NumberFormat(locales[locale], {
        style: "percent",
        maximumFractionDigits: 0,
      }).format(value),
    exchangeRate: (value: number) =>
      new Intl.NumberFormat(locales[locale], {
        maximumFractionDigits: 10,
      }).format(value),
    number: (value: number) =>
      new Intl.NumberFormat(locales[locale], {
        maximumFractionDigits: 3,
      }).format(value),
    date: (value: string) =>
      new Intl.DateTimeFormat(locales[locale], {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        timeZone: "UTC",
      }).format(new Date(value.length === 10 ? value + "T00:00:00Z" : value)),
    time: (value: string) =>
      new Intl.DateTimeFormat(locales[locale], {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      }).format(new Date(value)),
  };
}

"use client";
import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useSyncExternalStore,
} from "react";
import { formatters, type Locale } from "./core";
let memoryLocale: Locale | undefined;
function getLocale(): Locale {
  try {
    const saved = window.localStorage.getItem("lattice-locale");
    if (saved === "en" || saved === "vi" || saved === "zh") return saved;
  } catch {}
  if (memoryLocale) return memoryLocale;
  return navigator.language.startsWith("vi")
    ? "vi"
    : navigator.language.startsWith("zh")
      ? "zh"
      : "en";
}
function subscribe(listener: () => void) {
  window.addEventListener("storage", listener);
  window.addEventListener("lattice-language", listener);
  return () => {
    window.removeEventListener("storage", listener);
    window.removeEventListener("lattice-language", listener);
  };
}
function setLocale(locale: Locale) {
  memoryLocale = locale;
  try {
    window.localStorage.setItem("lattice-locale", locale);
  } catch {}
  window.dispatchEvent(new Event("lattice-language"));
}
const I18nContext = createContext({ ...formatters("en"), setLocale });
export function I18nProvider({ children }: { children: React.ReactNode }) {
  const locale = useSyncExternalStore(
    subscribe,
    getLocale,
    () => "en" as Locale,
  );
  useEffect(() => {
    document.documentElement.lang = locale === "zh" ? "zh-Hans" : locale;
    document.title =
      locale === "vi"
        ? "LATTICE · Điều phối tài chính đã xác minh"
        : locale === "zh"
          ? "LATTICE · 经核实的财务规划"
          : "LATTICE · Verified financial orchestration";
  }, [locale]);
  const value = useMemo(() => ({ ...formatters(locale), setLocale }), [locale]);
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}
export const useI18n = () => useContext(I18nContext);
export function LanguageSelect() {
  const { locale, setLocale, t } = useI18n();
  return (
    <label className="language-select">
      <span className="sr-only">{t("Language")}</span>
      <select
        aria-label={t("Language")}
        data-testid="language-select"
        value={locale}
        onChange={(e) => setLocale(e.target.value as Locale)}
      >
        <option value="en">English</option>
        <option value="vi">Tiếng Việt</option>
        <option value="zh">简体中文</option>
      </select>
    </label>
  );
}

"use client";
import { useI18n } from "@/lib/i18n/context";
import {
  ShieldCheck,
  AlertTriangle,
  ArrowUpRight,
  LoaderCircle,
} from "lucide-react";

import type { Coverage } from "@/lib/types";
export function Badge({ value }: { value: string }) {
  const { label } = useI18n();

  const green = [
    "VERIFIED",
    "USER_CONFIRMED",
    "SOURCE_VERIFIED",
    "AVAILABLE",
    "ACTIVE",
    "SAFE",
    "EXECUTED",
    "APPROVED",
  ].includes(value);
  const red = [
    "BLOCKED",
    "STALE",
    "FAILED",
    "CONFLICTED",
    "SECURITY_REVIEW",
  ].includes(value);
  return (
    <span className={`badge ${green ? "green" : red ? "red" : "amber"}`}>
      {label(value)}
    </span>
  );
}
export function Empty({
  title,
  children,
}: {
  title: string;
  children?: React.ReactNode;
}) {
  const { t } = useI18n();
  return (
    <div className="empty">
      <ShieldCheck size={28} />
      <h3>{t(title)}</h3>
      <p>
        {children ||
          t(
            "Load Maya from the demo controls to start a reproducible walkthrough.",
          )}
      </p>
    </div>
  );
}
export function Loading() {
  const { t } = useI18n();

  return (
    <div className="loading">
      <LoaderCircle className="spin" />
      {t("Loading verified workspace…")}
    </div>
  );
}
export function PageHeader({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow: string;
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  const { t } = useI18n();
  return (
    <div className="page-heading">
      <div>
        <div className="eyebrow">{t(eyebrow)}</div>
        <h1>{t(title)}</h1>
        <p>{t(description)}</p>
      </div>
      {action}
    </div>
  );
}
export function Metric({
  label: heading,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail: string;
}) {
  const { t } = useI18n();
  return (
    <div className="metric">
      <span>{t(heading)}</span>
      <strong>{value}</strong>
      <small>{t(detail)}</small>
    </div>
  );
}
export function CoverageTable({ coverage }: { coverage: Coverage[] }) {
  const { t, money, percent, date } = useI18n();

  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>{t("Commitment")}</th>
            <th>{t("Due")}</th>
            <th>{t("Nominal")}</th>
            <th>{t("Verified")}</th>
            <th>{t("On-time verified")}</th>
            <th>{t("Status")}</th>
          </tr>
        </thead>
        <tbody>
          {coverage.map((c) => (
            <tr key={c.obligation_id}>
              <td>
                <strong>{t(c.label)}</strong>
                <small>{money(c.amount, c.currency)}</small>
              </td>
              <td>{date(c.due_date)}</td>
              {[c.nominal, c.verified, c.on_time_verified].map((v, i) => (
                <td key={i}>
                  <div className="coverage-value">
                    {percent(v)}
                    <div className={`bar ${i === 2 ? "teal" : ""}`}>
                      <i style={{ width: `${Math.round(v * 100)}%` }} />
                    </div>
                  </div>
                </td>
              ))}
              <td>
                <Badge
                  value={
                    !c.in_horizon
                      ? "OUTSIDE_HORIZON"
                      : c.on_time_verified >= 1
                        ? "SAFE"
                        : "AT_RISK"
                  }
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
export function Notice({
  children,
  danger = false,
}: {
  children: React.ReactNode;
  danger?: boolean;
}) {
  const { t } = useI18n();
  return (
    <div className={`notice ${danger ? "danger" : ""}`}>
      <AlertTriangle size={17} />
      <div>{typeof children === "string" ? t(children) : children}</div>
    </div>
  );
}
export function Arrow() {
  return <ArrowUpRight size={16} />;
}

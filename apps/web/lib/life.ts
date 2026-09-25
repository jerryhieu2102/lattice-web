import { z } from "zod";
import type { Coverage, Candidate } from "./types";
export const eventTypes = [
  "PURCHASE_INTENT",
  "EXPENSE_OCCURRED",
  "NEW_OBLIGATION",
  "OBLIGATION_CHANGED",
  "FUNDING_EXPECTED",
  "FUNDING_RECEIVED",
  "FUNDING_DELAYED",
  "FUNDING_REDUCED",
  "RECURRING_EXPENSE",
  "REFUND_EXPECTED",
  "REIMBURSEMENT_EXPECTED",
  "BORROWING",
  "LENDING",
  "TRANSFER_PENDING",
  "TRANSFER_FAILED",
  "TRAVEL_PLAN",
  "EDUCATION_EXPENSE",
  "HOUSING_EVENT",
  "HEALTH_EXPENSE",
  "FAMILY_SUPPORT",
  "SAVINGS_GOAL",
  "SECURITY_INCIDENT",
  "ACCOUNT_UNAVAILABLE",
  "FX_CONCERN",
  "EMERGENCY",
  "OTHER",
] as const;
export const envelopeCategories = [
  "FLIGHT",
  "ACCOMMODATION",
  "LOCAL_TRANSPORT",
  "FOOD",
  "VISA",
  "INSURANCE",
  "ACTIVITIES",
  "BUFFER",
] as const;
export const expectedTypes = [
  "FUNDING_EXPECTED",
  "REFUND_EXPECTED",
  "REIMBURSEMENT_EXPECTED",
  "TRANSFER_PENDING",
  "FAMILY_SUPPORT",
];
export const overlayTypes = [
  "FUNDING_DELAYED",
  "FUNDING_REDUCED",
  "TRANSFER_FAILED",
  "ACCOUNT_UNAVAILABLE",
];
export interface LifeProposal {
  event_type: (typeof eventTypes)[number];
  mode: "HYPOTHETICAL" | "ACTUAL" | "EXPECTED";
  title: string;
  amount_minor: number | null;
  amount_min_minor: number | null;
  amount_max_minor: number | null;
  currency: string | null;
  event_date: string | null;
  expected_date: string | null;
  date_window_start: string | null;
  date_window_end: string | null;
  counterparty: string | null;
  category: string;
  essentiality: "ESSENTIAL" | "DISCRETIONARY" | "UNKNOWN";
  priority: string;
  recurrence_rule: string | null;
  confidence: number;
  funding_source_id: string | null;
  obligation_id: string | null;
  delay_days: number | null;
  amount_is_delta: boolean;
  receivable_minor: number | null;
  repayment_date: string | null;
  repayment_minor: number | null;
  envelope: {
    category: (typeof envelopeCategories)[number];
    amount_minor: number;
    currency: string;
  }[];
  security_flags: string[];
  question: boolean;
}
export interface SafeBudget {
  currency: string;
  today: number;
  this_week: number;
  this_month: number;
  dates: string[];
  horizon_days: number;
  plan_state: string;
  liquid_eur: number;
  reserve_eur: number;
  shortfall_eur: number;
  committed_eur: number;
  verified_coverage: number;
  coverage: Coverage[];
  pending_events: number;
  explanation: string;
}
export interface Runway {
  verified: { days: number; bounded: boolean; first_gap: Coverage | null };
  including_expected: {
    days: number;
    bounded: boolean;
    first_gap: Coverage | null;
  };
  next_critical: Coverage | null;
  limitation: string;
}
export interface Impact {
  before: SafeBudget;
  after: SafeBudget | null;
  missing: string[];
  affected?: Coverage[];
  difference?: {
    liquid_eur: number;
    reserve_eur: number;
    safe_to_spend: number;
  };
  options: {
    type: string;
    amount?: number;
    currency?: string;
    date?: string;
    conditional?: boolean;
  }[];
  variants: {
    label: string;
    amount_minor: number | null;
    event_date: string;
    after: SafeBudget;
  }[];
  effects?: {
    cash_gap_eur?: number;
    assumptions: string[];
    debits?: {
      funding_source_id: string;
      amount: number;
      currency: string;
      fee: number;
    }[];
  };
  rescue?: { candidates: Candidate[]; best_index: number | null };
  goal?: {
    monthly_required: number;
    safe_initial_contribution: number;
    soft_goal: boolean;
  };
  trip_total_eur?: number;
  runway?: Runway;
}
export interface LifeEvent {
  id: string;
  version: number;
  status: string;
  raw_input: string;
  title: string;
  verification_status: string;
  proposal: LifeProposal;
  impact: Impact | null;
  missing: string[];
  linked_funding_source_id: string | null;
  linked_obligation_id: string | null;
  metadata_json: {
    reminder_muted?: boolean;
    received_date?: string;
    receivable_event_id?: string;
  };
  recurring_summary?: {
    monthly_cost: number;
    annual_cost: number;
    currency: string;
    next_renewal: string | null;
  } | null;
}
export interface LifeInbox {
  events: LifeEvent[];
  budget: SafeBudget;
  runway: Runway;
  notifications: {
    id: string;
    type: string;
    title: string;
    date: string;
    href: string;
  }[];
}
export const captureSchema = z.object({
  raw_input: z.string().trim().min(3).max(4000),
  locale: z.enum(["en", "vi", "zh"]),
});
export function toMinor(raw: string, decimals: number): number | null {
  if (!raw.trim()) return null;
  const pattern = decimals
    ? new RegExp(`^\\d+(?:\\.\\d{1,${decimals}})?$`)
    : /^\d+$/;
  if (!pattern.test(raw))
    throw new Error(
      "Invalid input. Check all required fields, amounts, dates, and currency precision.",
    );
  const [whole, fraction = ""] = raw.split(".");
  const value =
    Number(whole) * 10 ** decimals + Number(fraction.padEnd(decimals, "0"));
  return z
    .number()
    .int()
    .min(0)
    .max(Math.min(100_000_000_000, 1_000_000_000 * 10 ** decimals))
    .parse(value);
}

export interface Actor {
  id: string;
  role: string;
  display_name: string;
  email: string;
  student_id: string | null;
}
export interface Funding {
  id: string;
  owner_actor_id: string;
  source_type: string;
  label: string;
  amount: number;
  currency: string;
  available_from: string;
  availability_status: string;
  verification_status: string;
  restriction_type: string;
  minimum_remaining_balance: number;
}
export interface Obligation {
  id: string;
  label: string;
  type: string;
  amount: number;
  currency: string;
  due_date: string;
  priority: string;
  beneficiary: string;
  security_hold: boolean;
  beneficiary_verified: boolean;
  budget_only?: boolean;
  verification_status: string;
  status: string;
  installment_option: {
    amounts: number[];
    dates: string[];
    fee: number;
  } | null;
}
export interface Coverage {
  obligation_id: string;
  type?: string;
  label: string;
  amount: number;
  currency: string;
  due_date: string;
  priority: string;
  nominal: number;
  verified: number;
  on_time_verified: number;
  on_time_nominal?: number;
  shortfall: number;
  in_horizon: boolean;
}
export interface Allocation {
  funding_source_id: string;
  obligation_id: string;
  transfer_route_id: string;
  source_amount: number;
  destination_amount: number;
  estimated_fee: number;
  estimated_rounding_cost_eur?: number;
  source_currency: string;
  currency: string;
  scheduled_date: string;
  expected_arrival_date: string;
  status: string;
}
export interface Summary {
  allocations: Allocation[];
  coverage: Coverage[];
  feasible: boolean;
  verified_feasible: boolean;
  total_estimated_cost: number;
  constraint_violations: number;
  horizon_end: string;
  safe_to_spend: Record<string, number>;
  solver_status: string;
}
export interface Plan {
  id: string;
  status: string;
  version: number;
  summary: Summary;
  explanation: string;
  stress_failure_rate: number | null;
}
export interface Fact {
  id: string;
  field: string;
  normalized_value: string;
  verification_status: string;
  evidence_text: string;
  confidence: number;
  source_page: number;
}
export interface DocumentRecord {
  owner_id: string;
  id: string;
  filename: string;
  document_type: string;
  trust_level: string;
  status: string;
  security_flags: string[];
  facts?: Fact[];
  text: string;
}
export interface Scenario {
  id: string;
  scenario_failure_rate: number;
  forecast_failure_rate: number;
  mean_shortfall_eur: number;
  p95_shortfall_eur: number;
  iterations: number;
  baseline_coverage: Coverage[];
  after_coverage: Coverage[];
  histogram: { bucket: string; count: number }[];
}
export interface Candidate {
  id: string;
  plan_id: string;
  type: string;
  title: string;
  feasible: boolean;
  conditional: boolean;
  family_contribution_eur: number;
  direct_cost_eur: number;
  reserve_impact_eur: number;
  friction: number;
  people_involved: number;
  score: number;
  assumptions: string[];
  scenario_failure_rate: number;
}
export interface Action {
  id: string;
  type: string;
  status: string;
  contribution_eur?: number;
  required_approvals?: string[];
  approvals?: string[];
  payload?: { required_approvals: string[]; approvals: string[] };
}
export interface Permission {
  id: string;
  owner_actor_id: string;
  target_actor_id: string;
  resource_type: string;
  resource_id: string;
  permission_type: string;
  revoked_at: string | null;
}
export interface Audit {
  id: string;
  sequence: number;
  event_type: string;
  category: string;
  created_at: string;
  payload: Record<string, unknown>;
  event_hash: string;
  previous_hash: string;
}
export interface Route {
  id: string;
  provider_name: string;
  from_currency: string;
  to_currency: string;
  fixed_fee: number;
  percentage_fee: number;
  fx_rate: number;
  settlement_p95_days: number;
}
export interface GraphData {
  nodes: {
    id: string;
    type: string;
    position: { x: number; y: number };
    data: Record<string, unknown>;
  }[];
  edges: {
    id: string;
    source: string;
    target: string;
    label: string;
    data: Record<string, unknown>;
  }[];
}
export type Notify = (message: string, error?: boolean) => void;

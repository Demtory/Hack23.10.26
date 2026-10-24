export type Level = "high" | "medium" | "low" | "unknown";

export interface CustomerListItem {
  id: number;
  email: string;
  balance: number;
  totalReplenished: number;
  score: number | null;
  level: Level;
  expectedLoss: number;
  amountAtRisk: number;
  servicesAtRisk: number;
}

export interface RuleExplanation {
  code: "status_floor" | "stale_status_floor" | "customer_bonus" | "score_cap";
  scope: "service" | "customer";
  serviceId: number | null;
  label: string;
  beforeScore: number;
  afterScore: number;
  delta: number;
  relatedServiceIds: number[];
}

export interface Driver {
  code: string;
  label: string;
  contribution: number;
  value?: number;
}

export interface Service {
  id: number;
  name: string;
  price: number;
  paymentTerm: string;
  status: string;
  autoProlong: boolean;
  createdAt: string;
  expiresAt: string;
  score: number;
  level: Level;
  confidence: number;
  staleStatus: boolean;
  drivers: Driver[];
  explanationRules?: RuleExplanation[];
  values: Record<string, number | null>;
  expiryDays: number;
}

export interface Money {
  amountAtRisk: number;
  expectedLoss: number;
  coveredLoss: number;
  coverage: number;
  mitigation: number;
}

export interface CustomerDetail {
  calculation: CalculationContext;
  asOf:string;
  updatedAt:string;
  id: number;
  email: string;
  balance: number;
  withdrawBalance: number;
  bonusBalance: number;
  bonusState: "locked" | "unlocked";
  totalReplenished: number;
  score: number | null;
  level: Level;
  confidence: number;
  summary: string;
  drivers: Driver[];
  explanationRules?: RuleExplanation[];
  services: Service[];
  money: Money;
  unknownReason: string | null;
  isEstimated: boolean;
}

export interface CountsByLevel {
  high: number;
  medium: number;
  low: number;
  unknown: number;
}

export interface CalculationContext {
  runId: number;
  settingsVersion: number;
  thresholds: { medium: number; high: number };
}

export interface Summary {
  calculation?: CalculationContext;
  countsByLevel: CountsByLevel;
  totalCustomers: number;
  scoredCustomers: number;
  servicesAtRisk: number;
  expectedLoss: number;
  amountAtRisk: number;
  coverage: number;
  aggregateCoverage: number;
  underfundedCustomers: number;
  avgScore: number | null;
  asOf: string;
  updatedAt: string;
  currency: string;
}

export interface FeatureMeta {
  code: string;
  title: string;
  description: string;
  min: number;
  max: number;
  step: number;
  default: number;
}

export interface ModelSettings {
  weights: Record<string, number>;
  thresholds: { medium: number; high: number };
  probability: { midpoint: number; steepness: number; floor: number; ceiling: number };
  money: { balanceMitigation: number; includeWithdrawBalance: boolean };
  statusFloors: Record<string, number>;
  recomputeIntervalSec: number;
  features: FeatureMeta[];
  version: number;
  updatedAt: string;
}

export interface CustomerPage {
  topLosses: CustomerListItem[];
  summary: Summary;
  calculation: CalculationContext;
  items: CustomerListItem[];
  total: number;
  page: number;
  pageSize: number;
}

export interface Snapshot {
  accounts: unknown[];
  services: unknown[];
  transactions: unknown[];
}

export interface User {
  id: number;
  email: string;
}

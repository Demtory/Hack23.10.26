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

export interface EmailDraft {
  situation: "prolong_wait" | "blocked" | "suspended" | "funds_gap" | "expiry_auto_off" | "unknown" | "on_track";
  situationLabel: string;
  subject: string;
  body: string;
  recipient: string;
  serviceId: number | null;
  serviceName: string | null;
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
  summaryDetails: string[];
  emailDraft?: EmailDraft | null;
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

export interface ForecastPoint {
  date: string;
  end: string;
  services: number;
  expectedNonRenewals: number;
  expectedLoss: number;
}

export interface ForecastFactPoint {
  date: string;
  end: string;
  services: number;
  customers: number;
}

export interface Forecast {
  asOf: string;
  pastDays: number;
  horizonDays: number;
  currency: string;
  fact: ForecastFactPoint[];
  forecast: ForecastPoint[];
  totals: {
    factServices: number;
    factCustomers: number;
    forecastServices: number;
    servicesAtRisk: number;
    expectedNonRenewals: number;
    expectedLoss: number;
  };
  note: string;
}

export interface ForecastDayItem {
  serviceId: number;
  serviceName: string;
  customerId: number;
  email: string;
  price: number;
  score: number;
  level: Level;
  status: string;
  expiresAt: string;
  probability?: number | null;
  expectedLoss?: number | null;
}

export interface ForecastDay {
  date: string;
  end: string;
  kind: "fact" | "forecast";
  services: number;
  customers: number;
  expectedNonRenewals: number;
  expectedLoss: number;
  items: ForecastDayItem[];
  truncated: boolean;
}

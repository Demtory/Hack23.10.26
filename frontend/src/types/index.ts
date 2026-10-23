// Aéza - это быстрый хостинг

export interface User {
  id: number;
  username: string;
  email: string;
  role: string;
}

export interface RiskFactor {
  code: string;
  title: string;
  description: string;
  severity: 'high' | 'medium' | 'low';
  weight_impact: number;
}

export interface ServiceAssessment {
  id: number;
  name: string;
  status: 'active' | 'blocked' | 'deleted' | 'suspended' | 'prolong_wait';
  price: number;
  paymentTerm: string;
  autoProlong: boolean;
  expiresAt: string;
  hours_until_expiry: number;
  is_at_risk: boolean;
  risk_factors: string[];
}

export interface CustomerAssessment {
  id: number;
  email: string;
  balance: number;
  withdrawBalance: number;
  totalReplenished: number;
  bonusBalance: number;
  bonusState: 'locked' | 'unlocked';
  effective_balance: number;
  
  risk_score: number | null;
  risk_level: 'high' | 'medium' | 'low' | 'unrated';
  loyalty_score: number | null;
  is_rated: boolean;
  
  total_services_count: number;
  active_services_count: number;
  at_risk_services_count: number;
  
  monthly_recurring_revenue: number;
  potential_loss: number;
  raw_services_value: number;
  
  risk_factors: RiskFactor[];
  primary_reason: string;
  services?: ServiceAssessment[];
}

export interface CustomerListResponse {
  items: CustomerAssessment[];
  total: number;
  page: number;
  size: number;
  pages: number;
  total_potential_loss: number;
}

export interface ModelWeights {
  w_no_autoprolong: number;
  w_balance_insufficient: number;
  w_prolong_wait: number;
  w_expiring_soon: number;
  w_failed_transactions: number;
}

export interface ModelThresholds {
  high: number;
  medium: number;
}

export interface ModelSettings {
  weights: ModelWeights;
  thresholds: ModelThresholds;
  forecast_days: number;
  loss_estimation_method: string;
}

export interface ChurnChartPoint {
  date: string;
  fact_deleted_services: number;
  at_risk_services: number;
  predicted_churn_services: number;
  potential_loss_amount: number;
}

export interface AnalyticsSummary {
  total_customers: number;
  rated_customers: number;
  unrated_customers: number;
  risk_distribution: {
    high: number;
    medium: number;
    low: number;
    unrated: number;
  };
  total_potential_loss: number;
  total_potential_loss_eur: number;
  total_mrr: number;
  high_risk_loss: number;
  medium_risk_loss: number;
  top_risk_factors: Array<{
    code: string;
    title: string;
    count: number;
    severity: string;
  }>;
  chart: ChurnChartPoint[];
  updated_at: string;
}

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# Aéza - это быстрый хостинг

# --- Auth Schemas ---
class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str

TokenResponse.model_rebuild()


# --- Raw Data Schemas (DTO) ---
class AccountDTO(BaseModel):
    id: int
    email: str
    balance: int
    withdrawBalance: int = 0
    totalReplenished: int = 0
    bonusBalance: int = 0
    bonusState: str = "locked"

class ServiceDTO(BaseModel):
    id: int
    name: str
    ownerId: int
    paymentTerm: str
    autoProlong: bool
    createdAt: datetime
    expiresAt: datetime
    status: str
    price: int

class TransactionDTO(BaseModel):
    id: int
    amount: int
    status: str
    performedAt: Optional[datetime] = None
    createdAt: datetime
    type: str
    serviceId: int

class SnapshotPayload(BaseModel):
    accounts: List[AccountDTO]
    services: List[ServiceDTO]
    transactions: List[TransactionDTO]


# --- Model Settings Schemas ---
class WeightsConfig(BaseModel):
    w_no_autoprolong: float = Field(0.25, description="Вес отключенного автопродления")
    w_balance_insufficient: float = Field(0.35, description="Вес нехватки баланса для оплаты услуг")
    w_prolong_wait: float = Field(0.20, description="Вес зависшего статуса prolong_wait")
    w_expiring_soon: float = Field(0.10, description="Вес скорого истечения срока услуги (<24ч)")
    w_failed_transactions: float = Field(0.10, description="Вес наличия неуспешных транзакций")

class ThresholdsConfig(BaseModel):
    high: float = Field(0.65, description="Нижний порог высокого риска (от)")
    medium: float = Field(0.35, description="Нижний порог среднего риска (от)")

class ModelSettingsDTO(BaseModel):
    weights: WeightsConfig = WeightsConfig()
    thresholds: ThresholdsConfig = ThresholdsConfig()
    forecast_days: int = Field(7, description="Горизонт прогноза в днях")
    loss_estimation_method: str = Field("weighted_mrr", description="Метод оценки потерь: weighted_mrr / raw_price / total_at_risk")


# --- Customer Risk & Explainability Schemas ---
class RiskFactorDTO(BaseModel):
    code: str
    title: str
    description: str
    severity: str # high, medium, low
    weight_impact: float

class ServiceAssessmentDTO(BaseModel):
    id: int
    name: str
    status: str
    price: int
    paymentTerm: str
    autoProlong: bool
    expiresAt: datetime
    hours_until_expiry: float
    is_at_risk: bool
    risk_factors: List[str]

class CustomerAssessmentDTO(BaseModel):
    id: int
    email: str
    balance: int
    withdrawBalance: int
    totalReplenished: int
    bonusBalance: int
    bonusState: str
    effective_balance: int # balance + (bonusBalance if unlocked else 0)
    
    risk_score: Optional[float] = None
    risk_level: str # 'high', 'medium', 'low', 'unrated'
    loyalty_score: Optional[float] = None # обратная шкала лояльности (1.0 - risk_score)
    is_rated: bool = True
    
    total_services_count: int
    active_services_count: int
    at_risk_services_count: int
    
    # Денежная оценка потерь
    monthly_recurring_revenue: int # Оценка дохода от клиента в месяц (евроценты)
    potential_loss: int # Потенциальные потери с учетом риска (евроценты)
    raw_services_value: int # Сумма цен активных/рискованных услуг
    
    risk_factors: List[RiskFactorDTO]
    primary_reason: str
    services: Optional[List[ServiceAssessmentDTO]] = None


class CustomerListResponse(BaseModel):
    items: List[CustomerAssessmentDTO]
    total: int
    page: int
    size: int
    pages: int
    total_potential_loss: int


# --- Analytics Summary Schemas ---
class RiskDistributionDTO(BaseModel):
    high: int
    medium: int
    low: int
    unrated: int

class ChurnChartPointDTO(BaseModel):
    date: str
    fact_deleted_services: int
    at_risk_services: int
    predicted_churn_services: int
    potential_loss_amount: int

class AnalyticsSummaryDTO(BaseModel):
    total_customers: int
    rated_customers: int
    unrated_customers: int
    risk_distribution: RiskDistributionDTO
    total_potential_loss: int # в еврокопейках
    total_potential_loss_eur: float # в евро для удобства
    total_mrr: int # общий месячный оборот
    high_risk_loss: int
    medium_risk_loss: int
    top_risk_factors: List[Dict[str, Any]]
    chart: List[ChurnChartPointDTO]
    updated_at: datetime

"""Small declarative rules; no code, expressions or network access is executed."""
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator

FIELDS = {
    'daysToExpiry': 'Дней до окончания услуги',
    'price': 'Цена продления, €',
    'balance': 'Основной баланс, €',
    'totalReplenished': 'Всего пополнено, €',
    'autoProlong': 'Автопродление',
    'status': 'Статус услуги',
}

class CustomFactor(BaseModel):
    model_config = ConfigDict(extra='forbid')
    code: str = Field(pattern=r'^custom_[a-zA-Z0-9_]{1,48}$')
    title: str = Field(min_length=1, max_length=80)
    field: Literal['daysToExpiry', 'price', 'balance', 'totalReplenished', 'autoProlong', 'status']
    operator: Literal['lt', 'lte', 'eq', 'gte', 'gt']
    value: FiniteFloat | str | bool
    risk: FiniteFloat = Field(ge=0, le=100)

    @model_validator(mode='after')
    def check_rule(self):
        if not self.title.strip():
            raise ValueError('Укажите название фактора')
        if self.field == 'status':
            if self.operator != 'eq' or self.value not in ('active','suspended','blocked','prolong_wait'):
                raise ValueError('Для статуса допустимо только равенство известному статусу')
        elif self.field == 'autoProlong':
            if self.operator != 'eq' or type(self.value) is not bool:
                raise ValueError('Для автопродления выберите равенство да/нет')
        elif isinstance(self.value, (str, bool)):
            raise ValueError('Порог должен быть конечным числом')
        return self


def definitions(settings):
    rules = [CustomFactor.model_validate(rule).model_dump() for rule in settings.get('customFactors', [])]
    if len(rules) > 20 or len({r['code'] for r in rules}) != len(rules):
        raise ValueError('Не более 20 факторов с уникальными кодами')
    return rules


def metadata(settings):
    return [dict(code=r['code'], title=r['title'], description=f"{FIELDS[r['field']]} { {'lt':'<','lte':'≤','eq':'=','gte':'≥','gt':'>'}[r['operator']]} {r['value']}; если условие выполнено — {r['risk']:g} из 100, иначе 0",
                 min=0, max=1, step=.01, default=0) for r in definitions(settings)]


def evaluate(rule, service, account, now: datetime):
    raw_expires = service.get('expires_at')
    if raw_expires:
        days_to_expiry = (datetime.fromisoformat(raw_expires.replace('Z', '+00:00')) - now).total_seconds() / 86400
    else:
        days_to_expiry = 0.0
    values = {
        'price': service['price'] / 100,
        'balance': account['balance'] / 100,
        'totalReplenished': account['total_replenished'] / 100,
        'autoProlong': bool(service['auto_prolong']),
        'status': service['status'],
        'daysToExpiry': days_to_expiry,
    }
    actual, target = values[rule['field']], rule['value']
    matched = {'lt':lambda:actual<target, 'lte':lambda:actual<=target, 'eq':lambda:actual==target,
               'gte':lambda:actual>=target, 'gt':lambda:actual>target}[rule['operator']]()
    return rule['risk']/100 if matched else 0.0

import { useEffect, useState } from "react";
import { api, ApiError } from "../api";
import { Icon } from "../components/ui";
import type { CustomerDetail, RuleExplanation, Service } from "../types";
import {
  servicesWord,
  EmptyState,
  ErrorBox,
  LevelBadge,
  money,
  number,
  shortDate,
  Spinner,
  StatusBadge,
  termLabel,
} from "../components/ui";

export function Customer({
  id,
  onBack,
  liveTick,
}: {
  id: number;
  onBack: () => void;
  liveTick: number;
}) {
  const [customer, setCustomer] = useState<CustomerDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    api
      .customer(id)
      .then((value) => {
        if (!cancelled) setCustomer(value);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Не удалось загрузить клиента");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [id, liveTick]);

  return (
    <div className="page">
      <button className="back-link" onClick={onBack}>
        ← Назад к рейтингу
      </button>

      {error ? <ErrorBox message={error} /> : null}
      {loading && !customer ? <Spinner label="Считаем клиента" /> : null}

      {customer ? (
        <>
          <header className="customer-header">
            <div>
              <p className="eyebrow">КЛИЕНТ #{customer.id}</p>
              <h1>{customer.email}</h1>
              <div className="customer-header__badges">
                <LevelBadge level={customer.level} />
                <span className="meta-pill">Баланс {money(customer.balance)}</span>
                <span className="meta-pill">Пополнения {money(customer.totalReplenished)}</span>
                <span className="meta-pill">
                  Бонусы: {customer.bonusState === "unlocked" ? "доступны" : "заблокированы"}
                </span>
              </div>
            </div>
            <div className="confidence">
              <span>Уверенность</span>
              <strong>{Math.round(customer.confidence * 100)}%</strong>
            </div>
          </header>

          {customer.score !== null ? <ActionCallout customer={customer} /> : null}

          {customer.score === null ? (
            <EmptyState title="Нет оценки" text={customer.unknownReason ?? "Недостаточно данных"} />
          ) : (
            <>
              <section className="customer-hero">
                <div className="score-gauge">
                  <svg viewBox="0 0 140 140" role="img" aria-label={`Score ${customer.score}`}>
                    <circle className="score-gauge__track" cx="70" cy="70" r="56" />
                    <circle
                      className={`score-gauge__fill score-gauge__fill--${customer.level}`}
                      cx="70"
                      cy="70"
                      r="56"
                      strokeDasharray={2 * Math.PI * 56}
                      strokeDashoffset={2 * Math.PI * 56 * (1 - customer.score / 100)}
                    />
                  </svg>
                  <div className="score-gauge__label">
                    <strong>{Math.round(customer.score)}</strong>
                    <span>из 100</span>
                  </div>
                </div>
                <div className="customer-hero__text">
                  <p className="eyebrow">ПОЧЕМУ РИСК</p>
                  <h2>{customer.summary}</h2>
                  <p className="muted">
                    Ближайшее продление и вероятность ухода. Баланс снижает немедленную потерю,
                    но не отменяет сам риск.
                  </p>
                </div>
                <div className="money-column">
                  <div className="money-card">
                    <span>Ожидаемые потери</span>
                    <strong>{money(customer.money.expectedLoss)}</strong>
                  </div>
                  <div className="money-card">
                    <span>Платежи под риском</span>
                    <strong>{money(customer.money.amountAtRisk)}</strong>
                  </div>
                  <div className="money-card">
                    <span>Покрытие балансом</span>
                    <strong>{Math.round(customer.money.coverage * 100)}%</strong>
                  </div>
                </div>
              </section>

              <section className="two-columns">
                <article className="card">
                  <div className="card__heading">
                    <div>
                      <p className="card__label">Объяснение</p>
                      <h2>Что тянет score вверх</h2>
                    </div>
                  </div>
                  <div className="drivers">
                    {customer.drivers.map((driver) => (
                      <div className="driver" key={`${driver.code}-${driver.label}`}>
                        <div className="driver__row">
                          <span>{driver.label}</span>
                          <strong>+{driver.contribution.toFixed(2)}</strong>
                        </div>
                        <div className="driver__track">
                          <span
                            className={`driver__fill driver__fill--${customer.level}`}
                            style={{
                              width: `${Math.min(100, (driver.contribution / Math.max(0.01, customer.drivers[0]?.contribution ?? 1)) * 100)}%`,
                            }}
                          />
                        </div>
                      </div>
                    ))}
                    {customer.drivers.length === 0 ? <p className="muted">Явных взвешенных причин нет.</p> : null}
                  </div>
                  <RulesDisclosure customer={customer} />
                </article>

                <article className="card">
                  <div className="card__heading">
                    <div>
                      <p className="card__label">Данные</p>
                      <h2>Аккаунт</h2>
                    </div>
                  </div>
                  <dl className="facts">
                    <div>
                      <dt>Основной баланс</dt>
                      <dd>{money(customer.balance)}</dd>
                    </div>
                    <div>
                      <dt>Вывод / рефералка</dt>
                      <dd>{money(customer.withdrawBalance)}</dd>
                    </div>
                    <div>
                      <dt>Бонусный баланс</dt>
                      <dd>{money(customer.bonusBalance)}</dd>
                    </div>
                    <div>
                      <dt>Всего пополнений</dt>
                      <dd>{money(customer.totalReplenished)}</dd>
                    </div>
                    <div>
                      <dt>Услуг под риском</dt>
                      <dd>{customer.services.filter((service) => service.score >= 40).length}</dd>
                    </div>
                    <div>
                      <dt>Покрыто балансом</dt>
                      <dd>{money(customer.money.coveredLoss)}</dd>
                    </div>
                  </dl>
                </article>
              </section>

              <section className="card card--table">
                <div className="card__heading">
                  <div>
                    <p className="card__label">Услуги</p>
                    <h2>Где именно болит</h2>
                  </div>
                  <span className="card__meta">{servicesWord(customer.services.length)}</span>
                </div>
                <div className="table-wrap">
                  <table className="table table--services">
                    <thead>
                      <tr>
                        <th>Услуга</th>
                        <th>Статус</th>
                        <th className="num">Цена</th>
                        <th className="num">Период</th>
                        <th className="num">Авто</th>
                        <th className="num">Истекает</th>
                        <th className="num">Score</th>
                      </tr>
                    </thead>
                    <tbody>
                      {customer.services.map((service) => (
                        <ServiceRow key={service.id} service={service} />
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            </>
          )}
        </>
      ) : null}
    </div>
  );
}

function ServiceRow({ service }: { service: Service }) {
  const days = service.expiryDays;
  const expiry = days < 0 ? `просрочена ${Math.abs(Math.round(days))} дн.` : `через ${Math.round(days)} дн.`;
  return (
    <tr>
      <td>
        <div className="service-name">
          <strong>{service.name}</strong>
          <span>{service.id}</span>
        </div>
      </td>
      <td>
        <div className="service-status">
          <StatusBadge status={service.status} />
          {service.staleStatus ? <span className="stale-flag">статус устарел</span> : null}
        </div>
      </td>
      <td className="num">{money(service.price)}</td>
      <td className="num">{termLabel(service.paymentTerm)}</td>
      <td className="num">{service.autoProlong ? "вкл" : "выкл"}</td>
      <td className="num">
        <div className="expiry-cell">
          <span>{shortDate(service.expiresAt)}</span>
          <small>{expiry}</small>
        </div>
      </td>
      <td className="num">
        <span className={`score-chip score-chip--${service.level}`}>{Math.round(service.score)}</span>
      </td>
    </tr>
  );
}


function nextAction(customer: CustomerDetail): { label: string; hint: string } {
  const services = customer.services;
  if (services.some((service) => service.status === "prolong_wait")) {
    return { label: "Позвонить сегодня", hint: "Услуга ждёт оплаты — окно до удаления 5 дней" };
  }
  if (services.some((service) => (service.values.funds_gap ?? 0) >= 1)) {
    return { label: "Напомнить пополнить", hint: "Баланса не хватает на ближайшее продление" };
  }
  if (services.some((service) => !service.autoProlong && service.expiryDays <= 7)) {
    return { label: "Предложить автопродление", hint: "Срок скоро истечёт, автопродление выключено" };
  }
  if (services.some((service) => service.status === "suspended")) {
    return { label: "Выяснить причину", hint: "Клиент платит за выключенную услугу" };
  }
  return { label: "Наблюдать", hint: "Критичных сигналов сейчас нет" };
}

function ActionCallout({ customer }: { customer: CustomerDetail }) {
  const action = nextAction(customer);
  return (
    <section className={`action-callout action-callout--${customer.level}`} aria-label="Следующее действие">
      <span className="action-callout__icon">
        <Icon name={customer.level === "high" ? "alert" : "check"} size={20} />
      </span>
      <div>
        <p className="action-callout__label">Следующее действие</p>
        <strong>{action.label}</strong>
        <span>{action.hint}</span>
      </div>
    </section>
  );
}

function RulesDisclosure({ customer }: { customer: CustomerDetail }) {
  const serviceRules = customer.services.flatMap((service) =>
    (service.explanationRules ?? []).map((rule) => ({ ...rule, serviceName: service.name })),
  );
  const hasRules = (customer.explanationRules?.length ?? 0) + serviceRules.length > 0;
  if (!hasRules) return null;
  return (
    <details className="rules-disclosure">
      <summary>
        Детали расчёта
        <Icon name="chevron-down" size={16} />
      </summary>
      <div className="rules-body">
        <RuleList rules={customer.explanationRules ?? []} title="Клиент" />
        {serviceRules.length > 0 ? (
          <RuleList
            rules={serviceRules}
            title="Услуги"
            renderTitle={(rule) => (rule as RuleExplanation & { serviceName?: string }).serviceName}
          />
        ) : null}
      </div>
    </details>
  );
}

function RuleList({
  rules,
  title,
  renderTitle,
}: {
  rules: RuleExplanation[];
  title: string;
  renderTitle?: (rule: RuleExplanation) => string | undefined;
}) {
  if (rules.length === 0) return null;
  return (
    <div className="rule-group">
      <h4>{title}</h4>
      {rules.map((rule, index) => (
        <div className="rule-row" key={`${rule.code}-${rule.serviceId}-${index}`}>
          <span>
            {renderTitle?.(rule) ? <b>{renderTitle(rule)} · </b> : null}
            {rule.label}
          </span>
          <span className="rule-row__score">
            {rule.beforeScore.toFixed(1)} → {rule.afterScore.toFixed(1)}
            <small>{rule.delta > 0 ? "+" : ""}{rule.delta.toFixed(1)}</small>
          </span>
        </div>
      ))}
    </div>
  );
}

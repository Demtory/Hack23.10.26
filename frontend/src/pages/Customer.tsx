import {CalculationContext} from "../components/CalculationContext";
import {EmailDraftDialog} from "../components/EmailDraft";
import { useEffect, useState } from "react";
import { api, ApiError } from "../api";
import type { CustomerDetail, RuleExplanation, Service } from "../types";
import {
  servicesWord,
  EmptyState,
  ErrorBox,
  LevelBadge,
  money,
  number,
  dateTime,
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
  const [retry,setRetry]=useState(0);
  const [loading, setLoading] = useState(true);
  const [emailOpen, setEmailOpen] = useState(false);

  useEffect(() => {
    setEmailOpen(false);
  }, [id]);

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
  }, [id, liveTick,retry]);

  return (
    <div className="page">
      <button className="back-link" onClick={onBack}>
        ← Назад
      </button>

      {error ? <ErrorBox message={error} onRetry={()=>setRetry(x=>x+1)}/> : null}
      {loading && !customer ? <Spinner label="Считаем клиента" /> : null}

      {customer && customer.id===id ? (
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
              <span>Полнота данных</span>
              <strong>{Math.round(customer.confidence * 100)}%</strong>
            </div>
          </header>

          <CalculationContext asOf={customer.asOf} updatedAt={customer.updatedAt}/>
          <p className="notice">Деньги — эвристическая оценка ближайших платежей разных услуг, не гарантированный убыток и не месячная выручка. При отсутствии оценки нулевые потери не доказывают безопасность.</p>
          {customer.score === null ? (
            <>
              <EmptyState title="Нет оценки" text={customer.unknownReason ?? "Недостаточно данных"} />
              {customer.emailDraft ? (
                <div className="hero-actions">
                  <button className="button button--primary" onClick={() => setEmailOpen(true)}>
                    Письмо клиенту
                  </button>
                </div>
              ) : null}
            </>
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
                  {customer.summaryDetails?.length ? (
                    <details className="details">
                      <summary>Подробное пояснение</summary>
                      <ul className="details__list">
                        {customer.summaryDetails.map((fact) => (
                          <li key={fact}>{fact}</li>
                        ))}
                      </ul>
                    </details>
                  ) : null}
                  <div className="hero-actions">
                    {customer.emailDraft ? (
                      <button className="button button--primary" onClick={() => setEmailOpen(true)}>
                        Письмо клиенту
                      </button>
                    ) : null}
                  </div>
                  <p className="muted">
                    Экспертная оценка, не статистически подтверждённая вероятность. Баланс снижает денежную оценку,
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
                  {(customer.explanationRules?.length ?? 0) > 0 ||
                  customer.services.some((service) => (service.explanationRules?.length ?? 0) > 0) ? (
                    <details className="details details--rules">
                      <summary>Детали расчёта</summary>
                      <RuleList rules={customer.explanationRules ?? []} title="Правила клиента" />
                      {customer.services.map((service) => (
                        <RuleList key={service.id} rules={service.explanationRules ?? []} title={`Правила услуги ${service.name}`} />
                      ))}
                    </details>
                  ) : null}
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
                      <dd>{customer.services.filter((service) => service.level === "medium" || service.level === "high").length}</dd>
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
                  <table className="table table--services"><caption className="sr-only">Услуги клиента, цена в EUR и платёжный период</caption>
                    <thead>
                      <tr>
                        <th scope="col">Услуга</th>
                        <th scope="col">Статус</th>
                        <th scope="col" className="num">Цена</th>
                        <th scope="col" className="num">Период</th>
                        <th scope="col" className="num">Авто</th>
                        <th scope="col" className="num">Истекает</th>
                        <th scope="col" className="col-center">Score</th>
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
      {emailOpen && customer?.emailDraft ? (
        <EmailDraftDialog draft={customer.emailDraft} onClose={() => setEmailOpen(false)} />
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
          <span>{dateTime(service.expiresAt)}</span>
          <small>{expiry}</small>
        </div>
      </td>
      <td className="col-center">
        <span className={`score-chip score-chip--${service.level}`}>{Math.round(service.score)}</span>
      </td>
    </tr>
  );
}


function RuleList({ rules, title }: { rules: RuleExplanation[]; title: string }) {
  if (rules.length === 0) return null;
  return (
    <section aria-label={title}>
      <h3>{title}</h3>
      {rules.map((rule, index) => (
        <p key={`${rule.code}-${rule.serviceId}-${index}`}>
          {rule.label}: {rule.beforeScore.toFixed(1)} → {rule.afterScore.toFixed(1)}
          {" "}({rule.delta > 0 ? "+" : ""}{rule.delta.toFixed(1)} баллов)
        </p>
      ))}
    </section>
  );
}

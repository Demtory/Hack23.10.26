import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../api";
import type { Forecast, ForecastDay } from "../types";
import { money, shortDate } from "./ui";

type Kind = "fact" | "forecast";
type Selection = { date: string; end: string; kind: Kind };

function dayLabel(value: string) {
  return new Date(`${value}T00:00:00Z`).toLocaleDateString("ru-RU", {
    day: "2-digit",
    month: "short",
    timeZone: "UTC",
  });
}

function fullDay(value: string) {
  return new Date(`${value}T00:00:00Z`).toLocaleDateString("ru-RU", {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });
}

function rangeLabel(start: string, end: string) {
  const from = new Date(`${start}T00:00:00Z`);
  const to = new Date(`${end}T00:00:00Z`);
  const day = (value: Date) =>
    value.toLocaleDateString("ru-RU", { day: "numeric", timeZone: "UTC" });
  const dayMonth = (value: Date) =>
    value.toLocaleDateString("ru-RU", { day: "numeric", month: "long", timeZone: "UTC" });
  if (start === end) return fullDay(start);
  return from.getUTCMonth() === to.getUTCMonth()
    ? `${day(from)}–${dayMonth(to)}`
    : `${dayMonth(from)} — ${dayMonth(to)}`;
}

export function ForecastChart({ liveTick }: { liveTick: number }) {
  const [data, setData] = useState<Forecast | null>(null);
  const [selected, setSelected] = useState<Selection | null>(null);
  const [day, setDay] = useState<ForecastDay | null>(null);
  const [dayError, setDayError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    api
      .forecast(7)
      .then((value) => {
        if (active) setData(value);
      })
      .catch(() => {
        if (active) setData(null);
      });
    return () => {
      active = false;
    };
  }, [liveTick]);

  useEffect(() => {
    if (!selected) {
      setDay(null);
      setDayError(null);
      return;
    }
    let active = true;
    setDayError(null);
    setDay(null);
    api
      .forecastDay(selected.date, selected.end, selected.kind)
      .then((value) => {
        if (active) setDay(value);
      })
      .catch((error) => {
        if (active) setDayError(error instanceof ApiError ? error.message : "Не удалось загрузить день");
      });
    return () => {
      active = false;
    };
  }, [selected]);

  const peak = useMemo(() => {
    if (!data) return 1;
    return Math.max(
      1,
      ...data.fact.map((point) => point.services),
      ...data.forecast.map((point) => point.services),
    );
  }, [data]);

  if (!data) return null;

  const height = (value: number) => (value ? `${Math.max(6, (value / peak) * 100)}%` : "0%");
  const isActive = (date: string, kind: Kind) => selected?.date === date && selected?.kind === kind;
  const toggle = (date: string, end: string, kind: Kind) =>
    setSelected((current) =>
      current && current.date === date && current.kind === kind ? null : { date, end, kind },
    );

  return (
    <section className="card forecast" aria-labelledby="forecast-heading">
      <div className="card__heading">
        <div>
          <p className="card__label">ПРОГНОЗ</p>
          <h2 id="forecast-heading">Когда наступает отток</h2>
        </div>
        <span className="card__meta">
          {data.pastDays} дней до и {data.horizonDays} после среза
        </span>
      </div>

      <div className="forecast__legend">
        <span className="forecast__key forecast__key--fact">Факт: срок истёк, услуга не продлена</span>
        <span className="forecast__key forecast__key--forecast">Прогноз: ожидаемые непродления</span>
        <span className="forecast__hint">Высота — число услуг. Нажмите на столбец, чтобы открыть услуги дня</span>
      </div>

      <div className="forecast__scroll">
        <div className="forecast__plot">
          <div className="forecast__grid" aria-hidden="true">
            <span style={{ bottom: "100%" }} />
            <span style={{ bottom: "50%" }} />
            <span style={{ bottom: 0 }} />
          </div>

          <div className="forecast__chart">
            <div className="forecast__half forecast__half--fact" role="group" aria-label="Факт: срок истёк">
              {data.fact.map((point) => (
                <button
                  key={point.date}
                  type="button"
                  className={`forecast__slot ${isActive(point.date, "fact") ? "forecast__slot--active" : ""}`}
                  onClick={() => toggle(point.date, point.end, "fact")}
                  aria-pressed={isActive(point.date, "fact")}
                  aria-label={`${rangeLabel(point.date, point.end)}, факт: ${point.services} услуг, ${point.customers} клиентов`}
                  title={`${rangeLabel(point.date, point.end)} — ${point.services} услуг, ${point.customers} клиентов`}
                >
                  <b className="forecast__value">{point.services || ""}</b>
                  {point.services ? (
                    <span className="forecast__bar forecast__bar--fact" style={{ height: height(point.services) }} />
                  ) : (
                    <span className="forecast__zero" />
                  )}
                </button>
              ))}
            </div>

            <div className="forecast__cut">
              <b>срез</b>
            </div>

            <div className="forecast__half forecast__half--forecast" role="group" aria-label="Прогноз: ожидаемые непродления">
              {data.forecast.map((point) => (
                <button
                  key={point.date}
                  type="button"
                  className={`forecast__slot ${isActive(point.date, "forecast") ? "forecast__slot--active" : ""}`}
                  onClick={() => toggle(point.date, point.end, "forecast")}
                  aria-pressed={isActive(point.date, "forecast")}
                  aria-label={`${rangeLabel(point.date, point.end)}, прогноз: ${point.services} услуг, ожидаемо ${point.expectedNonRenewals} непродлений на ${money(point.expectedLoss)}`}
                  title={`${rangeLabel(point.date, point.end)} — ${point.services} услуг, ожидаемо ${point.expectedNonRenewals}, ${money(point.expectedLoss)}`}
                >
                  <b className="forecast__value">{point.services || ""}</b>
                  {point.services ? (
                    <span className="forecast__bar forecast__bar--forecast" style={{ height: height(point.services) }} />
                  ) : (
                    <span className="forecast__zero" />
                  )}
                </button>
              ))}
            </div>
          </div>

          <div className="forecast__axis">
            {data.fact.map((point, index) => (
              <span key={point.date} style={{ left: `${((index + 0.5) / data.fact.length) * 50}%` }}>
                {dayLabel(point.date)}
              </span>
            ))}
            {data.forecast.map((point, index) => (
              <span key={point.date} style={{ left: `${50 + ((index + 0.5) / data.forecast.length) * 50}%` }}>
                {dayLabel(point.date)}
              </span>
            ))}
          </div>
        </div>
      </div>

      <div className="forecast__totals">
        <div>
          <span>Истекло и не продлено</span>
          <strong>{data.totals.factServices}</strong>
          <small>услуг у {data.totals.factCustomers} клиентов</small>
        </div>
        <div>
          <span>Ожидаемо не продлят</span>
          <strong>{data.totals.expectedNonRenewals}</strong>
          <small>из {data.totals.forecastServices} услуг впереди</small>
        </div>
        <div>
          <span>Ожидаемые потери</span>
          <strong>{money(data.totals.expectedLoss)}</strong>
          <small>за {data.horizonDays} дней</small>
        </div>
      </div>

      {selected ? (
        <div
          className="forecast__panel"
          role="region"
          aria-live="polite"
          aria-label={`Услуги ${rangeLabel(selected.date, selected.end)}`}
        >
          <div className="forecast__panel-head">
            <div>
              <p className="card__label">{selected.kind === "fact" ? "ФАКТ" : "ПРОГНОЗ"}</p>
              <h3>{rangeLabel(selected.date, selected.end)}</h3>
            </div>
            <div className="forecast__panel-meta">
              <span>{day?.services ?? "…"} услуг</span>
              <span>{day?.customers ?? "…"} клиентов</span>
              {selected.kind === "forecast" && day ? <span>{money(day.expectedLoss)} ожидаемо</span> : null}
            </div>
            <button className="button button--ghost" onClick={() => setSelected(null)}>
              Закрыть
            </button>
          </div>

          {dayError ? <p className="form-error">{dayError}</p> : null}
          {!day && !dayError ? <p className="muted">Загружаем услуги…</p> : null}
          {day && day.services === 0 ? <p className="muted">В этот день истечений нет.</p> : null}

          {day && day.services > 0 ? (
            <div className="forecast__rows">
              <div className="forecast__row forecast__row--head" aria-hidden="true">
                <span>Услуга и клиент</span>
                <span className="num">Цена</span>
                <span>Score</span>
                <span className="num">{selected.kind === "forecast" ? "Ожидаемые потери" : "Статус"}</span>
              </div>
              {day.items.map((item) => (
                <Link key={item.serviceId} className="forecast__row" to={`/customers/${item.customerId}`}>
                  <span className="forecast__row-main">
                    <strong>{item.serviceName}</strong>
                    <small>{item.email}</small>
                  </span>
                  <span className="num">{money(item.price)}</span>
                  <span>
                    <span className={`score-chip score-chip--${item.level}`}>{Math.round(item.score)}</span>
                  </span>
                  <span className="num">
                    {item.expectedLoss != null ? money(item.expectedLoss) : item.status}
                  </span>
                </Link>
              ))}
              {day.truncated ? (
                <p className="muted">Показаны первые {day.items.length} услуг из {day.services}.</p>
              ) : null}
            </div>
          ) : null}
        </div>
      ) : null}

      <p className="forecast__note">{data.note}</p>
    </section>
  );
}

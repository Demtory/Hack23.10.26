import { useEffect, useState } from "react";
import { api } from "../api";
import type { Forecast } from "../types";
import { money, shortDate } from "./ui";

export function ForecastChart({ liveTick }: { liveTick: number }) {
  const [data, setData] = useState<Forecast | null>(null);

  useEffect(() => {
    let active = true;
    api
      .forecast()
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

  if (!data) return null;

  const peak = Math.max(
    1,
    ...data.fact.map((point) => point.services),
    ...data.forecast.map((point) => point.services),
  );
  const height = (value: number) => `${value ? Math.max(6, (value / peak) * 100) : 0}%`;

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
      </div>

      <div
        className="forecast__chart"
        role="img"
        aria-label={`Факт истечений: ${data.totals.factServices} услуг за ${data.pastDays} дней. Прогноз: ${data.totals.forecastServices} услуг истекает за ${data.horizonDays} дней, ожидаемо не продлят ${data.totals.expectedNonRenewals}.`}
      >
        <div className="forecast__half">
          {data.fact.map((point) => (
            <span
              key={point.date}
              className="forecast__bar forecast__bar--fact"
              style={{ height: height(point.services) }}
              title={`${point.date}: ${point.services} услуг, ${point.customers} клиентов`}
            />
          ))}
        </div>
        <div className="forecast__divider">
          <span>срез</span>
        </div>
        <div className="forecast__half">
          {data.forecast.map((point) => (
            <span
              key={point.date}
              className="forecast__bar forecast__bar--forecast"
              style={{ height: height(point.services) }}
              title={`${point.date}: ${point.services} услуг, ожидаемо ${point.expectedNonRenewals}, ${money(point.expectedLoss)}`}
            />
          ))}
        </div>
      </div>

      <div className="forecast__axis">
        <span>{shortDate(data.fact[0]?.date)}</span>
        <span>срез {shortDate(data.asOf)}</span>
        <span>{shortDate(data.forecast[data.forecast.length - 1]?.date)}</span>
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

      <p className="forecast__note">{data.note}</p>
    </section>
  );
}

import { useEffect, useMemo, useState } from "react";
import { api, ApiError } from "../api";
import type { ModelSettings, Summary } from "../types";
import { ErrorBox, money, Spinner } from "../components/ui";

const DEFAULTS = {
  thresholds: { medium: 40, high: 70 },
  money: { balanceMitigation: 0.5, includeWithdrawBalance: true },
  statusFloors: { prolong_wait: 70, blocked: 60, stale: 70 },
};

const FEATURE_EXPLANATIONS: Record<string, { guide: string; impact: string }> = {
  expiry_pressure: {
    guide: "Близость expiresAt к дате среза с учётом срока оплаты и доступного баланса.",
    impact: "Вес определяет долю фактора срочности в базовой оценке услуги.",
  },
  funds_gap: {
    guide: "Баланс сравнивается с ценой одной оцениваемой услуги, без распределения между услугами. При нехватке фактор равен 1; иначе max(0, 0.3 × (1 − баланс / (3 × цена))). При нулевой цене фактор неизвестен.",
    impact: "Больший вес усиливает влияние нехватки денег в базовой оценке.",
  },
  autorenew_off: {
    guide: "autoProlong=false даёт 1, true даёт 0. Флаг не доказывает намерение клиента уйти.",
    impact: "Вес определяет влияние отключённого автопродления.",
  },
  status_pressure: {
    guide: "prolong_wait: 1; blocked: 0.9; suspended: 0.7; active: 0. Устаревший статус учитывается отдельно. suspended означает выключенную, но оплачиваемую услугу.",
    impact: "Кроме взвешенного фактора действуют отдельные минимумы по статусам, даже при весе 0.",
  },
  payment_history: {
    guide: "Наличие хотя бы одного not_performed prolong даёт 1, иначе not_performed order даёт 0.6, иначе 0. Без транзакций фактор неизвестен.",
    impact: "Оценивается наличие неоплаты, а не её частота или доля транзакций.",
  },
  commitment: {
    guide: "1 − min(1, totalReplenished / (3 × сумма цен всех услуг аккаунта)). При нулевой сумме цен фактор неизвестен.",
    impact: "Большие пополнения уменьшают этот эвристический фактор; это не доказанная лояльность клиента.",
  },
};

export function Settings({ liveTick }: { liveTick: number }) {
  const [settings, setSettings] = useState<ModelSettings | null>(null);
  const [draft, setDraft] = useState<ModelSettings | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api
      .settings()
      .then((value) => {
        if (cancelled) return;
        setSettings(value);
        setDraft(value);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Не удалось загрузить настройки");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    api
      .summary()
      .then(setSummary)
      .catch(() => undefined);
  }, [liveTick]);

  const weightSum = useMemo(
    () => (draft ? Object.values(draft.weights).reduce((sum, value) => sum + value, 0) : 0),
    [draft],
  );

  function setWeight(code: string, value: number) {
    if (!draft) return;
    setDraft({ ...draft, weights: { ...draft.weights, [code]: value } });
  }

  function reset() {
    if (!settings) return;
    const weights = Object.fromEntries(settings.features.map((feature) => [feature.code, feature.default]));
    setDraft({
      ...settings,
      weights,
      thresholds: { ...DEFAULTS.thresholds },
      money: { ...settings.money, ...DEFAULTS.money },
      statusFloors: { ...DEFAULTS.statusFloors },
    });
    setStatus("Значения сброшены в локальном черновике — нажмите «Сохранить».");
  }

  async function save() {
    if (!draft) return;
    setBusy(true);
    setError(null);
    setStatus(null);
    try {
      const result = await api.updateSettings({
        weights: draft.weights,
        thresholds: draft.thresholds,
        money: draft.money,
        statusFloors: draft.statusFloors,
      });
      setSettings(result.settings);
      setDraft(result.settings);
      setSummary(result.summary);
      setStatus("Модель пересчитана. Настройки сохранены в базе и переживут перезапуск.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось сохранить настройки");
    } finally {
      setBusy(false);
    }
  }

  if (!draft) {
    return (
      <div className="page">
        <header className="page__header">
          <div>
            <p className="eyebrow">МОДЕЛЬ</p>
            <h1>Настройки</h1>
          </div>
        </header>
        {error ? <ErrorBox message={error} /> : <Spinner label="Загружаем коэффициенты" />}
      </div>
    );
  }

  return (
    <div className="page">
      <header className="page__header">
        <div>
          <p className="eyebrow">МОДЕЛЬ · ВЕРСИЯ {draft.version}</p>
          <h1>Настройки риска</h1>
          <p className="page__subtitle">
            Веса нормируются при расчёте: можно ставить 0, чтобы отключить признак. Изменения применяются и сохраняются только после нажатия «Сохранить».
          </p>
        </div>
        <div className="settings-actions">
          <button className="button button--ghost" onClick={reset} disabled={busy}>
            Сбросить
          </button>
          <button className="button button--primary" onClick={save} disabled={busy}>
            {busy ? "Пересчитываем…" : "Сохранить"}
          </button>
        </div>
      </header>

      {error ? <ErrorBox message={error} /> : null}
      {status ? <div className="notice">{status}</div> : null}

      <div className="card" style={{ marginBottom: "1.5rem", borderLeft: "4px solid #6366f1" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
          <div>
            <h3 style={{ margin: "0 0 0.25rem 0", fontSize: "1rem" }}>Как рассчитывается итоговый Risk-Score</h3>
            <p className="muted" style={{ margin: 0, fontSize: "0.875rem" }}>
              Сумма сырых весов: <strong>{weightSum.toFixed(2)}</strong>. Модель производит автоматическую нормировку: доля фактора равна весу, делённому на сумму весов, а вклад учитывает и значение фактора. Сумма 1.00 не обязательна. Неизвестное значение заменяется на 0.5; при недостаточной полноте данных оценка отсутствует.
            </p>
          </div>
          <div style={{ background: "#1f2937", padding: "0.5rem 1rem", borderRadius: "8px", fontFamily: "monospace", fontSize: "0.875rem" }}>
            База услуги = 100 × Σ(вес_i × фактор_i) / Σ(весов)
          </div>
        </div>
      </div>

      <p className="muted">
        После базовой оценки действуют сохранённые минимумы prolong_wait ({draft.statusFloors.prolong_wait}),
        blocked ({draft.statusFloors.blocked}) и устаревшего статуса ({draft.statusFloors.stale}).
        Вес 0 их не отключает. Оценка клиента — максимум оценённых услуг плюс 4 балла за каждую
        дополнительную услугу от среднего порога; итог ограничен 100. Доли весов относятся к базе услуги.
      </p>
      <div className="settings-layout">
        <div className="settings-main">
          <section className="card">
            <div className="card__heading">
              <div>
                <p className="card__label">Коэффициенты</p>
                <h2>Веса признаков</h2>
              </div>
              <span className="card__meta">сумма весов: {weightSum.toFixed(2)} (100% вклад)</span>
            </div>
            <div className="weights">
              {draft.features.map((feature) => {
                const rawVal = draft.weights[feature.code] ?? 0;
                const sharePercent = weightSum > 0 ? ((rawVal / weightSum) * 100).toFixed(1) : "0.0";
                const info = FEATURE_EXPLANATIONS[feature.code] ?? { guide: feature.description, impact: "Влияние задаётся весом и значением этого признака." };
                return (
                  <div className="weight-row" key={feature.code} style={{ paddingBottom: "1.25rem", borderBottom: "1px solid #1f2937" }}>
                    <div className="weight-row__head">
                      <div>
                        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                          <strong>{feature.title}</strong>
                          <span style={{ fontSize: "0.75rem", background: "#374151", color: "#9ca3af", padding: "2px 6px", borderRadius: "4px" }}>
                            доля в модели: {sharePercent}%
                          </span>
                        </div>
                        <p style={{ margin: "0.25rem 0 0.5rem 0", color: "#d1d5db" }}>{feature.description}</p>
                        {info && (
                          <div style={{ fontSize: "0.8rem", color: "#9ca3af", background: "#111827", padding: "0.5rem 0.75rem", borderRadius: "6px", marginTop: "0.25rem" }}>
                            <div>📘 <em>Суть шкалы:</em> {info.guide}</div>
                            <div style={{ marginTop: "0.25rem" }}>⚡ <em>Влияние:</em> {info.impact}</div>
                          </div>
                        )}
                      </div>
                      <span className="weight-row__value">{rawVal.toFixed(2)}</span>
                    </div>
                    <div className="weight-row__controls" style={{ marginTop: "0.75rem" }}>
                      <input
                        type="range"
                        min={feature.min}
                        max={feature.max}
                        step={feature.step}
                        value={rawVal}
                        onChange={(event) => setWeight(feature.code, Number(event.target.value))}
                      />
                      <input
                        className="input input--number"
                        type="number"
                        min={0}
                        max={1}
                        step={0.01}
                        value={rawVal}
                        onChange={(event) => setWeight(feature.code, Number(event.target.value))}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </section>

          <section className="card">
            <div className="card__heading">
              <div>
                <p className="card__label">Пороги</p>
                <h2>Уровни риска</h2>
              </div>
            </div>
            <p className="muted" style={{ marginBottom: "1rem", fontSize: "0.85rem" }}>
              Определяют классификацию клиента: Низкий риск (ниже Среднего), Средний риск (от Среднего до Высокого) и Высокий риск (от порога Высокого).
            </p>
            <div className="thresholds">
              <label className="field field--inline">
                <span>Средний риск от</span>
                <input
                  className="input input--number"
                  type="number"
                  min={1}
                  max={99}
                  value={draft.thresholds.medium}
                  onChange={(event) =>
                    setDraft({ ...draft, thresholds: { ...draft.thresholds, medium: Number(event.target.value) } })
                  }
                />
              </label>
              <label className="field field--inline">
                <span>Высокий риск от</span>
                <input
                  className="input input--number"
                  type="number"
                  min={1}
                  max={100}
                  value={draft.thresholds.high}
                  onChange={(event) =>
                    setDraft({ ...draft, thresholds: { ...draft.thresholds, high: Number(event.target.value) } })
                  }
                />
              </label>
            </div>
          </section>

          <section className="card">
            <div className="card__heading">
              <div>
                <p className="card__label">Деньги</p>
                <h2>Влияние баланса</h2>
              </div>
              <span className="card__meta">{Math.round(draft.money.balanceMitigation * 100)}%</span>
            </div>
            <p className="muted">
              Насколько баланс может снизить ожидаемую потерю. 0% — не учитывать, 100% — вычитать
              покрытие полностью. Мы не рекомендуем 100%: баланс закрывает платёж, но не удерживает
              клиента.
            </p>
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={draft.money.balanceMitigation}
              onChange={(event) =>
                setDraft({
                  ...draft,
                  money: { ...draft.money, balanceMitigation: Number(event.target.value) },
                })
              }
            />
            <div className="range-labels">
              <span>0%</span>
              <span>50%</span>
              <span>100%</span>
            </div>
            <label className="checkbox">
              <input
                type="checkbox"
                checked={draft.money.includeWithdrawBalance}
                onChange={(event) =>
                  setDraft({
                    ...draft,
                    money: { ...draft.money, includeWithdrawBalance: event.target.checked },
                  })
                }
              />
              Учитывать реферальный баланс как доступные деньги
            </label>
          </section>
        </div>

        <aside className="settings-aside">
          <div className="card card--sticky">
            <p className="card__label">Что получится</p>
            <h2>После пересчёта</h2>
            {summary ? (
              <>
                <div className="mini-stat">
                  <span>Ожидаемые потери</span>
                  <strong>{money(summary.expectedLoss)}</strong>
                </div>
                <div className="mini-stat">
                  <span>Высокий риск</span>
                  <strong>{summary.countsByLevel.high}</strong>
                </div>
                <div className="mini-stat">
                  <span>Средний риск</span>
                  <strong>{summary.countsByLevel.medium}</strong>
                </div>
                <div className="mini-stat">
                  <span>Без оценки</span>
                  <strong>{summary.countsByLevel.unknown}</strong>
                </div>
                <div className="mini-stat">
                  <span>Средний score</span>
                  <strong>{summary.avgScore ?? "—"}</strong>
                </div>
              </>
            ) : (
              <Spinner label="Сводка" />
            )}
            <p className="settings-aside__note">
              Сохранение запускает пересчёт на сервере. Черновик до сохранения не влияет на результаты. Панель обновится по SSE или резервному опросу.
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
}

import { useEffect, useMemo, useState } from "react";
import { api, ApiError } from "../api";
import type { ModelSettings, Summary } from "../types";
import { ErrorBox, money, Spinner } from "../components/ui";

const DEFAULTS = {
  thresholds: { medium: 40, high: 70 },
  money: { balanceMitigation: 0.5, includeWithdrawBalance: true },
  statusFloors: { prolong_wait: 70, blocked: 60, stale: 70 },
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

  function share(code: string): string {
    if (!draft || weightSum <= 0) return "0%";
    return `${Math.round(((draft.weights[code] ?? 0) / weightSum) * 100)}%`;
  }

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
            Настройте, что важнее для вашего бизнеса. Веса относительные — сумма не обязана быть
            равна 1, ноль отключает признак.
          </p>
        </div>
        <div className="settings-actions">
          <button className="button button--ghost" onClick={reset} disabled={busy}>
            Сбросить
          </button>
          <button className="button button--primary" onClick={save} disabled={busy || weightSum <= 0}>
            {busy ? "Пересчитываем…" : "Сохранить"}
          </button>
        </div>
      </header>

      {error ? <ErrorBox message={error} /> : null}
      {status ? <div className="notice">{status}</div> : null}

      <div className="settings-layout">
        <div className="settings-main">
          <section className="card card--info">
            <div className="formula-box">
              <span className="formula-box__label">Как считается score</span>
              <code>100 × Σ(w × f) / Σw</code>
            </div>
            <p>
              <b>w</b> — вес признака, <b>f</b> — его значение от 0 до 1. Веса сравниваются
              относительно друг друга: важна пропорция, а не абсолютная сумма. Поставьте 0,
              чтобы полностью отключить признак. Итог ограничен 100 баллами.
            </p>
          </section>

          <section className="card">
            <div className="card__heading">
              <div>
                <p className="card__label">Коэффициенты</p>
                <h2>Веса признаков</h2>
              </div>
              <div className="weight-sum">
                <span>Σ весов</span>
                <strong>{weightSum.toFixed(2)}</strong>
                <small>нормализуется</small>
              </div>
            </div>
            <div className="weights">
              {draft.features.map((feature) => (
                <div className="weight-row" key={feature.code}>
                  <div className="weight-row__head">
                    <div>
                      <strong>{feature.title}</strong>
                      <p>{feature.description}</p>
                    </div>
                    <div className="weight-row__value">
                      <strong>{draft.weights[feature.code]?.toFixed(2) ?? "0.00"}</strong>
                      <small>{share(feature.code)} влияния</small>
                    </div>
                  </div>
                  <p className="weight-row__scale">
                    <span><b>0</b> — {feature.zero}</span>
                    <span><b>1</b> — {feature.one}</span>
                  </p>
                  <div className="weight-row__controls">
                    <input
                      type="range"
                      min={feature.min}
                      max={feature.max}
                      step={feature.step}
                      value={draft.weights[feature.code] ?? 0}
                      onChange={(event) => setWeight(feature.code, Number(event.target.value))}
                    />
                    <input
                      className="input input--number"
                      type="number"
                      min={0}
                      max={1}
                      step={0.01}
                      value={draft.weights[feature.code] ?? 0}
                      onChange={(event) => setWeight(feature.code, Number(event.target.value))}
                    />
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="card">
            <div className="card__heading">
              <div>
                <p className="card__label">Пороги</p>
                <h2>Уровни риска</h2>
              </div>
            </div>
            <p className="muted">
              Пороги не меняют score — они только относят клиента к группе. Ниже 40 — наблюдать,
              40–69 — программа удержания, 70+ — звонить сегодня.
            </p>
            <div className="threshold-map">
              <div className="threshold-map__item threshold-map__item--low">
                <span>0–{Math.round(draft.thresholds.medium)}</span>
                <strong>Низкий</strong>
                <small>{summary?.countsByLevel.low ?? "—"} клиентов</small>
              </div>
              <div className="threshold-map__item threshold-map__item--medium">
                <span>{Math.round(draft.thresholds.medium)}–{Math.round(draft.thresholds.high)}</span>
                <strong>Средний</strong>
                <small>{summary?.countsByLevel.medium ?? "—"} клиентов</small>
              </div>
              <div className="threshold-map__item threshold-map__item--high">
                <span>{Math.round(draft.thresholds.high)}+</span>
                <strong>Высокий</strong>
                <small>{summary?.countsByLevel.high ?? "—"} клиентов</small>
              </div>
            </div>
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
              <span>0% — не учитывать</span>
              <span>50% — рекомендуем</span>
              <span>100% — вычитать полностью</span>
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
              Изменение веса вызывает пересчёт на сервере. Панель обновится по SSE без перезагрузки.
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
}

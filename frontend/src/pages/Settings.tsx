import {CustomFactorEditor} from '../components/CustomFactorEditor';
import {useDraft} from "../state/SettingsDraft";
import {Dialog} from "../components/ui";
import {CalculationContext} from "../components/CalculationContext";
import { useEffect, useMemo, useState } from "react";
import { api, ApiError } from "../api";
import type { ModelSettings, Summary, WeightPreset } from "../types";
import { ErrorBox, money, Spinner } from "../components/ui";

const DEFAULTS = {
  thresholds: { medium: 40, high: 70 },
  money: { balanceMitigation: 0.5, includeWithdrawBalance: true },
  statusFloors: { prolong_wait: 70, blocked: 60, stale: 70 },
};

const FEATURE_EXPLANATIONS: Record<string, { guide: string; impact: string }> = {
  expiry_pressure: {
    guide: "Сколько времени осталось до окончания оплаченного периода. Автопродление снижает срочность, только если на основном и доступном бонусном балансе хватает на платёж.",
    impact: "Настройка определяет долю фактора срочности в базовой оценке услуги.",
  },
  funds_gap: {
    guide: "Баланс сравнивается с ценой одной оцениваемой услуги, без распределения между услугами. При нехватке фактор равен 1; иначе max(0, 0.3 × (1 − баланс / (3 × цена))). При нулевой цене фактор неизвестен.",
    impact: "Большее влияние усиливает влияние нехватки денег в базовой оценке.",
  },
  autorenew_off: {
    guide: "Отключено — 1, включено — 0. Сам по себе этот факт не означает, что клиент собирается уйти.",
    impact: "Настройка определяет влияние отключённого автопродления.",
  },
  status_pressure: {
    guide: "Ожидает оплаты — 1; заблокирована — 0,9; выключена, но оплачивается — 0,7; работает — 0. Если срок уже истёк, а статус не обновлён — 1.",
    impact: "Кроме взвешенного фактора действуют отдельные минимумы по статусам, даже при весе 0.",
  },
  payment_history: {
    guide: "Есть неоплаченное продление — 1; только неоплаченный заказ — 0,6; все счета оплачены — 0. Если платежей нет в данных, значение неизвестно.",
    impact: "Оценивается наличие неоплаты, а не её частота или доля транзакций.",
  },
  commitment: {
    guide: "Чем меньше клиент пополнил относительно стоимости его услуг, тем выше значение. Формула: 1 − min(1, сумма пополнений / (3 × стоимость всех услуг)). При нулевой стоимости значение неизвестно.",
    impact: "Чем больше пополнено, тем ниже значение. Это косвенный показатель, а не доказательство лояльности.",
  },
  auto_off_share: {
    guide: "Доля неудалённых услуг аккаунта без автопродления: 0 — включено везде, 1 — ни у одной услуги. Считается по клиенту, а не по одной услуге.",
    impact: "Влияние 0 отключает фактор; по умолчанию 0, чтобы не менять прежние оценки. Отличается от autorenew_off: тот про конкретную услугу, этот — про привычку клиента.",
  },
};

export function Settings({ liveTick }: { liveTick: number }) {
  const model=useDraft();
  const {settings,draft,setDraft,summary,error,busy}=model;
  const [discardPrompt,setDiscardPrompt]=useState(false);
  const [presets,setPresets]=useState<WeightPreset[]>([]);
  const [presetError,setPresetError]=useState<string|null>(null);
  const [presetStatus,setPresetStatus]=useState<string|null>(null);
  const [saveOpen,setSaveOpen]=useState(false);
  const [presetName,setPresetName]=useState("");
  const [savingPreset,setSavingPreset]=useState(false);
  const [deleteTarget,setDeleteTarget]=useState<WeightPreset|null>(null);
  useEffect(()=>{void model.load();},[liveTick]);
  useEffect(()=>{let active=true;api.presets().then(r=>{if(active)setPresets(r.presets);}).catch(()=>{if(active)setPresetError("Не удалось загрузить готовые наборы");});return()=>{active=false;};},[]);

  function applyPreset(preset: WeightPreset) {
    if (!draft) return;
    setDraft({ ...draft, weights: { ...draft.weights, ...preset.weights } });
    setPresetStatus(`Применён набор «${preset.name}»: настройки в черновике. Нажмите «Сохранить» вверху страницы, чтобы применить.`);
    setPresetError(null);
  }

  async function savePreset() {
    if (!draft || !presetName.trim() || savingPreset) return;
    setSavingPreset(true);
    setPresetError(null);
    try {
      const created = await api.createPreset(presetName.trim(), Object.fromEntries(Object.entries(draft.weights).filter(([code])=>!code.startsWith("custom_"))));
      setPresets((current) => [...current, created]);
      setPresetStatus(`Набор «${created.name}» сохранён.`);
      setSaveOpen(false);
      setPresetName("");
    } catch (error) {
      setPresetError(error instanceof ApiError ? error.message : "Не удалось сохранить набор");
    } finally {
      setSavingPreset(false);
    }
  }

  async function removePreset(preset: WeightPreset) {
    setPresetError(null);
    try {
      await api.deletePreset(preset.id);
      setPresets((current) => current.filter((item) => item.id !== preset.id));
      setPresetStatus(`Набор «${preset.name}» удалён.`);
    } catch (error) {
      setPresetError(error instanceof ApiError ? error.message : "Не удалось удалить набор");
    } finally {
      setDeleteTarget(null);
    }
  }
  const status=model.state==='saved'?'Настройки сохранены. Результаты относятся к применённой версии.':model.state==='conflict'?'Конфликт версий. Черновик сохранён; загрузка текущей модели требует отказа от правок.':model.state==='uncertain'?'Результат операции неизвестен. Черновик сохранён; автоматического повтора нет.':model.dirty?'Несохранённый черновик — результаты ещё не изменены.':null;
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
  }
  async function save(){await model.save();}
  async function saveDraft(){setPresetStatus(null);setPresetError(null);await model.save();}

  if (!draft) {
    return (
      <div className="page">
        <header className="page__header">
          <div>
            <p className="eyebrow">МОДЕЛЬ</p>
            <h1>Настройки</h1>
          </div>
        </header>
        {error ? <ErrorBox message={error} onRetry={()=>void model.load()} /> : <Spinner label="Загружаем настройки" />}
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
            Выберите, какие факторы влияют на риск и насколько сильно. Изменения начнут действовать после сохранения и пересчёта.
          </p>
        </div>
        <div className="settings-actions">
          <button className="button button--ghost" onClick={reset} disabled={busy}>
            Сбросить
          </button>
          <button className="button button--primary" onClick={save} disabled={busy||model.state==="conflict"||(!model.dirty&&model.state!=="uncertain")}>
            {busy ? "Пересчитываем…" : "Сохранить"}
          </button>
        </div>
      </header>

      {error ? <ErrorBox message={error} /> : null}
      {status ? <div className="notice">{status}</div> : null}

      <fieldset disabled={busy} className="settings-fields"><legend className="sr-only">Параметры модели</legend>
      <div className="card">
        <div>
          <div>
            <h3>Как работают настройки</h3>
            <p className="muted">Чем больше влияние фактора относительно остальных, тем сильнее он меняет базовую оценку услуги. Сумму не нужно подгонять к 1. Поставьте 0 или выключите фактор, чтобы исключить его вклад.</p>
            <p className="muted">Это не отключает отдельные правила по статусам и добавку за несколько услуг. Поэтому место клиента в рейтинге может остаться прежним.</p>
            <details><summary>Формула и неизвестные значения</summary><p>База услуги = 100 × сумма (влияние × значение фактора) / сумма влияний. Значение фактора — от 0 до 1. Неизвестное значение учитывается как 0,5; если известных данных меньше половины по влиянию, оценка не показывается.</p></details>
          </div>
          <div>

          </div>
        </div>
      </div>



      <p className="muted">
        Отдельные правила: услуга ожидает оплаты — минимум {draft.statusFloors.prolong_wait} баллов;
        заблокирована — {draft.statusFloors.blocked}; статус не соответствует сроку — {draft.statusFloors.stale}.
        Для клиента берётся самая высокая оценка услуги. За каждую дополнительную услугу со средним или высоким риском добавляется 4 балла, максимум — 100.
      </p>
      {model.state==='conflict'||model.state==='uncertain'?<button className="button" onClick={()=>setDiscardPrompt(true)}>Загрузить текущую версию</button>:null}
      <div className="settings-layout">
        <div className="settings-main">
          <section className="card">
            <div className="card__heading">
              <div>
                <p className="card__label">Готовые настройки</p>
                <h2>Готовые наборы влияния</h2>
              </div>
              <button className="button" onClick={()=>setSaveOpen(true)} disabled={!draft}>Сохранить как новый набор</button>
            </div>
            <p className="muted">
              Набор меняет влияние встроенных факторов. Собственные факторы сохраняются. Он заполняет черновик — результаты пересчитаются
              после «Сохранить». Пороги, минимумы и денежные правила остаются как есть.
            </p>
            <div className="presets">
              {presets.map((preset) => (
                <div className="preset" key={preset.id}>
                  <button className="preset__apply" onClick={()=>applyPreset(preset)}>
                    <strong>{preset.name}</strong>
                    <small>{preset.description}</small>
                  </button>
                  {!preset.builtin ? (
                    <button className="preset__delete" aria-label={`Удалить набор ${preset.name}`} onClick={()=>setDeleteTarget(preset)}>×</button>
                  ) : null}
                </div>
              ))}
            </div>
            {presetStatus ? (
              <div className="preset__status-row">
                <p className="preset__status" role="status">{presetStatus}</p>

              </div>
            ) : null}
            {presetError ? <p className="form-error">{presetError}</p> : null}
          </section>

          <CustomFactorEditor draft={draft} onChange={setDraft}/>
          <section className="card">
            <div className="card__heading">
              <div>
                <p className="card__label">Настройка влияния</p>
                <h2>Факторы риска</h2>
              </div>
              <span className="card__meta">Доли рассчитываются автоматически</span>
            </div>
            <div className="weights">
              {draft.features.map((feature) => {
                const rawVal = draft.weights[feature.code] ?? 0;
                const sharePercent = weightSum > 0 ? ((rawVal / weightSum) * 100).toFixed(1) : "0.0";
                const info = FEATURE_EXPLANATIONS[feature.code] ?? { guide: feature.description, impact: "Влияние задаётся весом и значением этого признака." };
                return (
                  <div className="weight-row" key={feature.code}>
                    <div className="weight-row__head">
                      <div>
                        <div className="weight-row__title">
                          <strong>{feature.title}</strong>
                          <span>доля в базовой оценке: {sharePercent}%</span>
                        </div>
                        <p>{feature.description}</p>
                        {info && (
                          <details>
                            <summary>Как оценивается фактор</summary>
                            <div><em>Правило:</em> {info.guide}</div>
                            <div><em>Влияние:</em> {info.impact}</div>
                          </details>
                        )}
                      </div>
                      <span className="weight-row__value">{rawVal.toFixed(2)}</span>
                    </div>
                    <label className="checkbox"><input type="checkbox" aria-label={`Включить: ${feature.title}`} checked={rawVal>0} onChange={e=>setWeight(feature.code,e.target.checked?(feature.default||.1):0)}/> {rawVal>0?'Включён':'Выключен · не влияет на базовую оценку'}</label>
                    <div className="weight-row__controls">
                      <input
                        type="range"
                        aria-label={`Шкала: ${feature.title}`}
                        min={feature.min}
                        max={feature.max}
                        step={feature.step}
                        value={rawVal}
                        onChange={(event) => setWeight(feature.code, Number(event.target.value))}
                      />
                      <input
                        className="input input--number"
                        type="number"
                        aria-label={`Вес: ${feature.title}`}
                        min={0}
                        max={feature.max}
                        step={feature.step}
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
            <p className="muted">
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
              aria-label="Снижение денежной оценки балансом"
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
              Учитывать реферальный баланс в денежной оценке (для оплаты потребуется ручной перевод)
            </label>
          </section>
        </div>

        <aside className="settings-aside">
          <div className="card card--sticky">
            <p className="card__label">Что получится</p>
            <h2>Применённая модель</h2>
            <p>Версия {settings?.version} · не предварительный расчёт черновика</p>
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
                  <span>Средняя оценка риска</span>
                  <strong>{summary.avgScore ?? "—"}</strong>
                </div>
              </>
            ) : (
              <Spinner label="Сводка" />
            )}
            <p className="settings-aside__note">
              После сохранения оценки пересчитаются. Пока вы редактируете черновик, в панели остаются прежние результаты.
            </p>
          </div>
        </aside>
      </div>
      </fieldset>
      <CalculationContext asOf={summary?.asOf} updatedAt={summary?.updatedAt}/>
      {saveOpen ? (
        <Dialog title="Сохранить набор влияния" onCancel={()=>{setSaveOpen(false);setPresetName("");}}>
          <p>Сохранятся настройки влияния встроенных факторов. Собственные правила, пороги и денежные настройки в набор не входят.</p>
          <label className="field">
            <span>Название набора</span>
            <input value={presetName} maxLength={40} autoFocus onChange={(event)=>setPresetName(event.target.value)} placeholder="Например, «Кампания по пополнениям»" />
          </label>
          <div className="dialog-actions">
            <button className="button button--primary" disabled={savingPreset||!presetName.trim()} onClick={()=>void savePreset()}>{savingPreset?"Сохраняем…":"Сохранить набор"}</button>
            <button className="button" onClick={()=>{setSaveOpen(false);setPresetName("");}}>Отмена</button>
          </div>
        </Dialog>
      ) : null}
      {deleteTarget ? (
        <Dialog title={`Удалить набор «${deleteTarget.name}»?`} onCancel={()=>setDeleteTarget(null)}>
          <p>Набор исчезнет из списка. Настройки модели и черновик не изменятся.</p>
          <div className="dialog-actions">
            <button className="button" autoFocus onClick={()=>setDeleteTarget(null)}>Оставить</button>
            <button className="button" onClick={()=>void removePreset(deleteTarget)}>Удалить</button>
          </div>
        </Dialog>
      ) : null}
      {discardPrompt&&<Dialog title="Отказаться от черновика?" onCancel={()=>setDiscardPrompt(false)}><p>Локальные изменения будут заменены текущими настройками.</p><button className="button button--primary" autoFocus onClick={()=>setDiscardPrompt(false)}>Остаться</button><button className="button" onClick={()=>{setDiscardPrompt(false);void model.load(true);}}>Отказаться и загрузить</button></Dialog>}
    </div>
  );
}

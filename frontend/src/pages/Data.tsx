import {CalculationContext} from "../components/CalculationContext";
import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "../api";
import type { Snapshot, Summary } from "../types";
import { dateTime, ErrorBox, money, Spinner } from "../components/ui";

export function Data({ liveTick, onSnapshotUploaded }: { liveTick: number; onSnapshotUploaded?: () => void }) {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [context,setContext]=useState<{asOf:string|null;updatedAt:string|null}|null>(null);
  const [retry,setRetry]=useState(0);
  const [snapshotText, setSnapshotText] = useState<string | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.sourceView(), api.summary()])
      .then(([source, currentSummary]) => {
        if (cancelled) return;
        setSnapshot(JSON.parse(source.text) as Snapshot);
        setSnapshotText(source.text);
        setContext(source);
        setSummary(source.runId===currentSummary.calculation?.runId?currentSummary:null);
        setError(null);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Не удалось загрузить снимок");
      });
    return () => {
      cancelled = true;
    };
  }, [liveTick,retry]);

  async function upload(file: File) {
    setBusy(true);
    setError(null);
    setStatus(null);
    try {
      const text = await file.text();
      const parsed = JSON.parse(text) as Snapshot;
      if (!Array.isArray(parsed.accounts) || !Array.isArray(parsed.services) || !Array.isArray(parsed.transactions)) {
        throw new Error("Ожидается объект с массивами accounts, services, transactions");
      }
      const result = await api.replaceSourceText(text);
      setSummary(result.summary);
      setSnapshot(parsed);
      setSnapshotText(null);
      try {
        const saved = await api.sourceView();
        setSnapshot(JSON.parse(saved.text) as Snapshot);
        setSnapshotText(saved.text);
        setContext(saved);
        if(saved.runId!==result.summary.calculation?.runId)setSummary(null);
      } catch {
        setError("Снимок сохранён, но не удалось прочитать текущий JSON. Обновите страницу перед скачиванием.");
      }
      onSnapshotUploaded?.();
      setStatus(
        `Снимок заменён: ${result.counts.accounts} аккаунтов, ${result.counts.services} услуг, ${result.counts.transactions} транзакций. Модель пересчитана.`,
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : err instanceof Error ? "Результат загрузки неизвестен: ответ не получен. Повторно прочитайте текущие данные перед новой загрузкой." : "Ошибка загрузки");
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  function download() {
    if (!snapshotText) return;
    const blob = new Blob([snapshotText], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "snapshot.json";
    anchor.click();
    URL.revokeObjectURL(url);
  }

  const counts = snapshot
    ? { accounts: snapshot.accounts.length, services: snapshot.services.length, transactions: snapshot.transactions.length }
    : null;

  return (
    <div className="page">
      <header className="page__header">
        <div>
          <p className="eyebrow">ИСТОЧНИК ДАННЫХ</p>
          <h1>Снимок</h1>
          <p className="page__subtitle">
            Полная замена данных через API. Формат — как у исходного <code>data.json</code>.
            После загрузки модель пересчитывается автоматически.
          </p>
        </div>
        <button className="button button--ghost" onClick={download} disabled={!snapshotText}>
          Скачать текущий JSON
        </button>
      </header>

      {error ? <ErrorBox message={error} onRetry={()=>setRetry(x=>x+1)}/> : null}
      {status ? <div className="notice">{status}</div> : null}

      <CalculationContext asOf={context?.asOf} updatedAt={context?.updatedAt}/>
      <div className="data-grid">
        <section className="card">
          <div className="card__heading">
            <div>
              <p className="card__label">Сейчас в системе</p>
              <h2>Активный снимок</h2>
            </div>
            {summary ? <span className="card__meta">{dateTime(summary.asOf)}</span> : null}
          </div>
          {counts ? (
            <div className="count-grid">
              <div>
                <strong>{counts.accounts}</strong>
                <span>аккаунтов</span>
              </div>
              <div>
                <strong>{counts.services}</strong>
                <span>услуг</span>
              </div>
              <div>
                <strong>{counts.transactions}</strong>
                <span>транзакций</span>
              </div>
            </div>
          ) : (
            <Spinner label="Читаем снимок" />
          )}
          {summary ? (
            <dl className="facts facts--compact">
              <div>
                <dt>Ожидаемые потери</dt>
                <dd>{money(summary.expectedLoss)}</dd>
              </div>
              <div>
                <dt>Высокий риск</dt>
                <dd>{summary.countsByLevel.high}</dd>
              </div>
              <div>
                <dt>Средний риск</dt>
                <dd>{summary.countsByLevel.medium}</dd>
              </div>
            </dl>
          ) : null}
        </section>

        <section className="card">
          <div className="card__heading">
            <div>
              <p className="card__label">ПОЛНАЯ ЗАМЕНА</p>
              <h2>Загрузить новый снимок</h2>
            </div>
          </div>
          <label
            className={`dropzone ${busy ? "dropzone--busy" : ""}`}
            onDragOver={(event) => event.preventDefault()}
            onDrop={(event) => {
              event.preventDefault();
              if (busy) return;
              const file = event.dataTransfer.files?.[0];
              if (file) void upload(file);
            }}
          >
            <input
              ref={inputRef}
              type="file"
              accept="application/json,.json"
              disabled={busy}
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) void upload(file);
              }}
            />
            <span className="dropzone__icon" aria-hidden="true">↑</span>
            <strong>{busy ? "Заменяем и пересчитываем…" : "Выберите JSON-файл"}</strong>
            <span>или перетащите его сюда. Данные заменяются целиком.</span>
          </label>
          <p className="muted">
            Валидация проверит связи, даты, статусы и денежные поля. При ошибке текущий снимок
            останется нетронутым.
          </p>
        </section>
      </div>
    </div>
  );
}

import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "../api";
import type { Snapshot, Summary } from "../types";
import { dateTime, ErrorBox, money, Spinner } from "../components/ui";

export function Data({ liveTick }: { liveTick: number }) {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.source(), api.summary()])
      .then(([source, currentSummary]) => {
        if (cancelled) return;
        setSnapshot(source);
        setSummary(currentSummary);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Не удалось загрузить снимок");
      });
    return () => {
      cancelled = true;
    };
  }, [liveTick]);

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
      const result = await api.replaceSource(parsed);
      setSummary(result.summary);
      setSnapshot(parsed);
      setStatus(
        `Снимок заменён: ${result.counts.accounts} аккаунтов, ${result.counts.services} услуг, ${result.counts.transactions} транзакций. Модель пересчитана.`,
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : err instanceof Error ? err.message : "Ошибка загрузки");
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  function download() {
    if (!snapshot) return;
    const blob = new Blob([JSON.stringify(snapshot, null, 2)], { type: "application/json" });
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
        <button className="button button--ghost" onClick={download} disabled={!snapshot}>
          Скачать текущий JSON
        </button>
      </header>

      {error ? <ErrorBox message={error} /> : null}
      {status ? <div className="notice">{status}</div> : null}

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
              <p className="card__label">PUT /api/v1/source/snapshot</p>
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
            <span className="dropzone__icon">↑</span>
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

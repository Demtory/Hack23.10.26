import { useEffect, useMemo, useState } from "react";
import type { CSSProperties } from "react";
import { api, ApiError } from "../api";
import type { CustomerListItem, Level, Summary } from "../types";
import { DataStatus, EmptyState, ErrorBox, LevelBadge, money, number, servicesWord, Spinner } from "../components/ui";

type SortKey = "id" | "email" | "balance" | "totalReplenished" | "score" | "expectedLoss";

const COLUMNS: { key: SortKey; label: string; className?: string }[] = [
  { key: "id", label: "ID", className: "col-id" },
  { key: "email", label: "Клиент" },
  { key: "balance", label: "Баланс", className: "num" },
  { key: "totalReplenished", label: "Пополнения", className: "num" },
  { key: "score", label: "Score", className: "num" },
  { key: "expectedLoss", label: "Потери", className: "num" },
];

const LEVELS: { key: Level | ""; label: string }[] = [
  { key: "", label: "Все" },
  { key: "high", label: "Высокий" },
  { key: "medium", label: "Средний" },
  { key: "low", label: "Низкий" },
  { key: "unknown", label: "Без оценки" },
];

export function Dashboard({ onSelect, liveTick }: { onSelect: (id: number) => void; liveTick: number }) {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [items, setItems] = useState<CustomerListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sort, setSort] = useState<SortKey>("score");
  const [order, setOrder] = useState<"asc" | "desc">("desc");
  const [level, setLevel] = useState<Level | "">("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const pageSize = 10;

  useEffect(() => {
    let cancelled = false;
    api
      .summary()
      .then((value) => {
        if (!cancelled) setSummary(value);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [liveTick]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    api
      .customers({ sort, order, level, q: query, page, pageSize })
      .then((value) => {
        if (cancelled) return;
        setItems(value.items);
        setTotal(value.total);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Не удалось загрузить клиентов");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [sort, order, level, query, page, liveTick]);

  useEffect(() => {
    setPage(1);
  }, [level, query, sort, order]);

  const maxLoss = useMemo(
    () => Math.max(0, ...items.map((item) => item.expectedLoss)),
    [items],
  );
  const topLosses = useMemo(
    () => [...items].sort((a, b) => b.expectedLoss - a.expectedLoss).slice(0, 5),
    [items],
  );
  const counts = summary?.countsByLevel;
  const totalCount = counts ? counts.high + counts.medium + counts.low + counts.unknown : 0;

  function toggleSort(key: SortKey) {
    if (key === sort) {
      setOrder((value) => (value === "desc" ? "asc" : "desc"));
      return;
    }
    setSort(key);
    setOrder(key === "score" || key === "expectedLoss" ? "desc" : "asc");
  }

  const pages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="page">
      <header className="page__header">
        <div>
          <p className="eyebrow">ОБЗОР · RETENTION</p>
          <h1>Кому звонить сегодня</h1>
          <p className="page__subtitle">
            Риск оттока, причина и деньги, которые можно потерять при ближайшем продлении.
          </p>
          {summary ? (
            <DataStatus
              asOf={summary.asOf}
              sourceUpdatedAt={summary.sourceUpdatedAt}
              updatedAt={summary.updatedAt}
            />
          ) : null}
        </div>
        <div className="live-indicator" title="Обновляется автоматически">
          <span className="live-indicator__dot" />
          Живые данные
        </div>
      </header>

      {error ? <ErrorBox message={error} /> : null}

      <section className="summary-grid">
        <article className="card card--hero">
          <p className="card__label">Ожидаемые потери</p>
          <p className="card__value">{summary ? money(summary.expectedLoss) : "—"}</p>
          <p className="card__hint">вероятность × ближайший платёж, с учётом баланса</p>
        </article>
        <article className="card">
          <p className="card__label">Платежи под риском</p>
          <p className="card__value">{summary ? money(summary.amountAtRisk) : "—"}</p>
          <p className="card__hint">услуги, у которых score ≥ 40</p>
        </article>
        <article className="card">
          <p className="card__label">Высокий риск</p>
          <p className="card__value">{counts ? counts.high : "—"}</p>
          <p className="card__hint">из {summary?.scoredCustomers ?? "—"} клиентов с оценкой</p>
        </article>
        <article className="card">
          <p className="card__label">Покрытие балансами</p>
          <p className="card__value">{summary ? `${Math.round(summary.coverage * 100)}%` : "—"}</p>
          <p className="card__hint">
            без запаса: {summary?.underfundedCustomers ?? "—"} · средний score{" "}
            {summary ? number(summary.avgScore) : "—"}
          </p>
        </article>
      </section>

      <section className="dashboard-grid">
        <article className="card card--chart">
          <div className="card__heading">
            <div>
              <p className="card__label">Распределение</p>
              <h2>Уровни риска</h2>
            </div>
          </div>
          <div className="donut-wrap">
            <div className={`donut ${totalCount === 0 ? "donut--empty" : ""}`} style={donutStyle(counts)}>
              <div className="donut__hole">
                <strong>{summary?.totalCustomers ?? "—"}</strong>
                <span>клиентов</span>
              </div>
            </div>
            <div className="legend">
              {counts
                ? (Object.entries(counts) as [Level, number][]).map(([key, value]) => (
                    <div className="legend__row" key={key}>
                      <span className={`legend__dot legend__dot--${key}`} />
                      <span className="legend__label">
                        {key === "high" ? "Высокий" : key === "medium" ? "Средний" : key === "low" ? "Низкий" : "Без оценки"}
                      </span>
                      <strong>{value}</strong>
                    </div>
                  ))
                : null}
            </div>
          </div>
        </article>

        <article className="card card--chart">
          <div className="card__heading">
            <div>
              <p className="card__label">Деньги</p>
              <h2>Кто даёт потери</h2>
            </div>
            <span className="card__meta">топ-5</span>
          </div>
          <div className="bars">
            {topLosses.length === 0 ? <p className="muted">Нет данных</p> : null}
            {topLosses.map((item) => (
              <button className="bar-row" key={item.id} onClick={() => onSelect(item.id)}>
                <span className="bar-row__label">{item.email.split("@")[0]}</span>
                <span className="bar-row__track">
                  <span
                    className={`bar-row__fill bar-row__fill--${item.level}`}
                    style={{ width: `${maxLoss ? Math.max(4, (item.expectedLoss / maxLoss) * 100) : 0}%` }}
                  />
                </span>
                <span className="bar-row__value">{money(item.expectedLoss)}</span>
              </button>
            ))}
          </div>
        </article>
      </section>

      <section className="card card--table">
        <div className="table-toolbar">
          <div>
            <p className="card__label">Рейтинг</p>
            <h2>Клиенты под риском</h2>
          </div>
          <div className="table-toolbar__controls">
            <input
              className="input input--search"
              type="search"
              placeholder="Поиск по email"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
            <div className="chips">
              {LEVELS.map((item) => (
                <button
                  key={item.key}
                  className={`chip ${level === item.key ? "chip--active" : ""}`}
                  onClick={() => setLevel(item.key)}
                >
                  {item.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {loading ? (
          <Spinner label="Считаем рейтинг" />
        ) : items.length === 0 ? (
          <EmptyState title="Ничего не найдено" text="Смените фильтр или поисковый запрос." />
        ) : (
          <div className="table-wrap table-wrap--clients">
            <table className="table">
              <thead>
                <tr>
                  {COLUMNS.map((column) => (
                    <th
                      key={column.key}
                      className={column.className}
                      aria-sort={sort === column.key ? (order === "desc" ? "descending" : "ascending") : "none"}
                    >
                      <button className="sort-button" onClick={() => toggleSort(column.key)}>
                        {column.label}
                        <span className={`sort-arrow ${sort === column.key ? "sort-arrow--active" : ""}`}>
                          {sort === column.key ? (order === "desc" ? "↓" : "↑") : "↕"}
                        </span>
                      </button>
                    </th>
                  ))}
                  <th className="num">Уровень</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr
                    key={item.id}
                    className="table__row"
                    tabIndex={0}
                    onClick={() => onSelect(item.id)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") onSelect(item.id);
                    }}
                  >
                    <td className="col-id">{item.id}</td>
                    <td>
                      <div className="client-cell">
                        <span className="client-cell__email">{item.email}</span>
                        <span className="client-cell__meta">{servicesWord(item.servicesAtRisk)} под риском</span>
                      </div>
                    </td>
                    <td className="num">{money(item.balance)}</td>
                    <td className="num">{money(item.totalReplenished)}</td>
                    <td className="num">
                      <div className="score-cell">
                        <strong>{item.score === null ? "—" : Math.round(item.score)}</strong>
                        <span className="score-cell__track">
                          <span
                            className={`score-cell__fill score-cell__fill--${item.level}`}
                            style={{ width: `${item.score ?? 0}%` }}
                          />
                        </span>
                      </div>
                    </td>
                    <td className="num">{money(item.expectedLoss)}</td>
                    <td className="num">
                      <LevelBadge level={item.level} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="mobile-clients">
          {items.map((item) => (
            <button className="mobile-client" key={item.id} onClick={() => onSelect(item.id)}>
              <div className="mobile-client__head">
                <span className="mobile-client__email">{item.email}</span>
                <LevelBadge level={item.level} />
              </div>
              <div className="mobile-client__meta">
                <span>Score {item.score === null ? "—" : Math.round(item.score)}</span>
                <span>{servicesWord(item.servicesAtRisk)} под риском</span>
                <span>{money(item.expectedLoss)}</span>
              </div>
            </button>
          ))}
        </div>

        <div className="pagination">
          <span className="muted">
            {total} клиентов · страница {page} из {pages}
          </span>
          <div className="pagination__buttons">
            <button className="button button--ghost" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>
              Назад
            </button>
            <button
              className="button button--ghost"
              disabled={page >= pages}
              onClick={() => setPage((value) => value + 1)}
            >
              Вперёд
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}

function donutStyle(counts: Summary["countsByLevel"] | undefined): CSSProperties {
  if (!counts) return {};
  const total = counts.high + counts.medium + counts.low + counts.unknown;
  if (!total) return {};
  const high = (counts.high / total) * 100;
  const medium = high + (counts.medium / total) * 100;
  const low = medium + (counts.low / total) * 100;
  return {
    background: `conic-gradient(var(--high) 0 ${high}%, var(--medium) ${high}% ${medium}%, var(--low) ${medium}% ${low}%, var(--unknown) ${low}% 100%)`,
  };
}

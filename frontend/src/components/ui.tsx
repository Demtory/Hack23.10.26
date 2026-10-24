import type { Level } from "../types";

export type IconName =
  | "overview"
  | "users"
  | "sliders"
  | "database"
  | "logout"
  | "refresh"
  | "alert"
  | "check"
  | "search"
  | "arrow-left"
  | "chevron-down"
  | "spark";

export function Brand({ dark = false }: { dark?: boolean }) {
  return (
    <span className={`brand ${dark ? "brand--light" : ""}`}>
      <svg className="brand__mark" viewBox="0 0 32 32" aria-hidden="true">
        <circle cx="16" cy="16" r="14" fill="currentColor" />
        <path d="M10 16a6 6 0 0 1 12 0" fill="none" stroke="#fffaf1" strokeWidth="2.4" strokeLinecap="round" />
        <circle cx="16" cy="22" r="1.7" fill="#fffaf1" />
      </svg>
      <span className="brand__text">
        ОТТОК
        <small>RISK DESK</small>
      </span>
    </span>
  );
}

export function Icon({ name, size = 18 }: { name: IconName; size?: number }) {
  const props = {
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
  };
  switch (name) {
    case "overview":
      return (
        <svg {...props}>
          <rect x="3" y="3" width="7" height="7" rx="1.5" />
          <rect x="14" y="3" width="7" height="7" rx="1.5" />
          <rect x="3" y="14" width="7" height="7" rx="1.5" />
          <rect x="14" y="14" width="7" height="7" rx="1.5" />
        </svg>
      );
    case "users":
      return (
        <svg {...props}>
          <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
          <circle cx="9" cy="7" r="4" />
          <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
          <path d="M16 3.13a4 4 0 0 1 0 7.75" />
        </svg>
      );
    case "sliders":
      return (
        <svg {...props}>
          <line x1="4" y1="21" x2="4" y2="14" />
          <line x1="4" y1="10" x2="4" y2="3" />
          <line x1="12" y1="21" x2="12" y2="12" />
          <line x1="12" y1="8" x2="12" y2="3" />
          <line x1="20" y1="21" x2="20" y2="16" />
          <line x1="20" y1="12" x2="20" y2="3" />
          <line x1="1" y1="14" x2="7" y2="14" />
          <line x1="9" y1="8" x2="15" y2="8" />
          <line x1="17" y1="16" x2="23" y2="16" />
        </svg>
      );
    case "database":
      return (
        <svg {...props}>
          <ellipse cx="12" cy="5" rx="9" ry="3" />
          <path d="M3 5v14a9 3 0 0 0 18 0V5" />
          <path d="M3 12a9 3 0 0 0 18 0" />
        </svg>
      );
    case "logout":
      return (
        <svg {...props}>
          <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
          <polyline points="16 17 21 12 16 7" />
          <line x1="21" y1="12" x2="9" y2="12" />
        </svg>
      );
    case "refresh":
      return (
        <svg {...props}>
          <path d="M21 12a9 9 0 1 1-3-6.7" />
          <polyline points="21 3 21 9 15 9" />
        </svg>
      );
    case "alert":
      return (
        <svg {...props}>
          <path d="m10.3 3.9-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.7-3.1l-8-14a2 2 0 0 0-3.4 0Z" />
          <line x1="12" y1="9" x2="12" y2="13" />
          <line x1="12" y1="17" x2="12.01" y2="17" />
        </svg>
      );
    case "check":
      return (
        <svg {...props}>
          <circle cx="12" cy="12" r="9" />
          <path d="m8 12 3 3 5-6" />
        </svg>
      );
    case "search":
      return (
        <svg {...props}>
          <circle cx="11" cy="11" r="7" />
          <line x1="21" y1="21" x2="16.2" y2="16.2" />
        </svg>
      );
    case "arrow-left":
      return (
        <svg {...props}>
          <line x1="19" y1="12" x2="5" y2="12" />
          <polyline points="12 19 5 12 12 5" />
        </svg>
      );
    case "chevron-down":
      return (
        <svg {...props}>
          <polyline points="6 9 12 15 18 9" />
        </svg>
      );
    default:
      return (
        <svg {...props}>
          <path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1" />
          <circle cx="12" cy="12" r="4" />
        </svg>
      );
  }
}


const LEVEL_LABEL: Record<Level, string> = {
  high: "Высокий",
  medium: "Средний",
  low: "Низкий",
  unknown: "Нет оценки",
};

const STATUS_LABEL: Record<string, string> = {
  active: "Активна",
  suspended: "Выключена",
  prolong_wait: "Ждёт оплаты",
  blocked: "Заблокирована",
  deleted: "Удалена",
};

const TERM_LABEL: Record<string, string> = {
  hour: "час",
  week: "неделя",
  month: "месяц",
  quarter_year: "квартал",
  half_year: "полгода",
  year: "год",
};

export function LevelBadge({ level }: { level: Level }) {
  return <span className={`badge badge--${level}`}>{LEVEL_LABEL[level]}</span>;
}

export function StatusBadge({ status }: { status: string }) {
  return <span className={`status status--${status}`}>{STATUS_LABEL[status] ?? status}</span>;
}

export function plural(count: number, one: string, few: string, many: string): string {
  const value = Math.abs(count) % 100;
  const last = value % 10;
  if (value > 10 && value < 20) return many;
  if (last === 1) return one;
  if (last >= 2 && last <= 4) return few;
  return many;
}

export function servicesWord(count: number): string {
  return `${count} ${plural(count, "услуга", "услуги", "услуг")}`;
}

export function termLabel(term: string): string {
  return TERM_LABEL[term] ?? term;
}

export function money(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat("ru-RU", {
    style: "currency",
    currency: "EUR",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

export function number(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 1 }).format(value);
}

export function shortDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function dateTime(value: string | null | undefined): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function shortDate(value: string | null | undefined): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat("ru-RU", { day: "2-digit", month: "short", year: "numeric" }).format(
    new Date(value),
  );
}

export function Spinner({ label = "Загрузка" }: { label?: string }) {
  return (
    <div className="spinner" role="status">
      <span className="spinner__dot" />
      <span>{label}…</span>
    </div>
  );
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="error-box" role="alert">
      <div>
        <strong>Не получилось.</strong> {message}
      </div>
      {onRetry ? (
        <button className="button button--ghost" onClick={onRetry}>
          Повторить
        </button>
      ) : null}
    </div>
  );
}

export function EmptyState({ title, text }: { title: string; text: string }) {
  return (
    <div className="empty-state">
      <div className="empty-state__mark">∅</div>
      <h3>{title}</h3>
      <p>{text}</p>
    </div>
  );
}


export function DataStatus({
  asOf,
  sourceUpdatedAt,
  updatedAt,
}: {
  asOf: string;
  sourceUpdatedAt: string;
  updatedAt: string;
}) {
  return (
    <div className="data-status" aria-label="Статус данных">
      <span className="data-status__item">
        <span className="data-status__dot" />
        Данные на {shortDateTime(asOf)}
      </span>
      <span className="data-status__sep">·</span>
      <span className="data-status__item">Загружено {shortDateTime(sourceUpdatedAt)}</span>
      <span className="data-status__sep">·</span>
      <span className="data-status__item">Пересчитано {shortDateTime(updatedAt)}</span>
    </div>
  );
}

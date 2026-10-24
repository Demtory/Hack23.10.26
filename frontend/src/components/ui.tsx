import {useRef,useEffect} from "react";
import type { Level } from "../types";

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

export function clientsWord(count: number): string {
  return `${count} ${plural(count, "клиент", "клиента", "клиентов")}`;
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

export function dateTime(value: string | null | undefined): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZoneName: "short",
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

export function Dialog({title,children,onCancel}:{title:string;children:React.ReactNode;onCancel:()=>void}){
 const ref=useRef<HTMLDialogElement>(null);
 useEffect(()=>{const previous=document.activeElement as HTMLElement|null;ref.current?.showModal();return()=>{ref.current?.close();previous?.focus();};},[]);
 return <dialog ref={ref} aria-label={title} onCancel={e=>{e.preventDefault();onCancel();}}><h2>{title}</h2>{children}</dialog>;
}

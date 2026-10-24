import{dateTime}from'./ui';
export function CalculationContext({asOf,updatedAt}:{asOf?:string|null;updatedAt?:string|null}){return <div className="calculation-context"><span>Дата исходных данных неизвестна</span><span>Срез расчёта: <strong>{dateTime(asOf)}</strong></span><span>Рассчитано: <strong>{dateTime(updatedAt)}</strong></span></div>;}

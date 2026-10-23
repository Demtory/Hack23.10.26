import { FormEvent, useState } from "react";
import { api, ApiError } from "../api";
import type { User } from "../types";

export function Login({ onLogin }: { onLogin: (user: User) => void }) {
  const [email, setEmail] = useState("admin@example.test");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const user = await api.login(email, password);
      onLogin(user);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Сервис недоступен");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login">
      <div className="login__aside">
        <div className="brand brand--light">
          <span className="brand__mark">◒</span>
          <span className="brand__text">
            ОТТОК
            <small>RISK DESK</small>
          </span>
        </div>
        <div className="login__pitch">
          <p className="eyebrow">ХАКАТОН РНД · MIDDLE</p>
          <h1>Кому звонить сегодня — и сколько это стоит.</h1>
          <p>
            Один экран для маркетолога: риск оттока, причина и деньги, которые можно потерять
            при ближайшем продлении.
          </p>
          <div className="login__facts">
            <div>
              <strong>3</strong>
              <span>вопроса: кому, почему, сколько</span>
            </div>
            <div>
              <strong>6</strong>
              <span>объяснимых признаков</span>
            </div>
            <div>
              <strong>0</strong>
              <span>чёрных ящиков</span>
            </div>
          </div>
        </div>
        <p className="login__footnote">Данные: синтетический снимок · модель v1</p>
      </div>

      <div className="login__panel">
        <form className="login__card" onSubmit={submit}>
          <p className="eyebrow">ВХОД В ПАНЕЛЬ</p>
          <h2>Аналитик на связи</h2>
          <p className="muted">Доступ защищает клиентские данные и настройки модели.</p>

          <label className="field">
            <span>Email</span>
            <input
              type="email"
              autoComplete="username"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </label>
          <label className="field">
            <span>Пароль</span>
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </label>

          {error ? <div className="form-error">{error}</div> : null}

          <button className="button button--primary button--wide" disabled={busy}>
            {busy ? "Проверяем…" : "Войти"}
          </button>

          <p className="login__hint">
            Демо-доступ: <code>admin@example.test</code> / <code>admin123</code>
          </p>
        </form>
      </div>
    </div>
  );
}

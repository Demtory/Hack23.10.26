import {BrandLogo} from "../components/BrandLogo";
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
      <div className="login__aside"><BrandLogo/><div className="login__pitch"><p className="eyebrow">ПАНЕЛЬ МАРКЕТОЛОГА</p><h1>Данные превращаются<br/>в приоритеты.</h1><p>Найдите клиентов, которым нужно внимание.<br/>Разберитесь в причинах риска и денежной оценке.</p></div><p className="login__footnote">Risk Desk · Aéza</p></div>

      <div className="login__panel">
        <form className="login__card" onSubmit={submit}>
          <p className="eyebrow">ВХОД В ПАНЕЛЬ</p>
          <h2>Вход в Risk Desk</h2>
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

          {error ? <div className="form-error" role="alert">{error}</div> : null}

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

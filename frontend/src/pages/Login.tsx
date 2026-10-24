import {BrandLogo} from "../components/BrandLogo";
import { FormEvent, useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api, ApiError } from "../api";
import type { User } from "../types";

const SSO_ERRORS: Record<string, string> = {
  account_conflict: "Этот email уже связан с другой учётной записью. Обратитесь к администратору: автоматическое объединение запрещено.",
  provider_unavailable: "Провайдер входа недоступен. Войдите по паролю или попробуйте позже.",
  state_invalid: "Время входа истекло или ссылка недействительна. Начните вход заново.",
  exchange_failed: "Провайдер отклонил вход. Попробуйте ещё раз.",
  access_denied: "Вход через SSO отменён.",
  email_unverified: "У вашей учётной записи не подтверждён email. Обратитесь к администратору.",
  token_invalid: "Провайдер вернул некорректный ответ. Попробуйте войти снова.",
  nonce_mismatch: "Провайдер вернул некорректный ответ. Попробуйте войти снова.",
  issuer_mismatch: "Провайдер вернул некорректный ответ. Попробуйте войти снова.",
  audience_mismatch: "Провайдер вернул некорректный ответ. Попробуйте войти снова.",
  token_expired: "Ответ провайдера устарел. Попробуйте войти снова.",
};

export function Login({ onLogin }: { onLogin: (user: User) => void }) {
  const [email, setEmail] = useState("admin@example.test");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [sso, setSso] = useState<{ enabled: boolean; providerName: string } | null>(null);
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  useEffect(() => {
    let active = true;
    api.oidcConfig()
      .then((config) => { if (active) setSso(config); })
      .catch(() => { if (active) setSso({ enabled: false, providerName: "SSO" }); });
    const code = searchParams.get("sso_error");
    if (code) {
      setError(SSO_ERRORS[code] ?? "Не удалось войти через SSO. Попробуйте ещё раз.");
      navigate("/login", { replace: true });
    }
    return () => { active = false; };
    // searchParams меняется только при возврате с провайдера
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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

          {sso?.enabled ? (
            <>
              <a className="button button--primary button--wide" href="/api/v1/auth/oidc/start">
                Войти через {sso.providerName}
              </a>
              <p className="login__hint login__hint--sso">
                Демо-вход SSO: <code>marketer@example.test</code> / <code>marketer123</code>
              </p>
              <p className="login__divider"><span>или по паролю</span></p>
            </>
          ) : null}

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

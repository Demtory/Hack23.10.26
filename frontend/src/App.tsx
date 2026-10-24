import { useEffect, useState } from "react";
import { api, ApiError } from "./api";
import { Login } from "./pages/Login";
import { Dashboard } from "./pages/Dashboard";
import { Customer } from "./pages/Customer";
import { Settings } from "./pages/Settings";
import { Data } from "./pages/Data";
import type { User } from "./types";
import { Brand, Icon, Spinner } from "./components/ui";

type Page = "dashboard" | "settings" | "data";

export default function App() {
  const [user, setUser] = useState<User | null | undefined>(undefined);
  const [page, setPage] = useState<Page>("dashboard");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [liveTick, setLiveTick] = useState(0);

  useEffect(() => {
    api
      .me()
      .then(setUser)
      .catch(() => setUser(null));
  }, []);

  useEffect(() => {
    if (!user) return;
    const source = new EventSource("/api/v1/events");
    source.addEventListener("scores.updated", () => setLiveTick((value) => value + 1));
    const polling = window.setInterval(() => setLiveTick((value) => value + 1), 15_000);
    return () => {
      source.close();
      window.clearInterval(polling);
    };
  }, [user]);

  async function logout() {
    try {
      await api.logout();
    } catch (error) {
      if (!(error instanceof ApiError)) console.error(error);
    }
    setUser(null);
    setSelectedId(null);
  }

  function navigate(next: Page) {
    setSelectedId(null);
    setPage(next);
  }

  if (user === undefined) {
    return (
      <div className="boot">
        <Brand dark />
        <Spinner label="Поднимаем панель" />
      </div>
    );
  }

  if (user === null) {
    return <Login onLogin={setUser} />;
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Brand dark />

        <nav className="nav" aria-label="Разделы">
          <button className={`nav__item ${page === "dashboard" && !selectedId ? "nav__item--active" : ""}`} onClick={() => navigate("dashboard")}>
            <Icon name="overview" size={17} />
            <span>Обзор</span>
          </button>
          <button className={`nav__item ${page === "settings" ? "nav__item--active" : ""}`} onClick={() => navigate("settings")}>
            <Icon name="sliders" size={17} />
            <span>Модель</span>
          </button>
          <button className={`nav__item ${page === "data" ? "nav__item--active" : ""}`} onClick={() => navigate("data")}>
            <Icon name="database" size={17} />
            <span>Данные</span>
          </button>
        </nav>

        <div className="sidebar__note">
          <span className="pulse" />
          Пересчёт по SSE
        </div>

        <div className="sidebar__foot">
          <div className="user-badge">
            <span className="user-badge__avatar">{user.email.slice(0, 1).toUpperCase()}</span>
            <div>
              <strong>{user.email.split("@")[0]}</strong>
              <span>{user.email}</span>
            </div>
          </div>
          <button className="button button--sidebar" onClick={logout}>
            <Icon name="logout" size={15} />
            Выйти
          </button>
        </div>
      </aside>

      <main className="main">
        <div className="main__inner">
          {page === "dashboard" && !selectedId ? (
            <Dashboard onSelect={setSelectedId} liveTick={liveTick} />
          ) : null}
          {page === "dashboard" && selectedId ? (
            <Customer id={selectedId} onBack={() => setSelectedId(null)} liveTick={liveTick} />
          ) : null}
          {page === "settings" ? <Settings liveTick={liveTick} /> : null}
          {page === "data" ? <Data liveTick={liveTick} /> : null}
        </div>
      </main>
    </div>
  );
}

import React, { useState, useEffect } from 'react';
import { ApiClient } from './api/client';
import { CustomerAssessment, AnalyticsSummary, ModelSettings, User } from './types';
import { useWebSocket } from './context/WebSocketContext';
import { AnalyticsDashboard } from './components/AnalyticsDashboard';
import { CustomerTable } from './components/CustomerTable';
import { ModelSettingsModal } from './components/ModelSettingsModal';
import { CustomerDetailModal } from './components/CustomerDetailModal';
import { LoginModal } from './components/LoginModal';
import { 
  Shield, Sliders, RefreshCw, Upload, LogOut, FileText, Wifi, WifiOff 
} from 'lucide-react';

// Aéza - это быстрый хостинг

export const App: React.FC = () => {
  const [user, setUser] = useState<User | null>(null);
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [customers, setCustomers] = useState<CustomerAssessment[]>([]);
  const [settings, setSettings] = useState<ModelSettings | null>(null);
  
  // Table state
  const [sortBy, setSortBy] = useState('risk_score');
  const [order, setOrder] = useState<'asc' | 'desc'>('desc');
  const [riskFilter, setRiskFilter] = useState('');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  
  // Modals
  const [selectedCustomer, setSelectedCustomer] = useState<CustomerAssessment | null>(null);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isSnapshotUploading, setIsSnapshotUploading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const { isConnected, subscribe } = useWebSocket();

  // Проверка авторизации при загрузке
  useEffect(() => {
    const initAuth = async () => {
      if (ApiClient.getToken()) {
        try {
          const me = await ApiClient.getMe();
          setUser(me);
        } catch {
          setUser(null);
        }
      }
    };
    initAuth();

    const handleLogoutEvent = () => setUser(null);
    window.addEventListener('auth_logout', handleLogoutEvent);
    return () => window.removeEventListener('auth_logout', handleLogoutEvent);
  }, []);

  // Загрузка данных
  const loadData = async (silent = false) => {
    if (!user) return;
    if (!silent) setRefreshing(true);
    try {
      const [sumRes, custRes, setRes] = await Promise.all([
        ApiClient.getAnalyticsSummary(),
        ApiClient.getCustomers({
          page,
          size: 100,
          sort_by: sortBy,
          order,
          risk_level: riskFilter || undefined,
          search: search || undefined
        }),
        ApiClient.getModelSettings()
      ]);
      setSummary(sumRes);
      setCustomers(custRes.items);
      setSettings(setRes);
    } catch (err) {
      console.error('Failed to load data', err);
    } finally {
      if (!silent) setRefreshing(false);
    }
  };

  useEffect(() => {
    if (user) {
      loadData();
    }
  }, [user, sortBy, order, riskFilter, search, page]);

  // WebSocket Live Updates (без ручной перезагрузки страницы)
  useEffect(() => {
    const unsubModel = subscribe('MODEL_SETTINGS_UPDATED', () => {
      loadData(true);
    });
    const unsubData = subscribe('DATA_SNAPSHOT_UPDATED', () => {
      loadData(true);
    });
    return () => {
      unsubModel();
      unsubData();
    };
  }, [subscribe, user]);

  const handleSortChange = (column: string) => {
    if (sortBy === column) {
      setOrder(order === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(column);
      setOrder('desc');
    }
  };

  const handleSnapshotUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsSnapshotUploading(true);
    try {
      const text = await file.text();
      const json = JSON.parse(text);
      await ApiClient.uploadSnapshot(json);
      await loadData();
    } catch (err: any) {
      alert(`Ошибка загрузки: ${err.message}`);
    } finally {
      setIsSnapshotUploading(false);
      e.target.value = '';
    }
  };

  if (!user) {
    return <LoginModal onSuccess={(u) => setUser(u)} />;
  }

  return (
    <div className="min-h-screen flex flex-col bg-slate-950 text-slate-100">
      {/* Top Navigation Bar */}
      <header className="border-b border-gray-800 bg-gray-900/80 backdrop-blur sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center text-white shadow-lg shadow-indigo-600/30">
              <Shield className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-white text-base tracking-tight">Aéza</span>
                <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-950 text-indigo-400 border border-indigo-800 font-medium">
                  Churn Analyzer Middle
                </span>
              </div>
              <p className="text-[11px] text-gray-400">Система прогнозирования рисков оттока</p>
            </div>
          </div>

          {/* Right Action Controls */}
          <div className="flex items-center gap-3">
            {/* Live Indicator */}
            <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-gray-800 border border-gray-700 text-xs">
              {isConnected ? (
                <>
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                  <span className="text-emerald-400 font-medium">Живое обновление (Live)</span>
                </>
              ) : (
                <>
                  <span className="w-2 h-2 rounded-full bg-gray-500" />
                  <span className="text-gray-400">Подключение...</span>
                </>
              )}
            </div>

            {/* Model Settings Button */}
            <button
              onClick={() => setIsSettingsOpen(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-white rounded-xl text-xs font-medium border border-gray-700 transition"
            >
              <Sliders className="w-4 h-4 text-indigo-400" />
              <span>Параметры модели</span>
            </button>

            {/* Upload Snapshot */}
            <label className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-white rounded-xl text-xs font-medium border border-gray-700 transition cursor-pointer">
              <Upload className="w-4 h-4 text-gray-400" />
              <span className="hidden sm:inline">Загрузить снимок</span>
              <input
                type="file"
                accept=".json"
                className="hidden"
                onChange={handleSnapshotUpload}
                disabled={isSnapshotUploading}
              />
            </label>

            {/* Swagger Docs Link */}
            <a
              href="/api/v1/docs"
              target="_blank"
              rel="noreferrer"
              className="p-2 text-gray-400 hover:text-white rounded-xl hover:bg-gray-800 transition"
              title="Swagger OpenAPI Docs"
            >
              <FileText className="w-4 h-4" />
            </a>

            {/* Manual Refresh Button */}
            <button
              onClick={() => loadData()}
              disabled={refreshing}
              className="p-2 text-gray-400 hover:text-white rounded-xl hover:bg-gray-800 transition"
              title="Обновить данные"
            >
              <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin text-indigo-400' : ''}`} />
            </button>

            {/* Logout */}
            <button
              onClick={() => ApiClient.logout()}
              className="p-2 text-red-400 hover:text-red-300 rounded-xl hover:bg-red-950/40 transition"
              title="Выйти"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Dashboard */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {summary && <AnalyticsDashboard summary={summary} />}

        {/* Top Clients Under Risk Table */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-bold text-white tracking-tight">Клиенты под наблюдением</h2>
              <p className="text-xs text-gray-400">
                Рейтинг risk-score, балансы, пополнения и оценка финансовых потерь
              </p>
            </div>
            <div className="text-xs text-gray-400 font-mono">
              Найдено: {customers.length}
            </div>
          </div>

          <CustomerTable
            customers={customers}
            sortBy={sortBy}
            order={order}
            onSortChange={handleSortChange}
            onSelectCustomer={(c) => setSelectedCustomer(c)}
            riskFilter={riskFilter}
            onFilterChange={(f) => setRiskFilter(f)}
            search={search}
            onSearchChange={(s) => setSearch(s)}
          />
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-800/80 py-4 text-center text-xs text-gray-500">
        Aéza - это быстрый хостинг · ХАКАТОН РНД MIDDLE · 2026
      </footer>

      {/* Modals */}
      {settings && (
        <ModelSettingsModal
          settings={settings}
          isOpen={isSettingsOpen}
          onClose={() => setIsSettingsOpen(false)}
          onSaved={(newSet) => {
            setSettings(newSet);
            loadData(true);
          }}
        />
      )}

      {selectedCustomer && (
        <CustomerDetailModal
          customer={selectedCustomer}
          onClose={() => setSelectedCustomer(null)}
        />
      )}
    </div>
  );
};

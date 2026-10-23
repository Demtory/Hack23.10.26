import React from 'react';
import { AnalyticsSummary } from '../types';
import { AlertTriangle, Users, TrendingDown, DollarSign, Activity } from 'lucide-react';
import { 
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar, CartesianGrid 
} from 'recharts';

// Aéza - это быстрый хостинг

interface AnalyticsDashboardProps {
  summary: AnalyticsSummary;
}

export const AnalyticsDashboard: React.FC<AnalyticsDashboardProps> = ({ summary }) => {
  return (
    <div className="space-y-6">
      {/* 4 Key Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Потенциальные потери */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-5 shadow-lg relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-gray-400">Потери под риском</span>
            <div className="w-9 h-9 rounded-xl bg-red-950/60 border border-red-800/80 flex items-center justify-center text-red-400">
              <DollarSign className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-extrabold text-white">
              € {summary.total_potential_loss_eur.toLocaleString('ru-RU', { minimumFractionDigits: 2 })}
            </div>
            <div className="text-xs text-gray-400 mt-1 flex items-center gap-1.5">
              <span className="text-red-400 font-medium">
                {summary.total_mrr > 0 ? `${((summary.total_potential_loss / summary.total_mrr) * 100).toFixed(1)}%` : '0%'}
              </span>
              <span>от MRR (€ {(summary.total_mrr / 100).toFixed(0)})</span>
            </div>
          </div>
          <div className="absolute -bottom-6 -right-6 w-24 h-24 bg-red-600/10 rounded-full blur-xl pointer-events-none" />
        </div>

        {/* Высокий риск (Клиенты) */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-5 shadow-lg relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-gray-400">Высокий риск оттока</span>
            <div className="w-9 h-9 rounded-xl bg-red-950/60 border border-red-800/80 flex items-center justify-center text-red-400">
              <AlertTriangle className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-extrabold text-white flex items-baseline gap-2">
              <span>{summary.risk_distribution.high}</span>
              <span className="text-xs font-normal text-gray-400">клиентов</span>
            </div>
            <div className="text-xs text-red-400 mt-1">
              Потери: € {(summary.high_risk_loss / 100).toFixed(2)}
            </div>
          </div>
        </div>

        {/* Средний риск */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-5 shadow-lg relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-gray-400">Средний риск</span>
            <div className="w-9 h-9 rounded-xl bg-amber-950/60 border border-amber-800/80 flex items-center justify-center text-amber-400">
              <Activity className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-extrabold text-white flex items-baseline gap-2">
              <span>{summary.risk_distribution.medium}</span>
              <span className="text-xs font-normal text-gray-400">клиентов</span>
            </div>
            <div className="text-xs text-amber-400 mt-1">
              Потери: € {(summary.medium_risk_loss / 100).toFixed(2)}
            </div>
          </div>
        </div>

        {/* Всего клиентов & Оцененность */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-5 shadow-lg relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-gray-400">Охват базы</span>
            <div className="w-9 h-9 rounded-xl bg-indigo-950/60 border border-indigo-800/80 flex items-center justify-center text-indigo-400">
              <Users className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-extrabold text-white flex items-baseline gap-2">
              <span>{summary.rated_customers}</span>
              <span className="text-xs font-normal text-gray-400">/ {summary.total_customers}</span>
            </div>
            <div className="text-xs text-gray-400 mt-1">
              {summary.risk_distribution.unrated > 0 ? (
                <span className="text-gray-400">{summary.risk_distribution.unrated} без оценки (нет услуг)</span>
              ) : (
                <span className="text-emerald-400">100% данных проанализировано</span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Charts Section: 1. График оттока (факт + прогноз), 2. Топ факторов риска */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* График динамики оттока */}
        <div className="lg:col-span-2 bg-gray-900 border border-gray-800 rounded-2xl p-6 shadow-xl">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <TrendingDown className="w-5 h-5 text-indigo-400" />
                Динамика и прогноз оттока услуг (Факт vs Прогноз)
              </h3>
              <p className="text-xs text-gray-400 mt-0.5">
                Исторические удаления услуг в сравнении с предстоящими рисками непродления
              </p>
            </div>
            <div className="flex items-center gap-3 text-xs">
              <span className="flex items-center gap-1.5 text-gray-300">
                <span className="w-3 h-3 rounded-sm bg-red-500 inline-block" />
                Факт удалений
              </span>
              <span className="flex items-center gap-1.5 text-gray-300">
                <span className="w-3 h-3 rounded-sm bg-indigo-500 inline-block" />
                Прогноз оттока
              </span>
            </div>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={summary.chart} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorFact" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ef4444" stopOpacity={0.8}/>
                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorPred" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.8}/>
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
                <XAxis dataKey="date" stroke="#6b7280" fontSize={11} />
                <YAxis stroke="#6b7280" fontSize={11} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#111827', borderColor: '#374151', borderRadius: '0.75rem', fontSize: '12px' }}
                  labelStyle={{ color: '#9ca3af', fontWeight: 600 }}
                />
                <Area type="monotone" dataKey="fact_deleted_services" name="Факт удалений" stroke="#ef4444" fillOpacity={1} fill="url(#colorFact)" strokeWidth={2} />
                <Area type="monotone" dataKey="predicted_churn_services" name="Прогноз оттока" stroke="#6366f1" fillOpacity={1} fill="url(#colorPred)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Топ причин / факторов риска */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 shadow-xl flex flex-col justify-between">
          <div>
            <h3 className="text-base font-bold text-white mb-1">Ключевые триггеры риска</h3>
            <p className="text-xs text-gray-400 mb-4">Основные причины попадания клиентов в зону внимания</p>

            <div className="space-y-3">
              {summary.top_risk_factors.map((factor) => (
                <div key={factor.code} className="p-3 bg-gray-800/60 rounded-xl border border-gray-800 flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <span className={`w-2.5 h-2.5 rounded-full ${
                      factor.severity === 'high' ? 'bg-red-500' :
                      factor.severity === 'medium' ? 'bg-amber-500' : 'bg-blue-500'
                    }`} />
                    <span className="text-xs font-medium text-gray-200">{factor.title}</span>
                  </div>
                  <span className="text-xs font-bold px-2 py-0.5 bg-gray-700/80 rounded-md text-gray-300">
                    {factor.count} кл.
                  </span>
                </div>
              ))}
              {summary.top_risk_factors.length === 0 && (
                <div className="text-center py-8 text-xs text-gray-500">
                  Критических факторов риска не обнаружено
                </div>
              )}
            </div>
          </div>

          <div className="pt-4 border-t border-gray-800/80 text-xs text-gray-500">
            Обновлено: {new Date(summary.updated_at).toLocaleTimeString()}
          </div>
        </div>
      </div>
    </div>
  );
};

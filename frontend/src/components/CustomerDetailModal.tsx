import React from 'react';
import { CustomerAssessment } from '../types';
import { 
  X, AlertTriangle, ShieldAlert, CheckCircle, Clock, Server, 
  CreditCard, TrendingDown, RefreshCw 
} from 'lucide-react';

// Aéza - это быстрый хостинг

interface CustomerDetailModalProps {
  customer: CustomerAssessment | null;
  onClose: () => void;
}

export const CustomerDetailModal: React.FC<CustomerDetailModalProps> = ({
  customer,
  onClose
}) => {
  if (!customer) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-80 backdrop-blur-sm p-4">
      <div className="bg-gray-900 border border-gray-800 rounded-2xl w-full max-w-2xl p-6 sm:p-8 shadow-2xl animate-fade-in relative max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-start justify-between pb-4 border-b border-gray-800">
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs px-2 py-0.5 rounded bg-gray-800 text-gray-400">
                ID #{customer.id}
              </span>
              <h2 className="text-xl font-bold text-white">{customer.email}</h2>
            </div>
            <p className="text-xs text-gray-400 mt-1">
              Детальный профиль риска клиента и объяснение факторов
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white p-1 rounded-lg text-lg leading-none"
          >
            ✕
          </button>
        </div>

        {/* Top Summary Banner */}
        <div className="mt-6 grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="bg-gray-950/70 border border-gray-800 p-3 rounded-xl">
            <span className="text-xs text-gray-500 uppercase tracking-wider block">Risk-Score</span>
            <span className={`text-xl font-extrabold font-mono ${
              customer.risk_level === 'high' ? 'text-red-400' :
              customer.risk_level === 'medium' ? 'text-amber-400' : 'text-emerald-400'
            }`}>
              {customer.risk_score !== null ? `${(customer.risk_score * 100).toFixed(0)}%` : 'N/A'}
            </span>
          </div>

          <div className="bg-gray-950/70 border border-gray-800 p-3 rounded-xl">
            <span className="text-xs text-gray-500 uppercase tracking-wider block">Потери бизнеса</span>
            <span className="text-xl font-extrabold font-mono text-red-400">
              € {(customer.potential_loss / 100).toFixed(2)}
            </span>
          </div>

          <div className="bg-gray-950/70 border border-gray-800 p-3 rounded-xl">
            <span className="text-xs text-gray-500 uppercase tracking-wider block">Баланс</span>
            <span className="text-xl font-extrabold font-mono text-white">
              € {(customer.balance / 100).toFixed(2)}
            </span>
          </div>

          <div className="bg-gray-950/70 border border-gray-800 p-3 rounded-xl">
            <span className="text-xs text-gray-500 uppercase tracking-wider block">MRR клиента</span>
            <span className="text-xl font-extrabold font-mono text-indigo-400">
              € {(customer.monthly_recurring_revenue / 100).toFixed(2)}
            </span>
          </div>
        </div>

        {/* Explainability Section */}
        <div className="mt-6">
          <h3 className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-3 flex items-center gap-1.5">
            <ShieldAlert className="w-4 h-4 text-indigo-400" />
            Факторы риска и объяснение оценки
          </h3>
          <div className="space-y-2.5">
            {customer.risk_factors.map((f, idx) => (
              <div 
                key={idx}
                className={`p-3.5 rounded-xl border flex items-start justify-between gap-3 ${
                  f.severity === 'high' ? 'bg-red-950/30 border-red-900/60' :
                  f.severity === 'medium' ? 'bg-amber-950/30 border-amber-900/60' :
                  'bg-gray-800/40 border-gray-800'
                }`}
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${
                      f.severity === 'high' ? 'bg-red-500' :
                      f.severity === 'medium' ? 'bg-amber-500' : 'bg-emerald-500'
                    }`} />
                    <span className="text-xs font-bold text-white">{f.title}</span>
                  </div>
                  <p className="text-xs text-gray-400 mt-1 pl-4">
                    {f.description}
                  </p>
                </div>
                {f.weight_impact > 0 && (
                  <span className="text-xs font-mono px-2 py-0.5 rounded bg-gray-800 text-gray-300 flex-shrink-0">
                    +{(f.weight_impact * 100).toFixed(1)}% к риску
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Services List */}
        <div className="mt-6">
          <h3 className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-3 flex items-center gap-1.5">
            <Server className="w-4 h-4 text-indigo-400" />
            Услуги клиента ({customer.services?.length || 0})
          </h3>
          <div className="space-y-2">
            {(customer.services || []).map((srv) => (
              <div 
                key={srv.id}
                className={`p-3 rounded-xl border flex flex-col sm:flex-row sm:items-center justify-between gap-2 ${
                  srv.is_at_risk ? 'bg-red-950/20 border-red-900/40' : 'bg-gray-800/30 border-gray-800'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg ${
                    srv.status === 'active' ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' :
                    srv.status === 'prolong_wait' ? 'bg-red-950 text-red-400 border border-red-800' :
                    'bg-gray-800 text-gray-400'
                  }`}>
                    <Server className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-white">{srv.name}</span>
                      <span className={`text-[10px] px-1.5 py-0.5 rounded font-mono uppercase ${
                        srv.status === 'active' ? 'bg-emerald-900/60 text-emerald-300' :
                        srv.status === 'prolong_wait' ? 'bg-red-900/60 text-red-300' :
                        'bg-gray-700 text-gray-300'
                      }`}>
                        {srv.status}
                      </span>
                    </div>
                    <div className="text-[11px] text-gray-400 flex items-center gap-3 mt-0.5">
                      <span>Истекает: {new Date(srv.expiresAt).toLocaleDateString()}</span>
                      <span>Период: {srv.paymentTerm}</span>
                      <span>Автопродление: {srv.autoProlong ? 'Да' : 'Нет'}</span>
                    </div>
                  </div>
                </div>

                <div className="text-right flex-shrink-0">
                  <div className="font-mono text-xs font-bold text-white">
                    € {(srv.price / 100).toFixed(2)}
                  </div>
                  {srv.risk_factors.length > 0 && (
                    <div className="text-[10px] text-red-400 mt-0.5">
                      {srv.risk_factors.join(', ')}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="mt-8 pt-4 border-t border-gray-800 flex justify-end">
          <button
            onClick={onClose}
            className="px-5 py-2.5 bg-gray-800 hover:bg-gray-700 text-white rounded-xl text-xs font-medium transition"
          >
            Закрыть
          </button>
        </div>
      </div>
    </div>
  );
};

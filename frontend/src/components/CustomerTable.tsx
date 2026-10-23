import React from 'react';
import { CustomerAssessment } from '../types';
import { 
  ArrowUpDown, ArrowUp, ArrowDown, HelpCircle, 
  ChevronRight 
} from 'lucide-react';

// Aéza - это быстрый хостинг

interface CustomerTableProps {
  customers: CustomerAssessment[];
  sortBy: string;
  order: 'asc' | 'desc';
  onSortChange: (column: string) => void;
  onSelectCustomer: (customer: CustomerAssessment) => void;
  riskFilter: string;
  onFilterChange: (filter: string) => void;
  search: string;
  onSearchChange: (search: string) => void;
}

export const CustomerTable: React.FC<CustomerTableProps> = ({
  customers,
  sortBy,
  order,
  onSortChange,
  onSelectCustomer,
  riskFilter,
  onFilterChange,
  search,
  onSearchChange,
}) => {
  const renderSortIcon = (column: string) => {
    if (sortBy !== column) {
      return <ArrowUpDown className="w-3.5 h-3.5 text-gray-600 inline ml-1 opacity-0 group-hover:opacity-100 transition" />;
    }
    return order === 'asc' ? (
      <ArrowUp className="w-3.5 h-3.5 text-indigo-400 inline ml-1" />
    ) : (
      <ArrowDown className="w-3.5 h-3.5 text-indigo-400 inline ml-1" />
    );
  };

  const getRiskBadge = (level: string, score: number | null) => {
    switch (level) {
      case 'high':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-red-950 text-red-400 border border-red-800">
            <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" />
            Высокий ({score !== null ? (score * 100).toFixed(0) + '%' : ''})
          </span>
        );
      case 'medium':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-950 text-amber-400 border border-amber-800">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
            Средний ({score !== null ? (score * 100).toFixed(0) + '%' : ''})
          </span>
        );
      case 'low':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-950 text-emerald-400 border border-emerald-800">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
            Низкий ({score !== null ? (score * 100).toFixed(0) + '%' : ''})
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-gray-800 text-gray-400 border border-gray-700">
            <HelpCircle className="w-3 h-3 text-gray-500" />
            Нет оценки
          </span>
        );
    }
  };

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-2xl shadow-xl overflow-hidden">
      {/* Controls Bar: Search & Filter Tabs */}
      <div className="p-4 sm:p-5 border-b border-gray-800 flex flex-col sm:flex-row gap-4 items-center justify-between">
        <div className="w-full sm:w-72">
          <input
            type="text"
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Поиск по email или ID..."
            className="w-full px-3.5 py-2 bg-gray-800 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500 text-xs sm:text-sm"
          />
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-1.5 bg-gray-950 p-1 rounded-xl border border-gray-800 self-stretch sm:self-auto overflow-x-auto">
          {[
            { id: '', label: 'Все клиенты' },
            { id: 'high', label: 'Высокий риск' },
            { id: 'medium', label: 'Средний риск' },
            { id: 'low', label: 'Низкий риск' },
            { id: 'unrated', label: 'Без оценки' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => onFilterChange(tab.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition ${
                riskFilter === tab.id
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-gray-400 hover:text-white hover:bg-gray-800'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs sm:text-sm">
          <thead className="bg-gray-950/70 border-b border-gray-800 text-gray-400 text-xs uppercase tracking-wider select-none">
            <tr>
              <th 
                className="py-3.5 px-4 cursor-pointer hover:text-white group"
                onClick={() => onSortChange('id')}
              >
                ID {renderSortIcon('id')}
              </th>
              <th 
                className="py-3.5 px-4 cursor-pointer hover:text-white group"
                onClick={() => onSortChange('email')}
              >
                Клиент {renderSortIcon('email')}
              </th>
              <th 
                className="py-3.5 px-4 cursor-pointer hover:text-white group"
                onClick={() => onSortChange('balance')}
              >
                Баланс {renderSortIcon('balance')}
              </th>
              <th 
                className="py-3.5 px-4 cursor-pointer hover:text-white group"
                onClick={() => onSortChange('totalReplenished')}
              >
                Пополнено {renderSortIcon('totalReplenished')}
              </th>
              <th 
                className="py-3.5 px-4 cursor-pointer hover:text-white group"
                onClick={() => onSortChange('risk_score')}
              >
                Risk-Score {renderSortIcon('risk_score')}
              </th>
              <th 
                className="py-3.5 px-4 cursor-pointer hover:text-white group"
                onClick={() => onSortChange('potential_loss')}
              >
                Потери бизнеса {renderSortIcon('potential_loss')}
              </th>
              <th className="py-3.5 px-4">Главный фактор риска</th>
              <th className="py-3.5 px-4 text-right">Детали</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800/60">
            {customers.map((c) => (
              <tr 
                key={c.id}
                onClick={() => onSelectCustomer(c)}
                className="hover:bg-gray-800/40 transition cursor-pointer group"
              >
                <td className="py-3.5 px-4 font-mono font-medium text-gray-400">
                  #{c.id}
                </td>
                <td className="py-3.5 px-4">
                  <div className="font-semibold text-white">{c.email}</div>
                  <div className="text-xs text-gray-500">
                    Услуг: {c.active_services_count} акт. / {c.total_services_count} всего
                  </div>
                </td>
                <td className="py-3.5 px-4 font-mono">
                  <div className="text-white font-medium">
                    € {(c.balance / 100).toFixed(2)}
                  </div>
                  {c.bonusBalance > 0 && (
                    <div className="text-xs text-indigo-400">
                      +€ {(c.bonusBalance / 100).toFixed(2)} бонус
                    </div>
                  )}
                </td>
                <td className="py-3.5 px-4 font-mono text-gray-300">
                  € {(c.totalReplenished / 100).toFixed(2)}
                </td>
                <td className="py-3.5 px-4">
                  <div className="flex items-center gap-2">
                    {getRiskBadge(c.risk_level, c.risk_score)}
                  </div>
                </td>
                <td className="py-3.5 px-4 font-mono font-bold text-red-400">
                  € {(c.potential_loss / 100).toFixed(2)}
                </td>
                <td className="py-3.5 px-4">
                  <span className="text-xs text-gray-300 line-clamp-1">
                    {c.primary_reason}
                  </span>
                </td>
                <td className="py-3.5 px-4 text-right">
                  <button className="p-1.5 rounded-lg bg-gray-800 text-gray-400 group-hover:text-white group-hover:bg-indigo-600 transition">
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </td>
              </tr>
            ))}
            {customers.length === 0 && (
              <tr>
                <td colSpan={8} className="py-12 text-center text-gray-500 text-sm">
                  Клиенты по заданным критериям не найдены
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

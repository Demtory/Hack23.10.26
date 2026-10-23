import React, { useState } from 'react';
import { ModelSettings } from '../types';
import { ApiClient } from '../api/client';
import { Sliders, Check, RotateCcw, AlertCircle, Save } from 'lucide-react';

// Aéza - это быстрый хостинг

interface ModelSettingsModalProps {
  settings: ModelSettings;
  isOpen: boolean;
  onClose: () => void;
  onSaved: (updated: ModelSettings) => void;
}

export const ModelSettingsModal: React.FC<ModelSettingsModalProps> = ({
  settings,
  isOpen,
  onClose,
  onSaved
}) => {
  const [formData, setFormData] = useState<ModelSettings>(settings);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  if (!isOpen) return null;

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(false);

    try {
      const updated = await ApiClient.updateModelSettings(formData);
      setSuccess(true);
      onSaved(updated);
      setTimeout(() => {
        setSuccess(false);
        onClose();
      }, 700);
    } catch (err: any) {
      setError(err.message || 'Ошибка сохранения настроек');
    } finally {
      setLoading(false);
    }
  };

  const handleResetDefaults = () => {
    setFormData({
      weights: {
        w_no_autoprolong: 0.25,
        w_balance_insufficient: 0.35,
        w_prolong_wait: 0.20,
        w_expiring_soon: 0.10,
        w_failed_transactions: 0.10
      },
      thresholds: {
        high: 0.65,
        medium: 0.35
      },
      forecast_days: 7,
      loss_estimation_method: 'weighted_mrr'
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-80 backdrop-blur-sm p-4">
      <div className="bg-gray-900 border border-gray-800 rounded-2xl w-full max-w-xl p-6 sm:p-8 shadow-2xl animate-fade-in relative max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between pb-4 border-b border-gray-800">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-indigo-600/20 text-indigo-400 rounded-xl">
              <Sliders className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">Параметры и коэффициенты модели</h2>
              <p className="text-xs text-gray-400">Настройка весов факторов риска и пороговых значений</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white p-1 rounded-lg text-lg leading-none"
          >
            ✕
          </button>
        </div>

        {error && (
          <div className="mt-4 p-3 bg-red-950 border border-red-800 text-red-300 rounded-xl text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSave} className="mt-6 space-y-6">
          {/* Weights */}
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-indigo-400 mb-3">
              Веса факторов риска (сумма нормализуется автоматически)
            </h3>
            <div className="space-y-3">
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-gray-300">Недостаточно средств на балансе</span>
                  <span className="font-mono text-indigo-400">{formData.weights.w_balance_insufficient}</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={formData.weights.w_balance_insufficient}
                  onChange={(e) => setFormData({
                    ...formData,
                    weights: { ...formData.weights, w_balance_insufficient: parseFloat(e.target.value) }
                  })}
                  className="w-full accent-indigo-500"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-gray-300">Отключено автопродление</span>
                  <span className="font-mono text-indigo-400">{formData.weights.w_no_autoprolong}</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={formData.weights.w_no_autoprolong}
                  onChange={(e) => setFormData({
                    ...formData,
                    weights: { ...formData.weights, w_no_autoprolong: parseFloat(e.target.value) }
                  })}
                  className="w-full accent-indigo-500"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-gray-300">Статус prolong_wait (ожидание оплаты)</span>
                  <span className="font-mono text-indigo-400">{formData.weights.w_prolong_wait}</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={formData.weights.w_prolong_wait}
                  onChange={(e) => setFormData({
                    ...formData,
                    weights: { ...formData.weights, w_prolong_wait: parseFloat(e.target.value) }
                  })}
                  className="w-full accent-indigo-500"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-gray-300">Скорое истечение срока (&lt;24-48ч)</span>
                  <span className="font-mono text-indigo-400">{formData.weights.w_expiring_soon}</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={formData.weights.w_expiring_soon}
                  onChange={(e) => setFormData({
                    ...formData,
                    weights: { ...formData.weights, w_expiring_soon: parseFloat(e.target.value) }
                  })}
                  className="w-full accent-indigo-500"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-gray-300">Ошибки/неуспешные транзакции</span>
                  <span className="font-mono text-indigo-400">{formData.weights.w_failed_transactions}</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={formData.weights.w_failed_transactions}
                  onChange={(e) => setFormData({
                    ...formData,
                    weights: { ...formData.weights, w_failed_transactions: parseFloat(e.target.value) }
                  })}
                  className="w-full accent-indigo-500"
                />
              </div>
            </div>
          </div>

          {/* Thresholds */}
          <div className="pt-4 border-t border-gray-800">
            <h3 className="text-xs font-bold uppercase tracking-wider text-indigo-400 mb-3">
              Пороги классификации риска
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-gray-400 mb-1">Порог высокого риска (от)</label>
                <input
                  type="number"
                  step="0.05"
                  min="0.1"
                  max="0.99"
                  value={formData.thresholds.high}
                  onChange={(e) => setFormData({
                    ...formData,
                    thresholds: { ...formData.thresholds, high: parseFloat(e.target.value) }
                  })}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-xl text-white text-xs font-mono"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Порог среднего риска (от)</label>
                <input
                  type="number"
                  step="0.05"
                  min="0.05"
                  max="0.9"
                  value={formData.thresholds.medium}
                  onChange={(e) => setFormData({
                    ...formData,
                    thresholds: { ...formData.thresholds, medium: parseFloat(e.target.value) }
                  })}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-xl text-white text-xs font-mono"
                />
              </div>
            </div>
          </div>

          {/* Method and Horizon */}
          <div className="pt-4 border-t border-gray-800 grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-400 mb-1">Горизонт прогноза (дней)</label>
              <input
                type="number"
                min="1"
                max="90"
                value={formData.forecast_days}
                onChange={(e) => setFormData({
                  ...formData,
                  forecast_days: parseInt(e.target.value) || 7
                })}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-xl text-white text-xs font-mono"
              />
            </div>

            <div>
              <label className="block text-xs text-gray-400 mb-1">Способ оценки потерь</label>
              <select
                value={formData.loss_estimation_method}
                onChange={(e) => setFormData({
                  ...formData,
                  loss_estimation_method: e.target.value
                })}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-xl text-white text-xs"
              >
                <option value="weighted_mrr">Взвешенный MRR (Рекомендуемый)</option>
                <option value="total_at_risk">Сумма услуг под риском</option>
                <option value="raw_price">Сумма всех цен услуг</option>
              </select>
            </div>
          </div>

          {/* Action buttons */}
          <div className="pt-4 border-t border-gray-800 flex items-center justify-between">
            <button
              type="button"
              onClick={handleResetDefaults}
              className="flex items-center gap-1.5 px-3 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-xl text-xs transition"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Сбросить к базовым
            </button>

            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-xl text-xs transition"
              >
                Отмена
              </button>
              <button
                type="submit"
                disabled={loading}
                className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-xl text-xs shadow-lg shadow-indigo-600/30 transition"
              >
                {success ? (
                  <>
                    <Check className="w-4 h-4 text-emerald-400" />
                    Сохранено!
                  </>
                ) : loading ? (
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                ) : (
                  <>
                    <Save className="w-4 h-4" />
                    Применить и пересчитать
                  </>
                )}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};

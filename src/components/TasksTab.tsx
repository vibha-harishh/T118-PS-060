import React, { useState, useEffect } from 'react';
import { Layers, CloudRain, Zap, Star, AlertCircle } from 'lucide-react';
import { TaskEvent } from '../types';
import { api } from '../api';

interface TasksTabProps {
  onRefresh: () => void;
}

export const TasksTab: React.FC<TasksTabProps> = () => {
  const [tasks, setTasks] = useState<TaskEvent[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchTasks = async () => {
    try {
      setLoading(true);
      const data = await api.getTasks(150);
      setTasks(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTasks();
  }, []);

  return (
    <div className="space-y-4">
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 shadow-sm flex items-center justify-between">
        <div>
          <h3 className="text-base font-semibold text-white">Task Events & Distance Earnings</h3>
          <p className="text-xs text-slate-400">
            Earnings formula: ₹25 base + ₹6/km beyond 3km • Rain (x1.5) & Surge (x1.3) slots • Customer cancel pickup: ₹20 • Calculated in Python
          </p>
        </div>
        <span className="text-xs px-2.5 py-1 bg-slate-800 rounded border border-slate-700 text-slate-300 font-mono">
          {tasks.length} events loaded
        </span>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-800/80 text-slate-300 uppercase font-semibold tracking-wider border-b border-slate-700">
              <tr>
                <th className="py-3 px-3">Event ID</th>
                <th className="py-3 px-3">Task ID</th>
                <th className="py-3 px-3">Partner</th>
                <th className="py-3 px-3">Event Type</th>
                <th className="py-3 px-3">Event TS (IST)</th>
                <th className="py-3 px-3">Slot & Multiplier</th>
                <th className="py-3 px-3 text-right">Distance</th>
                <th className="py-3 px-3 text-center">Pickup</th>
                <th className="py-3 px-3 text-center">Rating</th>
                <th className="py-3 px-3">Week Start</th>
                <th className="py-3 px-3 text-right">Earnings</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 text-slate-200 font-mono">
              {tasks.length === 0 ? (
                <tr>
                  <td colSpan={11} className="text-center py-12 text-slate-400 font-sans">
                    <div className="flex flex-col items-center justify-center space-y-2">
                      <Layers className="w-8 h-8 text-slate-500" />
                      <div className="text-sm font-medium text-slate-300">No task events ingested yet</div>
                      <p className="text-xs text-slate-500 max-w-sm">
                        Upload <code className="text-emerald-400">task_events.csv</code> in the Datasets tab to calculate weekly earnings, ratings, and incentives.
                      </p>
                    </div>
                  </td>
                </tr>
              ) : (
                tasks.map((t) => (
                  <tr key={t.event_id} className="hover:bg-slate-800/50 transition-colors">
                    <td className="py-2 px-3 text-slate-400">{t.event_id}</td>
                    <td className="py-2 px-3 font-bold text-white">{t.task_id}</td>
                    <td className="py-2 px-3 text-emerald-400">{t.partner_id}</td>
                    <td className="py-2 px-3 font-sans">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-medium ${
                        t.event_type === 'COMPLETED'
                          ? 'bg-emerald-950 text-emerald-300 border border-emerald-800/60'
                          : t.event_type === 'CANCELLED_BY_CUSTOMER'
                          ? 'bg-amber-950 text-amber-300 border border-amber-800/60'
                          : 'bg-rose-950 text-rose-300 border border-rose-800/60'
                      }`}>
                        {t.event_type}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-slate-400">{t.event_ts}</td>
                    <td className="py-2 px-3 font-sans">
                      <div className="flex items-center space-x-1.5">
                        <span className="font-mono text-xs text-slate-400">{t.slot_id || '—'}</span>
                        {t.rain ? (
                          <span className="px-1.5 py-0.2 rounded bg-blue-950 text-blue-300 border border-blue-800 text-[10px] flex items-center space-x-0.5">
                            <CloudRain className="w-3 h-3 inline" />
                            <span>x1.5</span>
                          </span>
                        ) : t.surge ? (
                          <span className="px-1.5 py-0.2 rounded bg-amber-950 text-amber-300 border border-amber-800 text-[10px] flex items-center space-x-0.5">
                            <Zap className="w-3 h-3 inline" />
                            <span>x1.3</span>
                          </span>
                        ) : null}
                      </div>
                    </td>
                    <td className="py-2 px-3 text-right">
                      {t.distance_km != null ? `${t.distance_km.toFixed(1)} km` : '—'}
                    </td>
                    <td className="py-2 px-3 text-center font-sans">
                      {t.picked_up != null ? (t.picked_up ? 'Yes' : 'No') : '—'}
                    </td>
                    <td className="py-2 px-3 text-center">
                      {t.rating != null ? (
                        <span className="text-amber-400 flex items-center justify-center space-x-0.5">
                          <span>{t.rating}</span>
                          <Star className="w-3 h-3 fill-amber-400" />
                        </span>
                      ) : '—'}
                    </td>
                    <td className="py-2 px-3 text-slate-400">{t.week_start}</td>
                    <td className="py-2 px-3 text-right font-bold text-emerald-400">
                      ₹{t.task_earnings_rupees.toFixed(2)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

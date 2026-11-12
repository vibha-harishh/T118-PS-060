import React, { useState, useEffect } from 'react';
import { Clock, Play, CheckCircle2, AlertCircle, DollarSign, Users, ShieldAlert } from 'lucide-react';
import { SettlementBatch } from '../types';
import { api } from '../api';

interface BatchesTabProps {
  onRefresh: () => void;
  setBannerMessage: (msg: { text: string; type: 'success' | 'error' | 'info' } | null) => void;
}

export const BatchesTab: React.FC<BatchesTabProps> = ({ onRefresh, setBannerMessage }) => {
  const [batches, setBatches] = useState<SettlementBatch[]>([]);
  const [loading, setLoading] = useState(true);
  const [batchDateInput, setBatchDateInput] = useState('2026-09-14');
  const [runningBatch, setRunningBatch] = useState(false);

  const fetchBatches = async () => {
    try {
      setLoading(true);
      const data = await api.getBatches();
      setBatches(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBatches();
  }, []);

  const handleRunBatch = async () => {
    if (!batchDateInput.trim()) return;
    try {
      setRunningBatch(true);
      const res = await api.runBatch(batchDateInput.trim());
      setBannerMessage({
        text: `Batch ${batchDateInput} processed successfully! Paid: ₹${(res.batch.amount_paid_paise / 100).toFixed(2)}, Held: ₹${(res.batch.amount_held_paise / 100).toFixed(2)}`,
        type: 'success'
      });
      await fetchBatches();
      onRefresh();
    } catch (err: any) {
      setBannerMessage({ text: err.message, type: 'error' });
    } finally {
      setRunningBatch(false);
    }
  };

  const sampleDates = [
    '2026-09-14',
    '2026-09-21',
    '2026-09-28',
    '2026-10-05',
    '2026-10-12',
    '2026-10-19',
    '2026-10-26',
    '2026-11-02'
  ];

  return (
    <div className="space-y-6">
      {/* Batch Runner Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 shadow-sm">
        <h3 className="text-base font-semibold text-white mb-1 flex items-center space-x-2">
          <Clock className="w-5 h-5 text-emerald-400" />
          <span>Execute Weekly Monday Settlement Batch</span>
        </h3>
        <p className="text-xs text-slate-400 mb-4">
          Settlement batches run every Monday to process the previous Monday-to-Sunday week (IST).
          Calculates gross earnings, incentives, penalty cap, TDS, equipment deductions, and carry-forwards.
        </p>

        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center space-x-2">
            <span className="text-xs text-slate-300 font-medium">Batch Date (Monday):</span>
            <input
              type="date"
              value={batchDateInput}
              onChange={(e) => setBatchDateInput(e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded px-3 py-1.5 text-xs text-white font-mono focus:outline-none focus:border-emerald-500"
            />
          </div>

          <button
            onClick={handleRunBatch}
            disabled={runningBatch}
            className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-xs font-semibold flex items-center space-x-1.5 transition-colors disabled:opacity-50"
          >
            <Play className="w-3.5 h-3.5" />
            <span>{runningBatch ? 'Processing...' : 'Run Batch'}</span>
          </button>

          <div className="flex items-center space-x-1 text-xs text-slate-400 ml-auto">
            <span>Quick pick:</span>
            {sampleDates.slice(0, 5).map((d) => (
              <button
                key={d}
                onClick={() => setBatchDateInput(d)}
                className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 font-mono text-[11px]"
              >
                {d.slice(5)}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Batches Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden shadow-sm">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <h4 className="text-sm font-semibold text-slate-200">Executed Batches (batch_summary.csv)</h4>
          <span className="text-xs font-mono text-slate-400">{batches.length} batches</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-800/80 text-slate-300 uppercase font-semibold tracking-wider border-b border-slate-700">
              <tr>
                <th className="py-3 px-3">Batch Date</th>
                <th className="py-3 px-3 text-center">Partners Paid</th>
                <th className="py-3 px-3 text-right">Amount Paid</th>
                <th className="py-3 px-3 text-center">Partners Held</th>
                <th className="py-3 px-3 text-right">Amount Held</th>
                <th className="py-3 px-3 text-right">Carried Forward</th>
                <th className="py-3 px-3 text-center">Retries</th>
                <th className="py-3 px-3 text-right">TDS Total</th>
                <th className="py-3 px-3">Processed TS</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 text-slate-200 font-mono">
              {batches.length === 0 ? (
                <tr>
                  <td colSpan={9} className="text-center py-12 text-slate-500 font-sans">
                    No settlement batches executed yet. Click &quot;Run Batch&quot; or execute commands.txt.
                  </td>
                </tr>
              ) : (
                batches.map((b) => (
                  <tr key={b.batch_date} className="hover:bg-slate-800/50">
                    <td className="py-2.5 px-3 font-bold text-white font-sans">{b.batch_date}</td>
                    <td className="py-2.5 px-3 text-center text-emerald-400 font-bold">{b.partners_paid}</td>
                    <td className="py-2.5 px-3 text-right text-emerald-400 font-bold">
                      ₹{b.amount_paid_rupees.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-2.5 px-3 text-center text-rose-400">{b.partners_held}</td>
                    <td className="py-2.5 px-3 text-right text-rose-400">
                      ₹{b.amount_held_rupees.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-2.5 px-3 text-right text-amber-400">
                      ₹{b.carried_forward_rupees.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-2.5 px-3 text-center text-slate-300">{b.retries}</td>
                    <td className="py-2.5 px-3 text-right text-blue-400 font-bold">
                      ₹{b.tds_total_rupees.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-2.5 px-3 text-slate-400 text-[11px] font-sans">{b.processed_ts}</td>
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

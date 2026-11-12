import React, { useState, useEffect } from 'react';
import { Percent, Download, Search, RefreshCw } from 'lucide-react';
import { LedgerEntry } from '../types';
import { api } from '../api';

export const LedgerTab: React.FC = () => {
  const [entries, setEntries] = useState<LedgerEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [partnerFilter, setPartnerFilter] = useState('');

  const fetchLedger = async () => {
    try {
      setLoading(true);
      const data = await api.getLedger(partnerFilter.trim() || undefined);
      setEntries(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLedger();
  }, [partnerFilter]);

  return (
    <div className="space-y-4">
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 shadow-sm flex flex-wrap gap-3 items-center justify-between">
        <div>
          <h3 className="text-base font-semibold text-white">Partner Financial Ledger</h3>
          <p className="text-xs text-slate-400">
            Immutable double-entry balance audit trail tracking cumulative earnings, TDS withholdings, payouts, and bag recoveries.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <input
            type="text"
            placeholder="Filter by Partner ID (e.g. GP-018)..."
            value={partnerFilter}
            onChange={(e) => setPartnerFilter(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded px-3 py-1.5 text-xs text-white placeholder-slate-400 focus:outline-none w-56 font-mono"
          />

          <a
            href={api.downloadReportUrl('ledger.csv')}
            download="ledger.csv"
            className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-xs font-semibold flex items-center space-x-1.5 transition-colors shadow-sm"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Download ledger.csv</span>
          </a>
        </div>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs whitespace-nowrap">
            <thead className="bg-slate-800/80 text-slate-300 uppercase font-semibold tracking-wider border-b border-slate-700">
              <tr>
                <th className="py-2.5 px-3">Partner ID</th>
                <th className="py-2.5 px-3">Entry Timestamp (IST)</th>
                <th className="py-2.5 px-3">Entry Type</th>
                <th className="py-2.5 px-3">Week Start</th>
                <th className="py-2.5 px-3 text-right">Amount (₹)</th>
                <th className="py-2.5 px-3 text-right">Earned To Date</th>
                <th className="py-2.5 px-3 text-right">Withheld (TDS)</th>
                <th className="py-2.5 px-3 text-right">Paid To Date</th>
                <th className="py-2.5 px-3 text-right">Bag Recovered</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 text-slate-200 font-mono">
              {entries.length === 0 ? (
                <tr>
                  <td colSpan={9} className="text-center py-12 text-slate-500 font-sans">
                    {loading ? 'Loading ledger entries...' : 'No ledger entries posted yet.'}
                  </td>
                </tr>
              ) : (
                entries.map((l) => (
                  <tr key={l.id} className="hover:bg-slate-800/50 transition-colors">
                    <td className="py-2 px-3 font-bold text-emerald-400">{l.partner_id}</td>
                    <td className="py-2 px-3 text-slate-400 font-sans">{l.entry_ts}</td>
                    <td className="py-2 px-3 font-sans">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                        l.entry_type === 'EARNING' ? 'bg-blue-950 text-blue-300 border border-blue-800/60' :
                        l.entry_type === 'INCENTIVE' ? 'bg-emerald-950 text-emerald-300 border border-emerald-800/60' :
                        l.entry_type === 'PENALTY' ? 'bg-rose-950 text-rose-300 border border-rose-800/60' :
                        l.entry_type === 'TDS' ? 'bg-amber-950 text-amber-300 border border-amber-800/60' :
                        l.entry_type === 'PAYOUT' ? 'bg-purple-950 text-purple-300 border border-purple-800/60' :
                        l.entry_type === 'PAYOUT_RETURN' ? 'bg-rose-950 text-rose-300 border border-rose-800/60' :
                        'bg-slate-800 text-slate-300'
                      }`}>
                        {l.entry_type}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-slate-400">{l.week_start || '—'}</td>
                    <td className={`py-2 px-3 text-right font-bold ${
                      l.amount_rupees >= 0 ? 'text-emerald-400' : 'text-rose-400'
                    }`}>
                      {l.amount_rupees >= 0 ? '+' : ''}₹{l.amount_rupees.toFixed(2)}
                    </td>
                    <td className="py-2 px-3 text-right">₹{l.earned_to_date_rupees.toFixed(2)}</td>
                    <td className="py-2 px-3 text-right text-amber-400">₹{l.withheld_to_date_rupees.toFixed(2)}</td>
                    <td className="py-2 px-3 text-right text-emerald-400">₹{l.paid_to_date_rupees.toFixed(2)}</td>
                    <td className="py-2 px-3 text-right text-slate-300">₹{l.recovered_to_date_rupees.toFixed(2)}</td>
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

import React, { useState, useEffect } from 'react';
import { FileSpreadsheet, Download, Filter, Search } from 'lucide-react';
import { WeeklyStatement } from '../types';
import { api } from '../api';

export const StatementsTab: React.FC = () => {
  const [statements, setStatements] = useState<WeeklyStatement[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedWeek, setSelectedWeek] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');
  const [partnerSearch, setPartnerSearch] = useState('');

  const fetchStatements = async () => {
    try {
      setLoading(true);
      const data = await api.getStatements(selectedWeek || undefined, selectedStatus || undefined);
      setStatements(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatements();
  }, [selectedWeek, selectedStatus]);

  const filtered = statements.filter((s) => {
    if (!partnerSearch) return true;
    return s.partner_id.toLowerCase().includes(partnerSearch.toLowerCase());
  });

  const weekOptions = [
    '2026-09-07',
    '2026-09-14',
    '2026-09-21',
    '2026-09-28',
    '2026-10-05',
    '2026-10-12',
    '2026-10-19',
    '2026-10-26'
  ];

  return (
    <div className="space-y-4">
      {/* Filter and Download Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 shadow-sm flex flex-wrap gap-3 items-center justify-between">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center space-x-1.5 text-xs text-slate-300">
            <span className="font-semibold">Week Start:</span>
            <select
              value={selectedWeek}
              onChange={(e) => setSelectedWeek(e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded px-2.5 py-1.5 text-slate-200 text-xs focus:outline-none"
            >
              <option value="">All Weeks</option>
              {weekOptions.map((w) => (
                <option key={w} value={w}>{w}</option>
              ))}
            </select>
          </div>

          <div className="flex items-center space-x-1.5 text-xs text-slate-300">
            <span className="font-semibold">Status:</span>
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded px-2.5 py-1.5 text-slate-200 text-xs focus:outline-none"
            >
              <option value="">All Statuses</option>
              <option value="PAID">PAID</option>
              <option value="HELD_BANK">HELD_BANK</option>
              <option value="HELD_PAN">HELD_PAN</option>
              <option value="HELD_MANUAL">HELD_MANUAL</option>
              <option value="CARRIED_FORWARD">CARRIED_FORWARD</option>
              <option value="NO_ACTIVITY">NO_ACTIVITY</option>
            </select>
          </div>

          <div className="relative">
            <input
              type="text"
              placeholder="Search partner ID (GP-xxx)..."
              value={partnerSearch}
              onChange={(e) => setPartnerSearch(e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded px-3 py-1.5 text-xs text-white placeholder-slate-400 focus:outline-none w-48 font-mono"
            />
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <span className="text-xs text-slate-400 font-mono">
            {filtered.length} statements
          </span>
          <a
            href={api.downloadReportUrl('weekly_statements.csv')}
            download="weekly_statements.csv"
            className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-xs font-semibold flex items-center space-x-1.5 transition-colors shadow-sm"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Download CSV</span>
          </a>
        </div>
      </div>

      {/* Statements Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs whitespace-nowrap">
            <thead className="bg-slate-800/80 text-slate-300 uppercase font-semibold tracking-wider border-b border-slate-700">
              <tr>
                <th className="py-2.5 px-2.5">Partner</th>
                <th className="py-2.5 px-2.5">Week Start</th>
                <th className="py-2.5 px-2 text-center">Done</th>
                <th className="py-2.5 px-2 text-center">P-Can</th>
                <th className="py-2.5 px-2 text-center">C-Can</th>
                <th className="py-2.5 px-2 text-center">Cancel %</th>
                <th className="py-2.5 px-2 text-center">Rating</th>
                <th className="py-2.5 px-2.5 text-right">Task Earn</th>
                <th className="py-2.5 px-2.5 text-right">Incentive</th>
                <th className="py-2.5 px-2.5 text-right">Gross</th>
                <th className="py-2.5 px-2.5 text-right">Penalties</th>
                <th className="py-2.5 px-2.5 text-right">Adjust</th>
                <th className="py-2.5 px-2.5 text-right">TDS Base</th>
                <th className="py-2.5 px-2.5 text-center">TDS Sec / %</th>
                <th className="py-2.5 px-2.5 text-right">TDS</th>
                <th className="py-2.5 px-2.5 text-right">Bag Rec</th>
                <th className="py-2.5 px-2.5 text-right">Carry In</th>
                <th className="py-2.5 px-2.5 text-right font-bold text-white">Net Payable</th>
                <th className="py-2.5 px-2.5 text-center">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 text-slate-200 font-mono">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={19} className="text-center py-12 text-slate-500 font-sans">
                    {loading ? 'Loading statements...' : 'No weekly statements found. Run settlement batches to generate statements.'}
                  </td>
                </tr>
              ) : (
                filtered.map((s) => (
                  <tr key={s.id} className="hover:bg-slate-800/50 transition-colors">
                    <td className="py-2 px-2.5 font-bold text-emerald-400">{s.partner_id}</td>
                    <td className="py-2 px-2.5 text-slate-300">{s.week_start}</td>
                    <td className="py-2 px-2 text-center">{s.completed}</td>
                    <td className="py-2 px-2 text-center text-rose-400">{s.cancelled_by_partner}</td>
                    <td className="py-2 px-2 text-center text-amber-400">{s.cancelled_by_customer}</td>
                    <td className="py-2 px-2 text-center">
                      <span className={s.cancellation_rate_pct > 8 ? 'text-rose-400 font-bold' : 'text-slate-300'}>
                        {s.cancellation_rate_pct.toFixed(2)}%
                      </span>
                    </td>
                    <td className="py-2 px-2 text-center">{s.avg_rating.toFixed(2)}</td>
                    <td className="py-2 px-2.5 text-right">₹{s.task_earnings_rupees.toFixed(2)}</td>
                    <td className="py-2 px-2.5 text-right text-emerald-400">
                      {s.incentive_rupees > 0 ? `₹${s.incentive_rupees.toFixed(2)}` : '—'}
                    </td>
                    <td className="py-2 px-2.5 text-right font-medium text-white">₹{s.gross_rupees.toFixed(2)}</td>
                    <td className="py-2 px-2.5 text-right text-rose-400">
                      {s.penalties_rupees > 0 ? `-₹${s.penalties_rupees.toFixed(2)}` : '—'}
                    </td>
                    <td className="py-2 px-2.5 text-right text-slate-300">
                      {s.adjustments_rupees !== 0 ? `₹${s.adjustments_rupees.toFixed(2)}` : '—'}
                    </td>
                    <td className="py-2 px-2.5 text-right font-medium">₹{s.tds_base_rupees.toFixed(2)}</td>
                    <td className="py-2 px-2.5 text-center font-sans">
                      <span className="text-[11px] text-slate-300">
                        {s.tds_section} ({s.tds_rate_pct}%)
                      </span>
                    </td>
                    <td className="py-2 px-2.5 text-right text-amber-400">
                      {s.tds_rupees > 0 ? `₹${s.tds_rupees.toFixed(2)}` : '—'}
                    </td>
                    <td className="py-2 px-2.5 text-right text-slate-400">
                      {s.equipment_deduction_rupees > 0 ? `-₹${s.equipment_deduction_rupees.toFixed(2)}` : '—'}
                    </td>
                    <td className="py-2 px-2.5 text-right text-slate-400">
                      {s.carry_in_rupees > 0 ? `₹${s.carry_in_rupees.toFixed(2)}` : '—'}
                    </td>
                    <td className="py-2 px-2.5 text-right font-bold text-emerald-400">
                      ₹{s.net_payable_rupees.toFixed(2)}
                    </td>
                    <td className="py-2 px-2.5 text-center font-sans">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-semibold tracking-wide ${
                        s.status === 'PAID'
                          ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                          : s.status.startsWith('HELD')
                          ? 'bg-rose-950 text-rose-400 border border-rose-800'
                          : s.status === 'CARRIED_FORWARD'
                          ? 'bg-amber-950 text-amber-400 border border-amber-800'
                          : 'bg-slate-800 text-slate-400 border border-slate-700'
                      }`}>
                        {s.status}
                      </span>
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

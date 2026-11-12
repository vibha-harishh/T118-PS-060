import React, { useState, useEffect } from 'react';
import { Download, FileSpreadsheet, ShieldCheck } from 'lucide-react';
import { TDSSummaryRow } from '../types';
import { api } from '../api';

export const TdsTab: React.FC = () => {
  const [fy, setFy] = useState('2026-27');
  const [quarter, setQuarter] = useState('Q2');
  const [rows, setRows] = useState<TDSSummaryRow[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchTds = async () => {
    try {
      setLoading(true);
      const data = await api.getTdsSummary(fy, quarter);
      setRows(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTds();
  }, [fy, quarter]);

  return (
    <div className="space-y-4">
      {/* Controls Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 shadow-sm flex flex-wrap gap-3 items-center justify-between">
        <div>
          <h3 className="text-base font-semibold text-white flex items-center space-x-2">
            <ShieldCheck className="w-5 h-5 text-emerald-400" />
            <span>Form 26Q Quarterly TDS Summary</span>
          </h3>
          <p className="text-xs text-slate-400">
            Compliant quarterly tax statement summarizing partner payments and TDS withholdings under 194C, 194J, and 194-O.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-1.5 text-xs text-slate-300">
            <span className="font-semibold">FY:</span>
            <select
              value={fy}
              onChange={(e) => setFy(e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded px-2.5 py-1.5 text-slate-200 text-xs focus:outline-none"
            >
              <option value="2026-27">2026-27</option>
            </select>
          </div>

          <div className="flex items-center space-x-1.5 text-xs text-slate-300">
            <span className="font-semibold">Quarter:</span>
            <select
              value={quarter}
              onChange={(e) => setQuarter(e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded px-2.5 py-1.5 text-slate-200 text-xs focus:outline-none"
            >
              <option value="Q1">Q1 (Apr–Jun)</option>
              <option value="Q2">Q2 (Jul–Sep)</option>
              <option value="Q3">Q3 (Oct–Dec)</option>
              <option value="Q4">Q4 (Jan–Mar)</option>
            </select>
          </div>

          <a
            href={api.downloadReportUrl(`tds_summary_${quarter.toLowerCase()}.csv`)}
            download={`tds_summary_${fy}_${quarter}.csv`}
            className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-xs font-semibold flex items-center space-x-1.5 transition-colors shadow-sm"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Download Form 26Q CSV</span>
          </a>
        </div>
      </div>

      {/* TDS Summary Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs whitespace-nowrap">
            <thead className="bg-slate-800/80 text-slate-300 uppercase font-semibold tracking-wider border-b border-slate-700">
              <tr>
                <th className="py-2.5 px-3">FY</th>
                <th className="py-2.5 px-3 text-center">Quarter</th>
                <th className="py-2.5 px-3">Partner ID</th>
                <th className="py-2.5 px-3">PAN</th>
                <th className="py-2.5 px-3 text-center">Section</th>
                <th className="py-2.5 px-3 text-center">Rate (%)</th>
                <th className="py-2.5 px-3 text-right">Amount Paid (₹)</th>
                <th className="py-2.5 px-3 text-right">TDS Deducted (₹)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 text-slate-200 font-mono">
              {rows.length === 0 ? (
                <tr>
                  <td colSpan={8} className="text-center py-12 text-slate-500 font-sans">
                    {loading ? 'Loading quarterly summary...' : `No TDS withholdings recorded for ${fy} ${quarter}.`}
                  </td>
                </tr>
              ) : (
                rows.map((r, idx) => (
                  <tr key={idx} className="hover:bg-slate-800/50 transition-colors">
                    <td className="py-2 px-3 text-slate-300 font-sans">{r.fy}</td>
                    <td className="py-2 px-3 text-center text-slate-300 font-sans">{r.quarter}</td>
                    <td className="py-2 px-3 font-bold text-emerald-400">{r.partner_id}</td>
                    <td className="py-2 px-3 text-slate-300">{r.pan || '—'}</td>
                    <td className="py-2 px-3 text-center font-sans font-semibold text-indigo-400">
                      {r.section}
                    </td>
                    <td className="py-2 px-3 text-center">{r.rate_pct}%</td>
                    <td className="py-2 px-3 text-right font-medium">₹{r.amount_paid}</td>
                    <td className="py-2 px-3 text-right font-bold text-amber-400">₹{r.tds_deducted}</td>
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

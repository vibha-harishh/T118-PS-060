import React, { useEffect, useState } from 'react';
import { X, ShieldAlert, CheckCircle2, AlertCircle, Clock, CreditCard, DollarSign } from 'lucide-react';
import { Partner, WeeklyStatement, LedgerEntry } from '../types';
import { api } from '../api';

interface PartnerModalProps {
  partnerId: string;
  onClose: () => void;
  onPartnerUpdated: () => void;
}

export const PartnerModal: React.FC<PartnerModalProps> = ({ partnerId, onClose, onPartnerUpdated }) => {
  const [data, setData] = useState<{ partner: Partner; statements: WeeklyStatement[]; ledger: LedgerEntry[] } | null>(null);
  const [loading, setLoading] = useState(true);
  const [panInput, setPanInput] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  const fetchDetail = async () => {
    try {
      setLoading(true);
      const res = await api.getPartnerDetail(partnerId);
      setData(res);
      if (res.partner.pan) setPanInput(res.partner.pan);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetail();
  }, [partnerId]);

  const handleBankVerify = async () => {
    try {
      setActionLoading(true);
      await api.executeSingleCommand(`BANK_VERIFIED|${partnerId}|2026-10-07 15:00:00`);
      await fetchDetail();
      onPartnerUpdated();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handlePanUpdate = async () => {
    if (!panInput.trim()) return;
    try {
      setActionLoading(true);
      await api.executeSingleCommand(`PAN_UPDATE|${partnerId}|2026-09-30 14:20:00|${panInput.trim().toUpperCase()}`);
      await fetchDetail();
      onPartnerUpdated();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleToggleHold = async () => {
    if (!data) return;
    try {
      setActionLoading(true);
      if (data.partner.is_held_manual) {
        await api.executeSingleCommand(`RELEASE|${partnerId}|2026-10-25 16:00:00`);
      } else {
        await api.executeSingleCommand(`HOLD|${partnerId}|2026-10-16 16:00:00|KYC_REVIEW`);
      }
      await fetchDetail();
      onPartnerUpdated();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  if (!data && loading) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-xs">
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 text-white text-sm">
          Loading partner profile...
        </div>
      </div>
    );
  }

  if (!data) return null;
  const { partner, statements, ledger } = data;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-xs p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl text-white">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-slate-800">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-lg bg-emerald-700/80 flex items-center justify-center font-bold text-lg">
              {partner.partner_name.charAt(0)}
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="font-bold text-base">{partner.partner_name}</h3>
                <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-emerald-400 font-mono">
                  {partner.partner_id}
                </span>
                <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                  {partner.partner_type}
                </span>
                <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                  {partner.category}
                </span>
              </div>
              <p className="text-xs text-slate-400">
                City: {partner.city} • Onboarded: {partner.onboarding_date} • IFSC: {partner.ifsc}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-5 space-y-6">
          {/* Status & Quick Actions */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Bank status */}
            <div className="p-3 bg-slate-800/60 rounded-lg border border-slate-700/60">
              <div className="text-xs text-slate-400 mb-1">Bank Status</div>
              <div className="flex items-center justify-between">
                <span className={`text-xs font-semibold px-2 py-0.5 rounded ${
                  partner.bank_status === 'VERIFIED'
                    ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                    : 'bg-rose-950 text-rose-400 border border-rose-800'
                }`}>
                  {partner.bank_status}
                </span>
                {partner.bank_status === 'UNVERIFIED' && (
                  <button
                    onClick={handleBankVerify}
                    disabled={actionLoading}
                    className="text-xs px-2 py-1 bg-emerald-600 hover:bg-emerald-500 text-white rounded transition-colors disabled:opacity-50"
                  >
                    Verify Bank
                  </button>
                )}
              </div>
            </div>

            {/* PAN status */}
            <div className="p-3 bg-slate-800/60 rounded-lg border border-slate-700/60">
              <div className="text-xs text-slate-400 mb-1">PAN Status</div>
              <div className="flex items-center space-x-2">
                <span className={`text-xs font-semibold px-2 py-0.5 rounded ${
                  partner.pan_status === 'VALID'
                    ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                    : 'bg-amber-950 text-amber-400 border border-amber-800'
                }`}>
                  {partner.pan_status}
                </span>
                <input
                  type="text"
                  value={panInput}
                  onChange={(e) => setPanInput(e.target.value)}
                  placeholder="Enter PAN"
                  className="bg-slate-900 border border-slate-700 rounded px-2 py-0.5 text-xs text-white uppercase font-mono w-28"
                />
                <button
                  onClick={handlePanUpdate}
                  disabled={actionLoading || !panInput.trim()}
                  className="text-xs px-2 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded transition-colors disabled:opacity-50"
                >
                  Save
                </button>
              </div>
            </div>

            {/* Hold status */}
            <div className="p-3 bg-slate-800/60 rounded-lg border border-slate-700/60">
              <div className="text-xs text-slate-400 mb-1">Manual Hold / KYC</div>
              <div className="flex items-center justify-between">
                <span className={`text-xs font-semibold px-2 py-0.5 rounded ${
                  partner.is_held_manual
                    ? 'bg-rose-950 text-rose-400 border border-rose-800'
                    : 'bg-slate-800 text-slate-300'
                }`}>
                  {partner.is_held_manual ? (partner.manual_hold_reason || 'HELD') : 'ACTIVE'}
                </span>
                <button
                  onClick={handleToggleHold}
                  disabled={actionLoading}
                  className={`text-xs px-2 py-1 rounded transition-colors disabled:opacity-50 ${
                    partner.is_held_manual
                      ? 'bg-emerald-600 hover:bg-emerald-500 text-white'
                      : 'bg-rose-600 hover:bg-rose-500 text-white'
                  }`}
                >
                  {partner.is_held_manual ? 'Release Hold' : 'Apply Hold'}
                </button>
              </div>
            </div>
          </div>

          {/* Financial Balances */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-800/40 p-3 rounded-lg border border-slate-800">
            <div>
              <div className="text-xs text-slate-400">FY Paid Before</div>
              <div className="text-sm font-semibold font-mono text-slate-200">
                ₹{partner.fy_paid_before_rupees.toFixed(2)}
              </div>
            </div>
            <div>
              <div className="text-xs text-slate-400">FY TDS Before</div>
              <div className="text-sm font-semibold font-mono text-slate-200">
                ₹{partner.fy_tds_before_rupees.toFixed(2)}
              </div>
            </div>
            <div>
              <div className="text-xs text-slate-400">Bag Recovered Before</div>
              <div className="text-sm font-semibold font-mono text-slate-200">
                ₹{partner.equipment_recovered_rupees.toFixed(2)} / ₹1800
              </div>
            </div>
            <div>
              <div className="text-xs text-slate-400">Bank Retries</div>
              <div className="text-sm font-semibold font-mono text-slate-200">
                {partner.bank_retry_count} / 2
              </div>
            </div>
          </div>

          {/* Weekly Statements */}
          <div>
            <h4 className="text-sm font-semibold text-slate-200 mb-2">Weekly Statements History</h4>
            {statements.length === 0 ? (
              <p className="text-xs text-slate-500 py-3">No settlement statements processed yet.</p>
            ) : (
              <div className="overflow-x-auto border border-slate-800 rounded-lg">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-800 text-slate-300 font-medium">
                    <tr>
                      <th className="p-2">Week Start</th>
                      <th className="p-2">Completed</th>
                      <th className="p-2">Gross (₹)</th>
                      <th className="p-2">Incentive</th>
                      <th className="p-2">Penalties</th>
                      <th className="p-2">TDS Base</th>
                      <th className="p-2">TDS Sec / %</th>
                      <th className="p-2">TDS (₹)</th>
                      <th className="p-2">Net Payable</th>
                      <th className="p-2">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800 font-mono">
                    {statements.map((s) => (
                      <tr key={s.id} className="hover:bg-slate-800/40">
                        <td className="p-2">{s.week_start}</td>
                        <td className="p-2">{s.completed}</td>
                        <td className="p-2">₹{s.gross_rupees.toFixed(2)}</td>
                        <td className="p-2">₹{s.incentive_rupees.toFixed(2)}</td>
                        <td className="p-2 text-rose-400">₹{s.penalties_rupees.toFixed(2)}</td>
                        <td className="p-2">₹{s.tds_base_rupees.toFixed(2)}</td>
                        <td className="p-2">{s.tds_section} ({s.tds_rate_pct}%)</td>
                        <td className="p-2 text-amber-400">₹{s.tds_rupees.toFixed(2)}</td>
                        <td className="p-2 font-bold text-emerald-400">₹{s.net_payable_rupees.toFixed(2)}</td>
                        <td className="p-2">
                          <span className={`px-1.5 py-0.5 rounded text-[10px] font-sans ${
                            s.status === 'PAID' ? 'bg-emerald-950 text-emerald-400' :
                            s.status.startsWith('HELD') ? 'bg-rose-950 text-rose-400' :
                            s.status === 'CARRIED_FORWARD' ? 'bg-amber-950 text-amber-400' :
                            'bg-slate-800 text-slate-400'
                          }`}>
                            {s.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Running Ledger Entries */}
          <div>
            <h4 className="text-sm font-semibold text-slate-200 mb-2">Partner Ledger Entries</h4>
            {ledger.length === 0 ? (
              <p className="text-xs text-slate-500 py-3">No ledger entries posted yet.</p>
            ) : (
              <div className="overflow-x-auto border border-slate-800 rounded-lg max-h-56">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-800 text-slate-300 font-medium sticky top-0">
                    <tr>
                      <th className="p-2">Timestamp</th>
                      <th className="p-2">Type</th>
                      <th className="p-2">Week</th>
                      <th className="p-2">Amount (₹)</th>
                      <th className="p-2">Earned to Date</th>
                      <th className="p-2">TDS Withheld</th>
                      <th className="p-2">Paid to Date</th>
                      <th className="p-2">Bag Recovered</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800 font-mono">
                    {ledger.map((l) => (
                      <tr key={l.id} className="hover:bg-slate-800/40">
                        <td className="p-2 text-slate-400">{l.entry_ts}</td>
                        <td className="p-2 font-sans font-semibold text-slate-300">{l.entry_type}</td>
                        <td className="p-2 text-slate-400">{l.week_start || '-'}</td>
                        <td className={`p-2 font-bold ${l.amount_rupees >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                          {l.amount_rupees >= 0 ? '+' : ''}₹{l.amount_rupees.toFixed(2)}
                        </td>
                        <td className="p-2">₹{l.earned_to_date_rupees.toFixed(2)}</td>
                        <td className="p-2 text-amber-400">₹{l.withheld_to_date_rupees.toFixed(2)}</td>
                        <td className="p-2 text-emerald-400">₹{l.paid_to_date_rupees.toFixed(2)}</td>
                        <td className="p-2">₹{l.recovered_to_date_rupees.toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-800 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs rounded transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

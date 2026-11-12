import React, { useState, useEffect } from 'react';
import { Search, Filter, ShieldAlert, CheckCircle2, AlertTriangle, AlertCircle, Eye, UserCheck } from 'lucide-react';
import { Partner } from '../types';
import { api } from '../api';
import { PartnerModal } from './PartnerModal';

interface PartnersTabProps {
  onRefresh: () => void;
}

export const PartnersTab: React.FC<PartnersTabProps> = ({ onRefresh }) => {
  const [partners, setPartners] = useState<Partner[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [panFilter, setPanFilter] = useState('');
  const [bankFilter, setBankFilter] = useState('');
  const [selectedPartnerId, setSelectedPartnerId] = useState<string | null>(null);

  const fetchPartners = async () => {
    try {
      setLoading(true);
      const data = await api.getPartners();
      setPartners(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPartners();
  }, []);

  const filteredPartners = partners.filter((p) => {
    const matchesSearch =
      p.partner_id.toLowerCase().includes(search.toLowerCase()) ||
      p.partner_name.toLowerCase().includes(search.toLowerCase()) ||
      (p.pan && p.pan.toLowerCase().includes(search.toLowerCase()));

    const matchesCat = !categoryFilter || p.category === categoryFilter;
    const matchesType = !typeFilter || p.partner_type === typeFilter;
    const matchesPan = !panFilter || p.pan_status === panFilter;
    const matchesBank = !bankFilter || p.bank_status === bankFilter;

    return matchesSearch && matchesCat && matchesType && matchesPan && matchesBank;
  });

  return (
    <div className="space-y-4">
      {/* Search and Filters Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 shadow-sm flex flex-wrap gap-3 items-center justify-between">
        <div className="flex items-center space-x-2 flex-1 min-w-[240px]">
          <div className="relative w-full max-w-sm">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search partner ID, name, PAN..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-md pl-9 pr-3 py-1.5 text-xs text-white placeholder-slate-400 focus:outline-none focus:border-emerald-500"
            />
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 text-xs">
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded-md px-2.5 py-1.5 text-slate-300 focus:outline-none"
          >
            <option value="">All Categories</option>
            <option value="DELIVERY">Delivery (194C)</option>
            <option value="SERVICE_PROFESSIONAL">Service Professional (194J)</option>
          </select>

          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded-md px-2.5 py-1.5 text-slate-300 focus:outline-none"
          >
            <option value="">All Types</option>
            <option value="INDIVIDUAL">Individual</option>
            <option value="FIRM">Firm</option>
          </select>

          <select
            value={panFilter}
            onChange={(e) => setPanFilter(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded-md px-2.5 py-1.5 text-slate-300 focus:outline-none"
          >
            <option value="">All PAN Status</option>
            <option value="VALID">Valid PAN</option>
            <option value="INVALID">Invalid PAN (20%)</option>
            <option value="MISSING">Missing PAN</option>
          </select>

          <select
            value={bankFilter}
            onChange={(e) => setBankFilter(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded-md px-2.5 py-1.5 text-slate-300 focus:outline-none"
          >
            <option value="">All Bank Status</option>
            <option value="VERIFIED">Verified</option>
            <option value="UNVERIFIED">Unverified (Held)</option>
          </select>

          <span className="text-slate-400 font-mono ml-2">
            Showing {filteredPartners.length} of {partners.length}
          </span>
        </div>
      </div>

      {/* Partners Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-800/80 text-slate-300 uppercase font-semibold tracking-wider border-b border-slate-700">
              <tr>
                <th className="py-3 px-3">Partner ID</th>
                <th className="py-3 px-3">Name</th>
                <th className="py-3 px-3">Type</th>
                <th className="py-3 px-3">Category</th>
                <th className="py-3 px-3">PAN & Status</th>
                <th className="py-3 px-3">Bank Status</th>
                <th className="py-3 px-3">City</th>
                <th className="py-3 px-3 text-right">FY Paid Before</th>
                <th className="py-3 px-3 text-right">Bag Recovered</th>
                <th className="py-3 px-3 text-center">Hold Status</th>
                <th className="py-3 px-3 text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 text-slate-200">
              {filteredPartners.length === 0 ? (
                <tr>
                  <td colSpan={11} className="text-center py-8 text-slate-500">
                    {loading ? 'Loading partners...' : 'No partners found matching filters.'}
                  </td>
                </tr>
              ) : (
                filteredPartners.map((p) => (
                  <tr
                    key={p.partner_id}
                    className="hover:bg-slate-800/50 cursor-pointer transition-colors"
                    onClick={() => setSelectedPartnerId(p.partner_id)}
                  >
                    <td className="py-2.5 px-3 font-mono font-bold text-emerald-400">
                      {p.partner_id}
                    </td>
                    <td className="py-2.5 px-3 font-medium text-white">{p.partner_name}</td>
                    <td className="py-2.5 px-3">
                      <span className={`px-2 py-0.5 rounded text-[11px] ${
                        p.partner_type === 'INDIVIDUAL'
                          ? 'bg-blue-950/60 text-blue-300 border border-blue-800/60'
                          : 'bg-purple-950/60 text-purple-300 border border-purple-800/60'
                      }`}>
                        {p.partner_type}
                      </span>
                    </td>
                    <td className="py-2.5 px-3">
                      <span className="text-slate-300">
                        {p.category === 'DELIVERY' ? 'Delivery (194C)' : 'Service Prof (194J)'}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 font-mono">
                      <div className="flex items-center space-x-1.5">
                        <span className="text-slate-300">{p.pan || '—'}</span>
                        <span className={`px-1.5 py-0.2 rounded text-[10px] ${
                          p.pan_status === 'VALID'
                            ? 'bg-emerald-950 text-emerald-400'
                            : p.pan_status === 'INVALID'
                            ? 'bg-rose-950 text-rose-400'
                            : 'bg-amber-950 text-amber-400'
                        }`}>
                          {p.pan_status}
                        </span>
                      </div>
                    </td>
                    <td className="py-2.5 px-3">
                      <span className={`px-2 py-0.5 rounded text-[11px] ${
                        p.bank_status === 'VERIFIED'
                          ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-800/60'
                          : 'bg-rose-950/60 text-rose-400 border border-rose-800/60'
                      }`}>
                        {p.bank_status}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-slate-300">{p.city}</td>
                    <td className="py-2.5 px-3 text-right font-mono">
                      ₹{p.fy_paid_before_rupees.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono text-slate-300">
                      ₹{p.equipment_recovered_rupees.toFixed(2)} / ₹1800
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      {p.is_held_manual ? (
                        <span className="px-1.5 py-0.5 rounded bg-rose-950 text-rose-400 text-[10px] border border-rose-800">
                          {p.manual_hold_reason || 'HELD_MANUAL'}
                        </span>
                      ) : p.bank_status === 'UNVERIFIED' ? (
                        <span className="px-1.5 py-0.5 rounded bg-rose-950 text-rose-400 text-[10px] border border-rose-800">
                          HELD_BANK
                        </span>
                      ) : (
                        <span className="text-emerald-400 text-[11px]">ACTIVE</span>
                      )}
                    </td>
                    <td className="py-2.5 px-3 text-center" onClick={(e) => e.stopPropagation()}>
                      <button
                        onClick={() => setSelectedPartnerId(p.partner_id)}
                        className="p-1 hover:bg-slate-700 rounded text-slate-400 hover:text-white transition-colors"
                        title="View partner profile & ledger"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {selectedPartnerId && (
        <PartnerModal
          partnerId={selectedPartnerId}
          onClose={() => setSelectedPartnerId(null)}
          onPartnerUpdated={() => {
            fetchPartners();
            onRefresh();
          }}
        />
      )}
    </div>
  );
};

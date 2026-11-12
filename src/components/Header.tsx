import React from 'react';
import { Database, ShieldCheck, ShoppingCart, RefreshCw, Layers } from 'lucide-react';
import { SystemStatus } from '../types';

interface HeaderProps {
  status: SystemStatus | null;
  activeTab: string;
  setActiveTab: (tab: string) => void;
  onRefresh: () => void;
  loading: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  status,
  activeTab,
  setActiveTab,
  onRefresh,
  loading
}) => {
  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'datasets', label: 'Datasets & Ingestion' },
    { id: 'partners', label: 'Partners' },
    { id: 'tasks', label: 'Tasks' },
    { id: 'batches', label: 'Settlement Batches' },
    { id: 'statements', label: 'Weekly Statements' },
    { id: 'ledger', label: 'Partner Ledger' },
    { id: 'tds', label: 'Form 26Q TDS' },
    { id: 'commands', label: 'Command Console' },
    { id: 'edge_cases', label: 'Edge Case Verification' },
  ];

  return (
    <header className="bg-slate-900 border-b border-slate-800 text-white sticky top-0 z-30 shadow-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center space-x-3">
            <div className="h-10 w-10 rounded-lg bg-emerald-600 flex items-center justify-center font-bold text-lg shadow-inner">
              ₹
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold text-lg tracking-tight text-slate-100">
                  GigWorker Payout Engine
                </span>
                <span className="text-xs px-2 py-0.5 rounded font-mono bg-slate-800 text-emerald-400 border border-slate-700">
                  T118-PS-060
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Weekly Settlement • TDS (194C / 194J / 194-O) • Partner Ledger
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            {/* Database indicator */}
            <div className="flex items-center space-x-1.5 px-3 py-1 rounded-md bg-slate-800/80 border border-slate-700 text-xs">
              <Database className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-slate-300">SQLite:</span>
              <span className="font-mono text-emerald-400">Connected</span>
            </div>

            {/* Marketplace indicator */}
            <div className={`flex items-center space-x-1.5 px-3 py-1 rounded-md border text-xs ${
              status?.marketplace_mode
                ? 'bg-amber-950/40 border-amber-800/60 text-amber-300'
                : 'bg-indigo-950/40 border-indigo-800/60 text-indigo-300'
            }`}>
              <ShoppingCart className="w-3.5 h-3.5" />
              <span>
                {status?.marketplace_mode ? '194-O (Marketplace)' : '194C / 194J (Standard)'}
              </span>
            </div>

            <button
              onClick={onRefresh}
              disabled={loading}
              title="Refresh all metrics from backend"
              className="p-1.5 rounded-md hover:bg-slate-800 text-slate-300 hover:text-white transition-colors border border-slate-700"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {/* Tab navigation */}
        <nav className="flex space-x-1 overflow-x-auto py-2 border-t border-slate-800/60 text-xs font-medium scrollbar-none">
          {tabs.map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-3 py-1.5 rounded-md whitespace-nowrap transition-colors ${
                  isActive
                    ? 'bg-emerald-600 text-white font-semibold shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                }`}
              >
                {tab.label}
              </button>
            );
          })}
        </nav>
      </div>
    </header>
  );
};

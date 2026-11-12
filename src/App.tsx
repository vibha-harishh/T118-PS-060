import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { OverviewTab } from './components/OverviewTab';
import { DatasetsTab } from './components/DatasetsTab';
import { PartnersTab } from './components/PartnersTab';
import { TasksTab } from './components/TasksTab';
import { BatchesTab } from './components/BatchesTab';
import { StatementsTab } from './components/StatementsTab';
import { LedgerTab } from './components/LedgerTab';
import { TdsTab } from './components/TdsTab';
import { CommandsTab } from './components/CommandsTab';
import { EdgeCasesTab } from './components/EdgeCasesTab';
import { SystemStatus } from './types';
import { api } from './api';
import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState('overview');
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [banner, setBanner] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  const fetchStatus = async () => {
    try {
      setLoading(true);
      const data = await api.getStatus();
      setStatus(data);
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <Header
        status={status}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onRefresh={fetchStatus}
        loading={loading}
      />

      {/* Global Notification Banner */}
      {banner && (
        <div className={`py-2.5 px-4 text-xs flex items-center justify-between border-b ${
          banner.type === 'success'
            ? 'bg-emerald-950/80 text-emerald-300 border-emerald-800'
            : banner.type === 'error'
            ? 'bg-rose-950/80 text-rose-300 border-rose-800'
            : 'bg-blue-950/80 text-blue-300 border-blue-800'
        }`}>
          <div className="flex items-center space-x-2 max-w-5xl mx-auto flex-1">
            {banner.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            ) : banner.type === 'error' ? (
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
            ) : (
              <Info className="w-4 h-4 text-blue-400 shrink-0" />
            )}
            <span className="font-medium">{banner.text}</span>
          </div>
          <button
            onClick={() => setBanner(null)}
            className="p-1 hover:bg-black/20 rounded transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {activeTab === 'overview' && (
          <OverviewTab
            status={status}
            onRefresh={fetchStatus}
            setActiveTab={setActiveTab}
            setBannerMessage={setBanner}
          />
        )}
        {activeTab === 'datasets' && (
          <DatasetsTab
            onRefresh={fetchStatus}
            setBannerMessage={setBanner}
          />
        )}
        {activeTab === 'partners' && <PartnersTab onRefresh={fetchStatus} />}
        {activeTab === 'tasks' && <TasksTab onRefresh={fetchStatus} />}
        {activeTab === 'batches' && (
          <BatchesTab
            onRefresh={fetchStatus}
            setBannerMessage={setBanner}
          />
        )}
        {activeTab === 'statements' && <StatementsTab />}
        {activeTab === 'ledger' && <LedgerTab />}
        {activeTab === 'tds' && <TdsTab />}
        {activeTab === 'commands' && (
          <CommandsTab
            onRefresh={fetchStatus}
            setBannerMessage={setBanner}
          />
        )}
        {activeTab === 'edge_cases' && <EdgeCasesTab />}
      </main>

      {/* Engineering Footer */}
      <footer className="border-t border-slate-900 bg-slate-950 py-4 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>Project T118-PS-060: Contractor &amp; Gig-Worker Payout Engine</span>
          <span className="font-mono text-slate-600">
            Python 3.10 • SQLite (payout_engine.db) • React SPA
          </span>
        </div>
      </footer>
    </div>
  );
}

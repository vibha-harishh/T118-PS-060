import React from 'react';
import {
  Users,
  Calendar,
  CheckCircle2,
  AlertCircle,
  FileSpreadsheet,
  Download,
  Play,
  RotateCcw,
  ShieldCheck,
  Percent,
  Clock,
  Layers
} from 'lucide-react';
import { SystemStatus } from '../types';
import { api } from '../api';

interface OverviewTabProps {
  status: SystemStatus | null;
  onRefresh: () => void;
  setActiveTab: (tab: string) => void;
  setBannerMessage: (msg: { text: string; type: 'success' | 'error' | 'info' } | null) => void;
}

export const OverviewTab: React.FC<OverviewTabProps> = ({
  status,
  onRefresh,
  setActiveTab,
  setBannerMessage
}) => {
  const [loading, setLoading] = React.useState(false);

  const handleIngestPreloaded = async () => {
    try {
      setLoading(true);
      const res = await api.ingestPreloaded();
      setBannerMessage({
        text: `Successfully ingested ${res.partners.successful} partners and ${res.slots.successful} delivery slots!`,
        type: 'success'
      });
      onRefresh();
    } catch (err: any) {
      setBannerMessage({ text: err.message, type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const handleExecutePreloadedCommands = async () => {
    try {
      setLoading(true);
      const res = await api.executePreloadedCommands();
      setBannerMessage({
        text: `Processed ${res.total_executed} commands from commands.txt (Batches, Adjustments, Holds, Returns)!`,
        type: 'success'
      });
      onRefresh();
    } catch (err: any) {
      setBannerMessage({ text: err.message, type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const handleResetDb = async () => {
    if (!confirm('Are you sure you want to re-initialize the database schema? All ingested data will be cleared.')) return;
    try {
      setLoading(true);
      await api.initDb(true);
      setBannerMessage({ text: 'Database reset successfully.', type: 'info' });
      onRefresh();
    } catch (err: any) {
      setBannerMessage({ text: err.message, type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-xs uppercase font-medium tracking-wider">Partners</span>
            <Users className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-white font-mono">{status?.partners_count ?? 0}</div>
          <div className="text-xs text-slate-400 mt-1">Delivery & Services</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-xs uppercase font-medium tracking-wider">Slots</span>
            <Calendar className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-2xl font-bold text-white font-mono">{status?.slots_count ?? 0}</div>
          <div className="text-xs text-slate-400 mt-1">Surge & Rain slots</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-xs uppercase font-medium tracking-wider">Task Events</span>
            <Layers className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-2xl font-bold text-white font-mono">{status?.tasks_count ?? 0}</div>
          <div className="text-xs text-slate-400 mt-1">Completed / Cancelled</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-xs uppercase font-medium tracking-wider">Settlement Batches</span>
            <Clock className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-white font-mono">{status?.batches_count ?? 0}</div>
          <div className="text-xs text-slate-400 mt-1">Monday runs</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-xs uppercase font-medium tracking-wider">Statements</span>
            <FileSpreadsheet className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-2xl font-bold text-white font-mono">{status?.statements_count ?? 0}</div>
          <div className="text-xs text-slate-400 mt-1">Weekly statements</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-xs uppercase font-medium tracking-wider">Ledger Entries</span>
            <Percent className="w-4 h-4 text-rose-400" />
          </div>
          <div className="text-2xl font-bold text-white font-mono">{status?.ledger_count ?? 0}</div>
          <div className="text-xs text-slate-400 mt-1">Immutable audit trail</div>
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Quick Actions & Ingestion */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 shadow-sm">
            <h3 className="text-base font-semibold text-white mb-2 flex items-center space-x-2">
              <ShieldCheck className="w-5 h-5 text-emerald-400" />
              <span>Official Dataset Pack Integration</span>
            </h3>
            <p className="text-sm text-slate-400 mb-4 leading-relaxed">
              Based on the capstone specification, the engine uses strictly supplied datasets without fake or invented records.
              The sample data pack contains 50 partners, 560 delivery slots, and 159 settlement/hold/adjustment commands.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
              <div className="p-3 bg-slate-800/60 rounded-md border border-slate-700/60">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-300">partners.csv (50 partners)</span>
                  {status?.partners_count && status.partners_count > 0 ? (
                    <span className="text-xs px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">Loaded</span>
                  ) : (
                    <span className="text-xs px-2 py-0.5 rounded bg-slate-700 text-slate-400">Ready</span>
                  )}
                </div>
                <div className="text-xs text-slate-400 mt-1">Delivery / Service, PAN & Bank Status</div>
              </div>

              <div className="p-3 bg-slate-800/60 rounded-md border border-slate-700/60">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-300">slots.csv (560 slots)</span>
                  {status?.slots_count && status.slots_count > 0 ? (
                    <span className="text-xs px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">Loaded</span>
                  ) : (
                    <span className="text-xs px-2 py-0.5 rounded bg-slate-700 text-slate-400">Ready</span>
                  )}
                </div>
                <div className="text-xs text-slate-400 mt-1">Bengaluru & Hyderabad slots (Surge/Rain)</div>
              </div>

              <div className="p-3 bg-slate-800/60 rounded-md border border-slate-700/60">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-300">commands.txt (159 lines)</span>
                  {status?.batches_count && status.batches_count > 0 ? (
                    <span className="text-xs px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">Executed</span>
                  ) : (
                    <span className="text-xs px-2 py-0.5 rounded bg-slate-700 text-slate-400">Ready</span>
                  )}
                </div>
                <div className="text-xs text-slate-400 mt-1">Batches, Holds, Bank Returns, Adjustments</div>
              </div>

              <div className="p-3 bg-slate-800/60 rounded-md border border-slate-700/60">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-300">task_events.csv</span>
                  {status?.tasks_count && status.tasks_count > 0 ? (
                    <span className="text-xs px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">{status.tasks_count} Rows</span>
                  ) : (
                    <span className="text-xs px-2 py-0.5 rounded bg-amber-950 text-amber-400 border border-amber-800">Upload in Datasets tab</span>
                  )}
                </div>
                <div className="text-xs text-slate-400 mt-1">Awaiting evaluation / task events upload</div>
              </div>
            </div>

            <div className="flex flex-wrap gap-3 pt-2">
              <button
                onClick={handleIngestPreloaded}
                disabled={loading}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-md font-medium text-xs flex items-center space-x-2 transition-colors shadow-sm disabled:opacity-50"
              >
                <Play className="w-4 h-4" />
                <span>Ingest Preloaded Partners & Slots</span>
              </button>

              <button
                onClick={handleExecutePreloadedCommands}
                disabled={loading}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-md font-medium text-xs flex items-center space-x-2 transition-colors shadow-sm disabled:opacity-50"
              >
                <Play className="w-4 h-4" />
                <span>Execute commands.txt Batch Script</span>
              </button>

              <button
                onClick={() => setActiveTab('datasets')}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-md font-medium text-xs border border-slate-700 transition-colors"
              >
                Upload Task Events CSV
              </button>

              <button
                onClick={handleResetDb}
                disabled={loading}
                className="px-3 py-2 bg-rose-950/40 hover:bg-rose-900/60 text-rose-300 border border-rose-800/50 rounded-md text-xs flex items-center space-x-1.5 transition-colors disabled:opacity-50"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Reset Database</span>
              </button>
            </div>
          </div>

          {/* Business Rules Architecture Card */}
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 shadow-sm">
            <h3 className="text-base font-semibold text-white mb-3">
              Engine Architecture & Business Rule Implementation
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-slate-300">
              <div className="space-y-2 border-l-2 border-emerald-500 pl-3">
                <div className="font-semibold text-slate-200">1. Financial Correctness in Python</div>
                <p className="text-slate-400">
                  All calculations happen exclusively in Python 3.10 using Decimal and integer paise.
                  Never duplicates monetary calculations in JavaScript.
                </p>
              </div>

              <div className="space-y-2 border-l-2 border-blue-500 pl-3">
                <div className="font-semibold text-slate-200">2. Earnings & Multipliers</div>
                <p className="text-slate-400">
                  Base ₹25 + ₹6/km beyond 3km. Surge x1.3, Rain x1.5 (higher applies, never stacks).
                  Customer cancel after pickup = ₹20. Rounded half-up to rupee.
                </p>
              </div>

              <div className="space-y-2 border-l-2 border-purple-500 pl-3">
                <div className="font-semibold text-slate-200">3. Incentives & 20% Penalty Cap</div>
                <p className="text-slate-400">
                  60 tasks = ₹600, 90 = ₹1,200, 120 = ₹2,000. Forfeit if cancellation rate &gt; 8% or rating &lt; 4.2.
                  Penalties capped at 20% of gross.
                </p>
              </div>

              <div className="space-y-2 border-l-2 border-amber-500 pl-3">
                <div className="font-semibold text-slate-200">4. TDS (194C / 194J / 194-O) & Holds</div>
                <p className="text-slate-400">
                  194C: 1% ind / 2% firm (&gt; ₹30k single or &gt; ₹1L annual). 194J: 10% (&gt; ₹30k). 194-O: 1% (&gt; ₹5L ind, 0 firm).
                  Missing PAN &gt; ₹50k holds payout.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Download Evaluation CSVs */}
        <div className="space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 shadow-sm">
            <h3 className="text-base font-semibold text-white mb-2 flex items-center space-x-2">
              <Download className="w-4 h-4 text-emerald-400" />
              <span>Evaluation CSV Outputs</span>
            </h3>
            <p className="text-xs text-slate-400 mb-4">
              Download the exact CSV formats specified in the sample pack specification:
            </p>

            <div className="space-y-2.5">
              <a
                href={api.downloadReportUrl('weekly_statements.csv')}
                download="weekly_statements.csv"
                className="w-full flex items-center justify-between p-3 rounded-md bg-slate-800/80 hover:bg-slate-800 border border-slate-700 text-xs text-slate-200 font-medium transition-colors"
              >
                <div className="flex items-center space-x-2">
                  <FileSpreadsheet className="w-4 h-4 text-emerald-400" />
                  <span>weekly_statements.csv</span>
                </div>
                <Download className="w-3.5 h-3.5 text-slate-400" />
              </a>

              <a
                href={api.downloadReportUrl('batch_summary.csv')}
                download="batch_summary.csv"
                className="w-full flex items-center justify-between p-3 rounded-md bg-slate-800/80 hover:bg-slate-800 border border-slate-700 text-xs text-slate-200 font-medium transition-colors"
              >
                <div className="flex items-center space-x-2">
                  <FileSpreadsheet className="w-4 h-4 text-blue-400" />
                  <span>batch_summary.csv</span>
                </div>
                <Download className="w-3.5 h-3.5 text-slate-400" />
              </a>

              <a
                href={api.downloadReportUrl('ledger.csv')}
                download="ledger.csv"
                className="w-full flex items-center justify-between p-3 rounded-md bg-slate-800/80 hover:bg-slate-800 border border-slate-700 text-xs text-slate-200 font-medium transition-colors"
              >
                <div className="flex items-center space-x-2">
                  <FileSpreadsheet className="w-4 h-4 text-purple-400" />
                  <span>ledger.csv</span>
                </div>
                <Download className="w-3.5 h-3.5 text-slate-400" />
              </a>

              <a
                href={api.downloadReportUrl('tds_summary_q2.csv')}
                download="tds_summary_2026-27_Q2.csv"
                className="w-full flex items-center justify-between p-3 rounded-md bg-slate-800/80 hover:bg-slate-800 border border-slate-700 text-xs text-slate-200 font-medium transition-colors"
              >
                <div className="flex items-center space-x-2">
                  <FileSpreadsheet className="w-4 h-4 text-amber-400" />
                  <span>tds_summary (Q2).csv</span>
                </div>
                <Download className="w-3.5 h-3.5 text-slate-400" />
              </a>

              <a
                href={api.downloadReportUrl('tds_summary_q3.csv')}
                download="tds_summary_2026-27_Q3.csv"
                className="w-full flex items-center justify-between p-3 rounded-md bg-slate-800/80 hover:bg-slate-800 border border-slate-700 text-xs text-slate-200 font-medium transition-colors"
              >
                <div className="flex items-center space-x-2">
                  <FileSpreadsheet className="w-4 h-4 text-amber-400" />
                  <span>tds_summary (Q3).csv</span>
                </div>
                <Download className="w-3.5 h-3.5 text-slate-400" />
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

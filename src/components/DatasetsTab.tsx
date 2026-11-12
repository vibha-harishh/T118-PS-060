import React, { useState } from 'react';
import { Upload, FileText, CheckCircle2, AlertTriangle, AlertCircle, RefreshCw } from 'lucide-react';
import { api } from '../api';

interface DatasetsTabProps {
  onRefresh: () => void;
  setBannerMessage: (msg: { text: string; type: 'success' | 'error' | 'info' } | null) => void;
}

export const DatasetsTab: React.FC<DatasetsTabProps> = ({ onRefresh, setBannerMessage }) => {
  const [loading, setLoading] = useState<string | null>(null);
  const [results, setResults] = useState<{ [key: string]: any }>({});

  const handleFileUpload = async (type: 'partners' | 'slots' | 'tasks' | 'commands', file: File) => {
    try {
      setLoading(type);
      const text = await file.text();
      let res: any;
      if (type === 'partners') {
        res = await api.ingestPartnersCsv(text);
      } else if (type === 'slots') {
        res = await api.ingestSlotsCsv(text);
      } else if (type === 'tasks') {
        res = await api.ingestTasksCsv(text);
      } else if (type === 'commands') {
        res = await api.executeCommandsScript(text);
      }

      setResults((prev) => ({ ...prev, [type]: res }));
      setBannerMessage({
        text: `Successfully processed ${file.name} (${type})!`,
        type: 'success'
      });
      onRefresh();
    } catch (err: any) {
      setResults((prev) => ({ ...prev, [type]: { error: err.message } }));
      setBannerMessage({ text: err.message, type: 'error' });
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-white mb-1">Dataset Upload & Ingestion</h2>
        <p className="text-xs text-slate-400 mb-6">
          Upload official CSV and command files. The engine strictly processes provided records without generating fake or random data.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* 1. Partners CSV */}
          <div className="p-4 rounded-lg bg-slate-800/60 border border-slate-700/80 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="font-semibold text-sm text-slate-200">1. Partners Dataset</span>
                <span className="text-xs px-2 py-0.5 rounded bg-slate-700 text-slate-300 font-mono">partners.csv</span>
              </div>
              <p className="text-xs text-slate-400 mb-3">
                Columns: partner_id, partner_name, partner_type, category, pan_status, pan, bank_status, ifsc, city, onboarding_date, fy_paid_before, fy_tds_before, equipment_recovered_before
              </p>
            </div>

            <div>
              <label className="flex flex-col items-center justify-center p-4 border-2 border-dashed border-slate-700 hover:border-emerald-500 rounded-md cursor-pointer transition-colors bg-slate-900/50">
                <Upload className="w-5 h-5 text-slate-400 mb-1" />
                <span className="text-xs text-slate-300 font-medium">Click to upload partners.csv</span>
                <input
                  type="file"
                  accept=".csv,.txt"
                  className="hidden"
                  onChange={(e) => e.target.files?.[0] && handleFileUpload('partners', e.target.files[0])}
                  disabled={loading === 'partners'}
                />
              </label>

              {results.partners && (
                <div className="mt-3 p-2.5 rounded bg-slate-900/80 border border-slate-700 text-xs">
                  {results.partners.error ? (
                    <div className="text-rose-400 flex items-center space-x-1.5">
                      <AlertCircle className="w-4 h-4" />
                      <span>{results.partners.error}</span>
                    </div>
                  ) : (
                    <div className="text-emerald-400 flex items-center justify-between">
                      <span className="flex items-center space-x-1">
                        <CheckCircle2 className="w-4 h-4" />
                        <span>Ingested {results.partners.result?.successful ?? results.partners.successful} rows</span>
                      </span>
                      {results.partners.result?.errors?.length > 0 && (
                        <span className="text-amber-400 font-semibold">
                          ({results.partners.result.errors.length} errors)
                        </span>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* 2. Slots CSV */}
          <div className="p-4 rounded-lg bg-slate-800/60 border border-slate-700/80 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="font-semibold text-sm text-slate-200">2. Delivery Slots</span>
                <span className="text-xs px-2 py-0.5 rounded bg-slate-700 text-slate-300 font-mono">slots.csv</span>
              </div>
              <p className="text-xs text-slate-400 mb-3">
                Columns: slot_id, city, slot_date, start_time, end_time, surge, rain.
                Controls slot multipliers (surge x1.3, rain x1.5, non-stacking).
              </p>
            </div>

            <div>
              <label className="flex flex-col items-center justify-center p-4 border-2 border-dashed border-slate-700 hover:border-emerald-500 rounded-md cursor-pointer transition-colors bg-slate-900/50">
                <Upload className="w-5 h-5 text-slate-400 mb-1" />
                <span className="text-xs text-slate-300 font-medium">Click to upload slots.csv</span>
                <input
                  type="file"
                  accept=".csv,.txt"
                  className="hidden"
                  onChange={(e) => e.target.files?.[0] && handleFileUpload('slots', e.target.files[0])}
                  disabled={loading === 'slots'}
                />
              </label>

              {results.slots && (
                <div className="mt-3 p-2.5 rounded bg-slate-900/80 border border-slate-700 text-xs">
                  {results.slots.error ? (
                    <div className="text-rose-400 flex items-center space-x-1.5">
                      <AlertCircle className="w-4 h-4" />
                      <span>{results.slots.error}</span>
                    </div>
                  ) : (
                    <div className="text-emerald-400 flex items-center space-x-1">
                      <CheckCircle2 className="w-4 h-4" />
                      <span>Ingested {results.slots.result?.successful ?? results.slots.successful} slots</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* 3. Task Events CSV */}
          <div className="p-4 rounded-lg bg-slate-800/60 border border-slate-700/80 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="font-semibold text-sm text-slate-200">3. Task Events Dataset</span>
                <span className="text-xs px-2 py-0.5 rounded bg-slate-700 text-slate-300 font-mono">task_events.csv</span>
              </div>
              <p className="text-xs text-slate-400 mb-3">
                Columns: event_id, task_id, partner_id, event_type, event_ts, slot_id, distance_km, picked_up, rating.
                Deduplicates identical events (e.g. EV-00905).
              </p>
            </div>

            <div>
              <label className="flex flex-col items-center justify-center p-4 border-2 border-dashed border-slate-700 hover:border-emerald-500 rounded-md cursor-pointer transition-colors bg-slate-900/50">
                <Upload className="w-5 h-5 text-slate-400 mb-1" />
                <span className="text-xs text-slate-300 font-medium">Click to upload task_events.csv</span>
                <input
                  type="file"
                  accept=".csv,.txt"
                  className="hidden"
                  onChange={(e) => e.target.files?.[0] && handleFileUpload('tasks', e.target.files[0])}
                  disabled={loading === 'tasks'}
                />
              </label>

              {results.tasks && (
                <div className="mt-3 p-2.5 rounded bg-slate-900/80 border border-slate-700 text-xs">
                  {results.tasks.error ? (
                    <div className="text-rose-400 flex items-center space-x-1.5">
                      <AlertCircle className="w-4 h-4" />
                      <span>{results.tasks.error}</span>
                    </div>
                  ) : (
                    <div className="text-emerald-400 flex items-center justify-between">
                      <span className="flex items-center space-x-1">
                        <CheckCircle2 className="w-4 h-4" />
                        <span>Ingested {results.tasks.result?.successful ?? results.tasks.successful} events</span>
                      </span>
                      {results.tasks.result?.duplicates_skipped > 0 && (
                        <span className="text-amber-400">
                          ({results.tasks.result.duplicates_skipped} duplicates skipped)
                        </span>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* 4. Command File */}
          <div className="p-4 rounded-lg bg-slate-800/60 border border-slate-700/80 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="font-semibold text-sm text-slate-200">4. Settlement Commands</span>
                <span className="text-xs px-2 py-0.5 rounded bg-slate-700 text-slate-300 font-mono">commands.txt</span>
              </div>
              <p className="text-xs text-slate-400 mb-3">
                Commands: RUN_BATCH, BANK_RETURN, BANK_VERIFIED, PAN_UPDATE, HOLD, RELEASE, COMPLAINT, ADJUST, SET_MARKETPLACE.
              </p>
            </div>

            <div>
              <label className="flex flex-col items-center justify-center p-4 border-2 border-dashed border-slate-700 hover:border-emerald-500 rounded-md cursor-pointer transition-colors bg-slate-900/50">
                <Upload className="w-5 h-5 text-slate-400 mb-1" />
                <span className="text-xs text-slate-300 font-medium">Click to upload commands.txt</span>
                <input
                  type="file"
                  accept=".txt,.csv"
                  className="hidden"
                  onChange={(e) => e.target.files?.[0] && handleFileUpload('commands', e.target.files[0])}
                  disabled={loading === 'commands'}
                />
              </label>

              {results.commands && (
                <div className="mt-3 p-2.5 rounded bg-slate-900/80 border border-slate-700 text-xs">
                  {results.commands.error ? (
                    <div className="text-rose-400 flex items-center space-x-1.5">
                      <AlertCircle className="w-4 h-4" />
                      <span>{results.commands.error}</span>
                    </div>
                  ) : (
                    <div className="text-emerald-400 flex items-center space-x-1">
                      <CheckCircle2 className="w-4 h-4" />
                      <span>Executed {results.commands.total_executed} commands</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

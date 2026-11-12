import React, { useState } from 'react';
import { Play, Terminal, CheckCircle2, AlertCircle, RefreshCw } from 'lucide-react';
import { api } from '../api';

interface CommandsTabProps {
  onRefresh: () => void;
  setBannerMessage: (msg: { text: string; type: 'success' | 'error' | 'info' } | null) => void;
}

export const CommandsTab: React.FC<CommandsTabProps> = ({ onRefresh, setBannerMessage }) => {
  const [singleCmd, setSingleCmd] = useState('');
  const [scriptContent, setScriptContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<{ cmd: string; time: string; result: any }[]>([]);

  const handleRunSingle = async () => {
    if (!singleCmd.trim()) return;
    try {
      setLoading(true);
      const res = await api.executeSingleCommand(singleCmd.trim());
      setHistory((prev) => [
        { cmd: singleCmd.trim(), time: new Date().toLocaleTimeString(), result: res },
        ...prev
      ]);
      setBannerMessage({ text: `Command executed: ${res.status || 'OK'}`, type: 'success' });
      onRefresh();
    } catch (err: any) {
      setHistory((prev) => [
        { cmd: singleCmd.trim(), time: new Date().toLocaleTimeString(), result: { error: err.message } },
        ...prev
      ]);
      setBannerMessage({ text: err.message, type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const handleRunScript = async () => {
    if (!scriptContent.trim()) return;
    try {
      setLoading(true);
      const res = await api.executeCommandsScript(scriptContent.trim());
      setHistory((prev) => [
        {
          cmd: `Batch Script (${res.total_executed} commands)`,
          time: new Date().toLocaleTimeString(),
          result: res
        },
        ...prev
      ]);
      setBannerMessage({ text: `Script executed successfully (${res.total_executed} commands)!`, type: 'success' });
      onRefresh();
    } catch (err: any) {
      setBannerMessage({ text: err.message, type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const commandPresets = [
    { label: 'Run Batch 2026-09-14', cmd: 'RUN_BATCH|2026-09-14' },
    { label: 'Bank Return GP-018', cmd: 'BANK_RETURN|GP-018|2026-09-14|2026-09-16 12:00:00|ACCOUNT_CLOSED' },
    { label: 'PAN Update GP-048', cmd: 'PAN_UPDATE|GP-048|2026-09-30 14:20:00|BYDPS3365L' },
    { label: 'Set Marketplace Active', cmd: 'SET_MARKETPLACE|2026-10-01|true' },
    { label: 'Verify Bank GP-004', cmd: 'BANK_VERIFIED|GP-004|2026-10-07 15:00:00' },
    { label: 'Valid Adjust GP-024', cmd: 'ADJUST|GP-024|2026-10-05|-350.00|TKT-88219|2026-10-08 13:00:00' },
    { label: 'Reject Adjust GP-024 (No Ref)', cmd: 'ADJUST|GP-024|2026-10-05|-350.00||2026-10-08 12:00:00' },
    { label: 'Reject Adjust GP-024 (>2000)', cmd: 'ADJUST|GP-024|2026-10-05|2500.00|TKT-88213|2026-10-08 11:00:00' },
    { label: 'Hold GP-026 (KYC)', cmd: 'HOLD|GP-026|2026-10-16 16:00:00|KYC_REVIEW' },
    { label: 'Release GP-026', cmd: 'RELEASE|GP-026|2026-10-25 16:00:00' },
  ];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Single Command Runner */}
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 shadow-sm space-y-4">
          <div>
            <h3 className="text-base font-semibold text-white flex items-center space-x-2">
              <Terminal className="w-4 h-4 text-emerald-400" />
              <span>Interactive Command Runner</span>
            </h3>
            <p className="text-xs text-slate-400 mt-1">
              Execute individual commands strictly parsed and validated by the Python backend.
            </p>
          </div>

          <div className="flex space-x-2">
            <input
              type="text"
              placeholder="e.g. RUN_BATCH|2026-09-14"
              value={singleCmd}
              onChange={(e) => setSingleCmd(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleRunSingle()}
              className="flex-1 bg-slate-800 border border-slate-700 rounded-md px-3 py-2 text-xs font-mono text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
            />
            <button
              onClick={handleRunSingle}
              disabled={loading || !singleCmd.trim()}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-md text-xs font-semibold flex items-center space-x-1.5 transition-colors disabled:opacity-50"
            >
              <Play className="w-3.5 h-3.5" />
              <span>Execute</span>
            </button>
          </div>

          <div>
            <span className="text-xs text-slate-400 font-medium block mb-2">Preset Quick Actions:</span>
            <div className="flex flex-wrap gap-1.5">
              {commandPresets.map((p) => (
                <button
                  key={p.label}
                  onClick={() => setSingleCmd(p.cmd)}
                  className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-[11px] font-mono border border-slate-700 transition-colors"
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Script Runner */}
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 shadow-sm space-y-4">
          <div>
            <h3 className="text-base font-semibold text-white flex items-center space-x-2">
              <Terminal className="w-4 h-4 text-indigo-400" />
              <span>Multi-Line Command Script</span>
            </h3>
            <p className="text-xs text-slate-400 mt-1">
              Paste or edit commands.txt lines to process in sequential file order.
            </p>
          </div>

          <textarea
            rows={5}
            placeholder={`RUN_BATCH|2026-09-14\nBANK_RETURN|GP-018|2026-09-14|2026-09-16 12:00:00|ACCOUNT_CLOSED\nRUN_BATCH|2026-09-21`}
            value={scriptContent}
            onChange={(e) => setScriptContent(e.target.value)}
            className="w-full bg-slate-800 border border-slate-700 rounded-md p-3 text-xs font-mono text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />

          <button
            onClick={handleRunScript}
            disabled={loading || !scriptContent.trim()}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-md text-xs font-semibold flex items-center space-x-1.5 transition-colors disabled:opacity-50"
          >
            <Play className="w-3.5 h-3.5" />
            <span>Run Multi-Line Script</span>
          </button>
        </div>
      </div>

      {/* Execution Console History */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 shadow-sm">
        <h4 className="text-xs uppercase font-semibold text-slate-400 tracking-wider mb-3">
          Console Output & Audit Trail
        </h4>
        {history.length === 0 ? (
          <div className="text-center py-8 text-slate-500 text-xs font-mono">
            No commands executed in this session yet.
          </div>
        ) : (
          <div className="space-y-2 max-h-72 overflow-y-auto font-mono text-xs">
            {history.map((h, i) => (
              <div key={i} className="p-3 bg-slate-950 rounded border border-slate-800">
                <div className="flex items-center justify-between text-slate-400 mb-1">
                  <span className="font-semibold text-emerald-400">&gt; {h.cmd}</span>
                  <span className="text-[10px] text-slate-500">{h.time}</span>
                </div>
                <pre className="text-slate-300 text-[11px] overflow-x-auto whitespace-pre-wrap">
                  {JSON.stringify(h.result, null, 2)}
                </pre>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

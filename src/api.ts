import {
  SystemStatus,
  Partner,
  TaskEvent,
  WeeklyStatement,
  SettlementBatch,
  LedgerEntry,
  TDSSummaryRow
} from './types';

export const api = {
  async getStatus(): Promise<SystemStatus> {
    const res = await fetch('/api/status');
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to get status`);
    return res.json();
  },

  async initDb(dropAll = false): Promise<{ status: string; message: string }> {
    const res = await fetch('/api/init-db', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ drop_all: dropAll })
    });
    if (!res.ok) throw new Error(`Failed to initialize database: ${res.statusText}`);
    return res.json();
  },

  async ingestPreloaded(): Promise<any> {
    const res = await fetch('/api/ingest/preloaded', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    });
    if (!res.ok) throw new Error('Failed to ingest preloaded files');
    return res.json();
  },

  async ingestPartnersCsv(csvContent: string): Promise<any> {
    const res = await fetch('/api/ingest/partners', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ csv_content: csvContent })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || 'Failed to ingest partners CSV');
    }
    return res.json();
  },

  async ingestSlotsCsv(csvContent: string): Promise<any> {
    const res = await fetch('/api/ingest/slots', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ csv_content: csvContent })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || 'Failed to ingest slots CSV');
    }
    return res.json();
  },

  async ingestTasksCsv(csvContent: string): Promise<any> {
    const res = await fetch('/api/ingest/tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ csv_content: csvContent })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || 'Failed to ingest task events CSV');
    }
    return res.json();
  },

  async executePreloadedCommands(): Promise<any> {
    const res = await fetch('/api/commands/execute-preloaded', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    });
    if (!res.ok) throw new Error('Failed to execute preloaded commands');
    return res.json();
  },

  async executeCommandsScript(commandsText: string): Promise<any> {
    const res = await fetch('/api/commands/execute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ commands: commandsText })
    });
    if (!res.ok) throw new Error('Failed to execute command script');
    return res.json();
  },

  async executeSingleCommand(line: string): Promise<any> {
    const res = await fetch('/api/commands/single', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command: line })
    });
    if (!res.ok) throw new Error('Failed to execute command line');
    return res.json();
  },

  async runBatch(batchDate: string): Promise<any> {
    const res = await fetch('/api/batches/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ batch_date: batchDate })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || `Failed to run batch ${batchDate}`);
    }
    return res.json();
  },

  async getPartners(): Promise<Partner[]> {
    const res = await fetch('/api/partners');
    if (!res.ok) throw new Error('Failed to fetch partners');
    const data = await res.json();
    return data.partners || [];
  },

  async getPartnerDetail(partnerId: string): Promise<{ partner: Partner; statements: WeeklyStatement[]; ledger: LedgerEntry[] }> {
    const res = await fetch(`/api/partners/${encodeURIComponent(partnerId)}`);
    if (!res.ok) throw new Error('Failed to fetch partner detail');
    return res.json();
  },

  async getTasks(limit = 100): Promise<TaskEvent[]> {
    const res = await fetch(`/api/tasks?limit=${limit}`);
    if (!res.ok) throw new Error('Failed to fetch task events');
    const data = await res.json();
    return data.tasks || [];
  },

  async getStatements(weekStart?: string, status?: string): Promise<WeeklyStatement[]> {
    let url = '/api/statements';
    const params = new URLSearchParams();
    if (weekStart) params.append('week_start', weekStart);
    if (status) params.append('status', status);
    if (params.toString()) url += `?${params.toString()}`;

    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch weekly statements');
    const data = await res.json();
    return data.statements || [];
  },

  async getBatches(): Promise<SettlementBatch[]> {
    const res = await fetch('/api/batches');
    if (!res.ok) throw new Error('Failed to fetch batches');
    const data = await res.json();
    return data.batches || [];
  },

  async getLedger(partnerId?: string): Promise<LedgerEntry[]> {
    let url = '/api/ledger';
    if (partnerId) url += `?partner_id=${encodeURIComponent(partnerId)}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch ledger entries');
    const data = await res.json();
    return data.ledger || [];
  },

  async getTdsSummary(fy = '2026-27', quarter = 'Q2'): Promise<TDSSummaryRow[]> {
    const res = await fetch(`/api/reports/tds_summary?fy=${encodeURIComponent(fy)}&quarter=${encodeURIComponent(quarter)}`);
    if (!res.ok) throw new Error('Failed to fetch TDS summary');
    const data = await res.json();
    return data.summary || [];
  },

  downloadReportUrl(reportName: string): string {
    return `/api/reports/download/${reportName}`;
  }
};

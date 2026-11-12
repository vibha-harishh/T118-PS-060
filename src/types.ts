export interface SystemStatus {
  partners_count: number;
  slots_count: number;
  tasks_count: number;
  batches_count: number;
  statements_count: number;
  ledger_count: number;
  marketplace_mode: boolean;
  marketplace_date: string | null;
  preloaded: {
    partners: boolean;
    slots: boolean;
    commands: boolean;
  };
}

export interface Partner {
  partner_id: string;
  partner_name: string;
  partner_type: 'INDIVIDUAL' | 'FIRM';
  category: 'DELIVERY' | 'SERVICE_PROFESSIONAL';
  pan_status: 'VALID' | 'INVALID' | 'MISSING';
  pan: string | null;
  bank_status: 'VERIFIED' | 'UNVERIFIED';
  ifsc: string;
  city: string;
  onboarding_date: string;
  fy_paid_before_rupees: number;
  fy_tds_before_rupees: number;
  equipment_recovered_rupees: number;
  is_held_manual: number;
  manual_hold_reason: string | null;
  bank_retry_count: number;
  paid_in_batches_rupees?: number;
  tds_in_batches_rupees?: number;
}

export interface TaskEvent {
  event_id: string;
  task_id: string;
  partner_id: string;
  partner_name?: string;
  event_type: 'COMPLETED' | 'CANCELLED_BY_CUSTOMER' | 'CANCELLED_BY_PARTNER';
  event_ts: string;
  slot_id: string | null;
  distance_km: number | null;
  picked_up: number | null;
  rating: number | null;
  week_start: string;
  task_earnings_rupees: number;
  surge?: number;
  rain?: number;
}

export interface WeeklyStatement {
  id: number;
  partner_id: string;
  week_start: string;
  batch_date: string;
  completed: number;
  cancelled_by_partner: number;
  cancelled_by_customer: number;
  cancellation_rate_pct: number;
  avg_rating: number;
  task_earnings_rupees: number;
  incentive_rupees: number;
  gross_rupees: number;
  penalties_rupees: number;
  penalty_cap_rupees: number;
  adjustments_rupees: number;
  tds_base_rupees: number;
  tds_section: string;
  tds_rate_pct: number;
  tds_rupees: number;
  equipment_deduction_rupees: number;
  carry_in_rupees: number;
  net_payable_rupees: number;
  status: 'PAID' | 'HELD_BANK' | 'HELD_PAN' | 'HELD_MANUAL' | 'HELD' | 'CARRIED_FORWARD' | 'RETURNED' | 'NO_ACTIVITY';
}

export interface SettlementBatch {
  batch_date: string;
  processed_ts: string;
  partners_paid: number;
  amount_paid_rupees: number;
  partners_held: number;
  amount_held_rupees: number;
  carried_forward_rupees: number;
  retries: number;
  tds_total_rupees: number;
}

export interface LedgerEntry {
  id: number;
  partner_id: string;
  entry_ts: string;
  entry_type: string;
  week_start: string | null;
  amount_rupees: number;
  earned_to_date_rupees: number;
  withheld_to_date_rupees: number;
  paid_to_date_rupees: number;
  recovered_to_date_rupees: number;
}

export interface TDSSummaryRow {
  fy: string;
  quarter: string;
  partner_id: string;
  pan: string;
  section: string;
  rate_pct: string;
  amount_paid: string;
  tds_deducted: string;
}

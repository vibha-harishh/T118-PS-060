# PS-060 – Contractor and Gig-Worker Payout Engine with TDS and Weekly Settlement — Sample Data Pack

Prepared by 10 SECONDS for Team T118.

## Files

| File | What it holds | Row count |
|---|---|---|
| `partners.csv` | 50 gig partners with type, category, PAN and bank status, FY payments before the period | 50 data rows |
| `slots.csv` | Delivery slots per city per day with SURGE and RAIN flags (8 weeks) | 560 data rows |
| `task_events.csv` | Task events (completed / cancelled) over 8 weeks, in event_ts order | 2713 data rows |
| `commands.txt` | Weekly batch runs, bank returns, bank verification, PAN updates, holds/releases, complaints, adjustments, marketplace flag and prints | 159 command lines (excluding comments) |

Volumes in this sample are reduced for email delivery; the hidden evaluation set is larger and uses the same schema.

Row numbers quoted below are 1-based data-row numbers (the header is row 0). Line numbers for `commands.txt` are physical line numbers including comment lines.

## Column reference

Conventions: dates `YYYY-MM-DD`; timestamps `YYYY-MM-DD HH:MM:SS` (24h, IST, no timezone suffix); money in Rs as plain decimals with 2 places (no commas, no symbol); percentages as plain numbers (12.5 means 12.5%); booleans `true`/`false`; IDs uppercase with a fixed prefix. An empty cell means "not applicable / not supplied" and only occurs in columns whose notes say so.

### `partners.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| partner_id | string | GP-nnn | — | — |
| partner_name | string | — | — | — |
| partner_type | enum | — | INDIVIDUAL, FIRM | 194C rate 1% / 2% |
| category | enum | — | DELIVERY, SERVICE_PROFESSIONAL | 194C / 194J |
| pan_status | enum | — | VALID, INVALID, MISSING | — |
| pan | string | AAAAA9999A | — | empty when MISSING |
| bank_status | enum | — | VERIFIED, UNVERIFIED | UNVERIFIED → payouts HELD |
| ifsc | string | 11 chars | — | — |
| city | string | — | Bengaluru, Hyderabad | slot city |
| onboarding_date | date | — | — | — |
| fy_paid_before | decimal | Rs | — | payments already made in FY 2026-27 before 2026-09-07 (threshold tests) |
| fy_tds_before | decimal | Rs | — | TDS already deducted in the FY before the period |
| equipment_recovered_before | decimal | Rs | 0–1800 | bag cost already recovered; 1800 = nothing left to recover |

### `slots.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| slot_id | string | SLT-<CITY>-<YYYYMMDD>-<n> | — | — |
| city | string | — | — | — |
| slot_date | date | — | — | date on which the slot starts |
| start_time | string | HH:MM | — | — |
| end_time | string | HH:MM | — | slot 5 runs 23:00 → 07:00 the next morning |
| surge | bool | — | — | x1.3 |
| rain | bool | — | — | x1.5; surge and rain do not stack, the higher applies |

### `task_events.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| event_id | string | EV-nnnnn | — | unique except the planted duplicate |
| task_id | string | TSK-nnnnn | — | — |
| partner_id | string | — | partners.csv | — |
| event_type | enum | — | COMPLETED, CANCELLED_BY_CUSTOMER, CANCELLED_BY_PARTNER | — |
| event_ts | timestamp | IST | — | completion or cancellation time; decides the week |
| slot_id | string | — | slots.csv | slot containing event_ts |
| distance_km | decimal | km, 1 dp | — | base pay = Rs 25 + Rs 6 per km beyond 3 km, rounded half-up to the rupee |
| picked_up | bool | — | — | CANCELLED_BY_CUSTOMER only (Rs 20 if true) |
| rating | int | — | 1–5 | COMPLETED only |

## Command file format

`commands.txt` holds one command per line in the form `COMMAND_NAME|arg1|arg2|...`. Commands must be processed strictly in file order. Lines starting with `#` are comments and blank lines are ignored. An empty argument (two adjacent `|`) means "not supplied". Every command used in this pack:

| Command | Arguments (in order) | Meaning |
|---|---|---|
| `RUN_BATCH` | `batch_date` | Monday settlement batch for the previous Mon–Sun week |
| `BANK_RETURN` | `partner_id|batch_date|ts|reason` | the payout made in that batch bounced |
| `BANK_VERIFIED` | `partner_id|ts` | bank status becomes VERIFIED |
| `PAN_UPDATE` | `partner_id|ts|pan` | PAN supplied / corrected; pan_status becomes VALID |
| `HOLD` | `partner_id|ts|reason` | manual hold of all future payouts |
| `RELEASE` | `partner_id|ts` | release a manual hold |
| `COMPLAINT` | `partner_id|task_id|ts|reason` | verified customer complaint (Rs 200 penalty) in the task's week |
| `ADJUST` | `partner_id|week_start|amount|reference|ts` | manual adjustment (signed) for the week; reference may be empty (then reject) |
| `SET_MARKETPLACE` | `effective_date|flag` | platform marketplace mode on/off (194-O) for payments on or after the date |
| `PRINT_STATEMENT` | `partner_id|week_start` | weekly payout statement |
| `PRINT_BATCH` | `batch_date` | batch summary |
| `PRINT_TDS_SUMMARY` | `fy|quarter` | Form 26Q-style summary; fy as 2026-27, quarter Q1–Q4 (Indian FY) |

## Planted scenarios

Every edge case in the brief, mapped to the exact record where it occurs, followed by extra traps.

- **EC-01 Week with exactly 60 completed tasks and cancellation rate exactly 8%**
  - GP-010 week of 2026-09-21: exactly 60 COMPLETED + 6 CANCELLED_BY_PARTNER + 9 CANCELLED_BY_CUSTOMER → cancellation rate 6/75 = 8.00% (not > 8%), so the Rs 600 tier is kept; 3 partner cancellations beyond the free 3 cost Rs 150 — `task_events.csv rows 860, 862, 883, 886, 887, 889 … 1338 (75 rows)`
- **EC-02 Single payment of exactly Rs 30,000 under 194C (not exceeding) versus Rs 30,001**
  - GP-004 and GP-005 (FIRM, DELIVERY, bank UNVERIFIED) are HELD for weeks 2026-09-07..09-28; each week has 100–110 clean tasks (>= 90 → Rs 1,200 incentive). After BANK_VERIFIED the 2026-10-12 batch releases one payment (no tasks in the week of 2026-10-05): GP-004 exactly Rs 30,000.00 (not exceeding Rs 30,000 → no 194C TDS, FY cumulative stays < Rs 1,00,000) and GP-005 exactly Rs 30,001.00 (→ 194C at 2%) — `task_events.csv rows 1, 5, 16, 20, 21, 25 … 1805 (422 rows) / rows 2, 8, 9, 11, 14, 18 … 1809 (422 rows); commands.txt line 15 and line 16`
- **EC-03 Cumulative 194C threshold crossed by a payment that itself is Rs 500**
  - GP-012: FY payments before the period Rs 99,800.00; its first weekly payment (batch 2026-09-14) is exactly Rs 500.00 → cumulative Rs 1,00,300 crosses Rs 1,00,000; 194C at 1% applies to this Rs 500 payment and every later one (not to the earlier Rs 99,800) — `partners.csv GP-012 (row 12); task_events.csv rows 28, 35, 79, 89, 130, 136 … 391 (12 rows)`
- **EC-04 Penalty cap of 20% binding so only part of a complaint deduction applies**
  - GP-014 week of 2026-09-28: task earnings Rs 1,225.00 (24 tasks = Rs 1,200 + the complained task Rs 25); 4 partner cancellations (1 beyond 3 → Rs 50) + verified complaint Rs 200 = Rs 250 > cap 20% x 1,225 = Rs 245 → only Rs 195 of the complaint applies — `task_events.csv rows 1351, 1366, 1385, 1408, 1409, 1422 … 1788 (28 rows) and row 1722; commands.txt line 12`
- **EC-05 Net payable Rs 199.50 rounding to Rs 200 (minimum met or not) **
  - GP-016 week of 2026-09-07: 4 rain-slot tasks with base pay 25 + 31 + 37 + 40 = Rs 133 x 1.5 = Rs 199.50 net — below the Rs 200 minimum (do not round up): carried forward; it has no tasks in the next week, and the carry-forward pays at any amount in the batch after — `task_events.csv rows 146, 154, 160, 205`
- **EC-06 Bank return on the second retry**
  - GP-018: batch 2026-09-14 payout returns (BANK_RETURN), retry 1 in batch 2026-09-21 returns, retry 2 in batch 2026-09-28 returns — second retry exhausted → HELD_MANUAL (Rs 10 bank charge per retry) — `commands.txt line 3, line 6, line 9`
- **EC-07 PAN supplied mid-week after a hold: release in the same batch or next**
  - GP-048: PAN MISSING with Rs 49,000 FY payments before the period — once cumulative passes Rs 50,000 payouts are HELD (and 20% rate applies); PAN supplied Wednesday 2026-09-30 14:20 — decide whether the held amount releases in the 2026-10-05 batch (same week's batch) or later, and at which rate — `commands.txt line 10`
- **EC-08 Marketplace flag flipping on at the start of a quarter with partners already past the 194C threshold**
  - SET_MARKETPLACE true from 2026-10-01 (Q3). GP-020 (Rs 1,26,000) and GP-022 (Rs 1,04,500) are INDIVIDUAL DELIVERY partners already past the 194C cumulative threshold (1% in September); from the 2026-10-05 batch 194-O applies instead, whose INDIVIDUAL threshold is Rs 5,00,000 — no TDS; FIRM partners pay 194-O 1% with no threshold — `commands.txt line 11; partners.csv GP-020 (row 20) and GP-022 (row 22)`
- **Extra traps (not in the brief, but realistic):**
  - GP-047: PAN INVALID — TDS at 20% under whichever section applies, once that section's threshold is met — `partners.csv GP-047 (row 47)`
  - GP-024: ADJUST +2,500 (above the Rs 2,000 limit) and ADJUST −350 without a reference — both REJECTED; ADJUST −350 with reference TKT-88219 accepted and reduces the TDS base — `commands.txt line 17, line 18, line 19`
  - GP-026: manual HOLD (KYC review) before the 2026-10-19 batch and RELEASE before the 2026-10-26 batch — the held week pays in the release batch — `commands.txt line 22 and line 25`
  - GP-028: Rs 1,650 of the Rs 1,800 bag already recovered — only Rs 150 is deducted (in the first week whose net before TDS is >= Rs 1,000), then the deduction stops — `partners.csv GP-028 (row 28)`
  - GP-001: task COMPLETED at 2026-09-20 23:59:59 (Sunday) belongs to the week of 2026-09-14 (batch 2026-09-21) — `task_events.csv row 850`
  - GP-001: a task assigned Sunday night is CANCELLED_BY_PARTNER at 2026-10-05 00:00:10 — the cancellation counts in the week of 2026-10-05, not 2026-09-28 — `task_events.csv rows 1820, 1822`
  - Duplicate task event EV-00905 (identical row delivered twice) — count and pay it once — `task_events.csv rows 905, 906`

## What is NOT in this pack

Expected outputs are not provided for this set. Validate your engine with your own test suite against the rules in your brief (BR-01 … BR-nn). A separate hidden input set with the same schema will be used at final evaluation; outputs are compared field-for-field, so follow the column formats above exactly in your own output.

## Output format expected at evaluation

Produce these CSV files (header row, same conventions as above, rows sorted as stated). Where the brief is silent on a format detail the choice below is binding for evaluation.

### `weekly_statements.csv`

One row per partner per week (every partner, every week, whether printed or not), sorted by week_start then partner_id.

Columns, in order: `partner_id`, `week_start`, `completed`, `cancelled_by_partner`, `cancelled_by_customer`, `cancellation_rate_pct`, `avg_rating`, `task_earnings`, `incentive`, `gross`, `penalties`, `penalty_cap`, `adjustments`, `tds_base`, `tds_section`, `tds_rate_pct`, `tds`, `equipment_deduction`, `carry_in`, `net_payable`, `status`

### `batch_summary.csv`

One row per RUN_BATCH.

Columns, in order: `batch_date`, `partners_paid`, `amount_paid`, `partners_held`, `amount_held`, `carried_forward`, `retries`, `tds_total`

### `ledger.csv`

One row per ledger movement, in posting order.

Columns, in order: `partner_id`, `entry_ts`, `entry_type`, `week_start`, `amount`, `earned_to_date`, `withheld_to_date`, `paid_to_date`, `recovered_to_date`

### `tds_summary.csv`

One row per section per partner per PRINT_TDS_SUMMARY.

Columns, in order: `fy`, `quarter`, `partner_id`, `pan`, `section`, `rate_pct`, `amount_paid`, `tds_deducted`

Binding choices: cancellation_rate_pct = cancelled_by_partner / (completed + cancelled_by_partner + cancelled_by_customer) x 100, 2 dp. gross = task_earnings + incentive. tds_base = gross − applied penalties ± accepted adjustments (the equipment deduction is a recovery and is not in the TDS base). `status` is PAID, HELD_BANK, HELD_PAN, HELD_MANUAL, HELD, CARRIED_FORWARD, RETURNED or NO_ACTIVITY; tds_section is 194C, 194J, 194-O or NONE.

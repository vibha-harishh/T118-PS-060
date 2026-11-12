# T118-PS-060: Contractor and Gig-Worker Payout Engine with TDS and Weekly Settlement

A full-stack, industry-standard engineering platform for contractor and gig-worker weekly settlements, tax deducted at source (TDS under Sections 194C, 194J, and 194-O), incentive computation, penalty capping, and running financial ledgers.

---

## 1. Architecture & Technology Stack

- **Frontend**: React 19, TypeScript, Tailwind CSS, Lucide Icons, Vite.
  - Role: Displays data, collects inputs, triggers operations.
  - Constraint: **Zero financial calculations in JavaScript**; all business rules execute in Python.
- **Backend**: Python 3.10+ REST API server (`backend/server.py`).
  - Monetary Precision: Uses Python `decimal.Decimal` and integer paise storage (1 Rupee = 100 paise) with `ROUND_HALF_UP` rounding.
  - Timezone: Indian Standard Time (IST) attribution for all task completions and cancellations.
- **Database**: SQLite (`payout_engine.db`) with foreign key constraints, atomic transactions, and indexing.
- **Proxy**: Express server on port 3000 proxying `/api/*` to the Python backend on port 5050 and mounting `vite.middlewares` in development.

---

## 2. Core Business Rules

### Module 1: Partner Registration
- Partner types: `INDIVIDUAL`, `FIRM`.
- Categories: `DELIVERY` (Section 194C), `SERVICE_PROFESSIONAL` (Section 194J).
- PAN validation (`^[A-Z]{5}[0-9]{4}[A-Z]$`), status: `VALID`, `INVALID`, `MISSING`.
- Duplicate partner ID and duplicate valid PAN detection.
- Bank verification status: `VERIFIED`, `UNVERIFIED` (unverified accounts have payouts held).

### Module 2 & 3: Task Ingestion & Distance Earnings
- Base Pay: ₹25.
- Distance Rate: Additional ₹6 per km beyond 3 km.
  $$\text{Base Pay} = 25 + \max(0, \text{distance} - 3) \times 6$$
- Multipliers:
  - Surge slot: $\times 1.3$
  - Rain slot: $\times 1.5$
  - If both apply, **the higher multiplier applies (1.5), never stacked**.
- Rounding: Completed task earnings rounded to nearest Rupee half-up.
- Customer cancellation after pickup: Flat ₹20. Customer cancellation before pickup: ₹0.
- Partner cancellation: ₹0.
- Week attribution: Monday 00:00:00 to Sunday 23:59:59 IST.

### Module 4: Weekly Incentives
- Tier 1: $\ge 60$ completed tasks $\rightarrow$ ₹600.
- Tier 2: $\ge 90$ completed tasks $\rightarrow$ ₹1,200.
- Tier 3: $\ge 120$ completed tasks $\rightarrow$ ₹2,000.
- Highest eligible tier applies.
- **Forfeiture**:
  - Cancellation rate $> 8.00\%$ (strictly greater; exactly 8.00% is kept).
  - Average rating $< 4.20$.

### Module 5: Penalties and Equipment Deductions
- Partner cancellations: First 3 are free; ₹50 for every cancellation thereafter.
- Customer complaints: Verified complaint penalty is ₹200.
- **Penalty Cap**: Total applied penalties cannot exceed $20\%$ of weekly gross earnings ($\text{gross} = \text{task earnings} + \text{incentive}$).
- Equipment Bag Deduction: ₹150 per week up to ₹1,800 maximum lifetime recovery.
  - Paused if net payable before TDS is below ₹1,000.

### Module 6: TDS Selection & PAN Rules
1. **Standard Mode**:
   - **Section 194C** (Delivery):
     - Individual: $1\%$. Firm: $2\%$.
     - Applies if single payment $> ₹30,000$ OR annual cumulative $> ₹1,00,000$.
   - **Section 194J** (Service Professionals):
     - Rate: $10\%$.
     - Applies if annual cumulative $> ₹30,000$.
2. **Marketplace Mode (Section 194-O)**:
   - Activated via `SET_MARKETPLACE|effective_date|true`.
   - Replaces 194C and 194J.
   - Individual: $1\%$ with annual threshold $> ₹5,00,000$.
   - Firm: $1\%$ with **no threshold**.
3. **PAN Penal Rules**:
   - Invalid or Missing PAN: $20\%$ TDS rate once thresholds are crossed.
   - Missing PAN with cumulative payouts $> ₹50,000$: Settlement hold (`HELD_PAN`) until PAN is supplied.

### Module 7 & 8: Weekly Settlement, Holds & Bank Returns
- Weekly settlement runs every Monday for the prior Mon–Sun period.
- Minimum payout threshold is ₹200. Amounts below ₹200 are carried forward.
  - A carried-forward amount is paid in the subsequent batch without re-applying the minimum.
- Holds: `HELD_BANK` (unverified bank), `HELD_PAN` (missing PAN $> 50k$), `HELD_MANUAL` (KYC or retries exhausted).
- Bank Returns: Reverses payout in ledger. Deducts ₹10 bank charge per retry. Maximum 2 retries; third return sets `HELD_MANUAL`.

---

## 3. Evaluation Output CSVs

The engine generates all four required evaluation files:

1. `weekly_statements.csv`: Partner weekly breakdown (Gross, Incentives, Penalties, Cap, TDS Base, TDS, Equipment Deduction, Carry In, Net Payable, Status).
2. `batch_summary.csv`: Summary of each `RUN_BATCH` (Paid count/amount, Held count/amount, Carried forward, Retries, Total TDS).
3. `ledger.csv`: Complete double-entry running ledger audit trail.
4. `tds_summary.csv`: Form 26Q quarterly tax withholding reports.

---

## 4. Automated Test Suite

Run the full suite of automated unit tests covering all 15+ edge cases:

```bash
python3 -m unittest backend.tests.test_engine
```

Or via npm:

```bash
npm run test:py
```

---

## 5. Local Setup & Execution

### Prerequisites
- Python 3.10+
- Node.js 18+ and npm

### Installation
```bash
npm install
```

### Running the Application
```bash
npm run dev
```

Visit `http://localhost:3000` to interact with the engineering dashboard.

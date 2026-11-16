# Decision Log — Team(T118-PS-060)

**1. Integer Paise Representation:** Stored monetary values as integer paise in the database and used Python Decimal with ROUND_HALF_UP for financial calculations. This prevents floating-point precision errors and ensures accurate payout calculations.

**2. Modular Backend Architecture:** Divided backend functionality into separate Python modules for earnings, incentives, penalties, TDS, ledger management, reports, partner management and task processing. This improves code organisation, readability and maintainability.

**3. Weekly Settlement Processing:** Designed the settlement process around weekly payment cycles, using the previous Monday-to-Sunday period to calculate partner earnings, deductions and payable amounts.

**4. Business-Rule-Based Earnings Calculation:** Applied predefined rules for task payments, distance-based earnings and surge multipliers to ensure consistent calculation of partner earnings.

**5. TDS Calculation Based on Partner Category:** Implemented TDS calculations using partner category, PAN status and applicable project rules, including Sections 194C, 194J and 194-O.

**6. Penalty Limitation:** Applied a maximum penalty limit of 20% of weekly gross earnings to prevent total penalties from exceeding the defined business-rule limit.

**7. Partner Ledger Management:** Maintained financial transaction records for earnings, deductions and adjustments to support partner-wise financial tracking.

**8. Carry-Forward of Unpaid Amounts:** Implemented carry-forward handling for amounts below the minimum payout threshold so eligible unpaid balances can be considered in subsequent settlement cycles.

**9. Database Management:** Selected SQLite for storing partner details, task records, settlement information and financial transactions because it provides lightweight and structured database management.

**10. Backend API Design and Testing:** Used backend API endpoints to expose project operations and JSON responses. Tested backend functionality and business rules to identify errors and verify expected results.

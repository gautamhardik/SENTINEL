# Phase 7.2 — Information Architecture, Screen States & Detailed User Flow Master UX Specification

---

## 1. FINAL INFORMATION ARCHITECTURE

**Sentinel Risk Engine** is designed as a **Single-View State-Driven Screening Instrument**.

Rather than navigating across multiple pages or sub-routes, the user remains within a single focused container (`max-w-5xl` centered viewport). The view transitions dynamically between 4 core operational states: `IDLE`/`EDITING`, `ANALYZING`, `SUCCESS`, and `ERROR`.

---

## 2. FINAL FORM GROUPING

The 11 raw transaction fields are grouped into **3 logical, domain-aligned panels**:

1. **GROUP 1: TRANSACTION IDENTIFICATION**: `transaction_id`, `Timestamp`
2. **GROUP 2: PARTIES & ACCOUNTS**: `From_Account`, `From_Bank`, `To_Account`, `To_Bank`
3. **GROUP 3: PAYMENT & CURRENCY DETAILS**: `Amount_Paid`, `Amount_Received`, `Payment_Format`, `Payment_Currency`, `Receiving_Currency`

---

## 3. FIELD SPECIFICATION TABLE

| Field Name | User-Facing Label | Purpose / Description | Input Type | Req? | Default Value | Client Validation Rule | Helper Text | UX Priority |
| :--- | :--- | :--- | :--- | :---: | :--- | :--- | :--- | :---: |
| `transaction_id` | **Transaction ID** | Correlation ID for audit tracing | `text` (mono) | Yes | Auto-generated UUID | Non-empty string | Unique transaction reference | P0 |
| `Timestamp` | **Timestamp** | Local transaction execution time | `datetime-local` | Yes | Current ISO Timestamp | Valid date string | Execution date & time | P0 |
| `Amount_Paid` | **Amount Paid** | Outbound transfer amount | `number` | Yes | *None* | Float > `0.0` | Sender currency amount | P0 |
| `Amount_Received` | **Amount Received** | Inbound transfer amount | `number` | Yes | *None* | Float > `0.0` | Receiver currency amount | P0 |
| `From_Account` | **Sender Account ID** | Source account identifier | `text` (mono) | Yes | *None* | Non-empty string | Originating account key | P0 |
| `From_Bank` | **Sender Bank ID** | Source financial institution | `text` | Yes | *None* | Non-empty string | Originating bank code | P1 |
| `To_Account` | **Receiver Account ID** | Destination account identifier | `text` (mono) | Yes | *None* | Non-empty string | Destination account key | P0 |
| `To_Bank` | **Receiver Bank ID** | Destination financial institution | `text` | Yes | *None* | Non-empty string | Destination bank code | P1 |
| `Payment_Format` | **Payment Method** | Transfer format/rail | `select` | Yes | `"Wire"` | Must be valid option | Rails (Wire, ACH, Cheque, Credit) | P1 |
| `Payment_Currency` | **Sender Currency** | Outbound ISO currency code | `select` | Yes | `"USD"` | 3-letter ISO code | Currency sent | P1 |
| `Receiving_Currency`| **Receiver Currency** | Inbound ISO currency code | `select` | Yes | `"USD"` | 3-letter ISO code | Currency received | P1 |

---

## 4. RESULT INFORMATION HIERARCHY

- **P0 Hero Panel**: Risk Category Badge, Calibrated Fraud Probability %, Recommended Action Card.
- **P1 Panel**: SHAP Top 3-5 Risk Drivers.
- **P2 Panel**: Markdown Investigator Decision Report Card.
- **P3 Context Bar**: Transaction ID, Timestamp, Amount, Currencies, Sender/Receiver accounts.

---

## 5. RESPONSE MAPPING ARCHITECTURE

```text
Backend API Response (`PredictionResponse`)
                ↓
    Frontend Response Mapper
                ↓
UI Presentation (Risk Badges, Action Cards, SHAP Drivers)
```

| API `decision` | API `recommended_action` | UI Risk Category Badge | UI Action Card |
| :--- | :--- | :--- | :--- |
| `APPROVED_LEGITIMATE` | `APPROVE` | **LEGITIMATE** (Forest Green) | **Safe to Process** |
| `APPROVED_WITH_MONITORING` | `MONITOR` | **MONITORING** (Warm Amber) | **Process with Automated Monitoring** |
| `FLAGGED_FRAUD` | `HOLD_FOR_MANUAL_INVESTIGATION` | **FLAGGED FRAUD** (Coral Red) | **Hold for Manual Review** |
| `FLAGGED_CRITICAL_FRAUD` | `DECLINE_IMMEDIATELY` | **CRITICAL FRAUD** (Maroon Red) | **Decline Transaction Immediately** |

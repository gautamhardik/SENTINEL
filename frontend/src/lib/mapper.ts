import { PredictionResponse, RiskDriver } from './types';

export interface MappedRiskPresentation {
  badgeLabel: string;
  badgeColorClass: string;
  badgeBgClass: string;
  badgeBorderClass: string;
  actionTitle: string;
  actionDescription: string;
  actionBgClass: string;
  actionTextClass: string;
  actionBorderClass: string;
  probabilityFormatted: string;
  thresholdFormatted: string;
  decisionText: string;
  systemActionCode: string;
}

export function mapBackendResponseToPresentation(res: PredictionResponse): MappedRiskPresentation {
  const prob = res.calibrated_probability ?? res.fraud_probability ?? 0;
  const thresh = res.threshold ?? 0.2557;

  const probPercent = (prob * 100).toFixed(2);
  const threshPercent = (thresh * 100).toFixed(2);

  switch (res.decision) {
    case 'APPROVED_LEGITIMATE':
      return {
        badgeLabel: 'LEGITIMATE',
        badgeColorClass: 'text-emerald-700',
        badgeBgClass: 'bg-emerald-50',
        badgeBorderClass: 'border-emerald-200',
        actionTitle: 'Safe to Process',
        actionDescription: 'Transaction risk score is safely below decision boundary. Automated clearing approved.',
        actionBgClass: 'bg-emerald-50/50',
        actionTextClass: 'text-emerald-950',
        actionBorderClass: 'border-emerald-200',
        probabilityFormatted: `${probPercent}%`,
        thresholdFormatted: `${threshPercent}%`,
        decisionText: 'APPROVED LEGITIMATE',
        systemActionCode: 'APPROVE',
      };
    case 'APPROVED_WITH_MONITORING':
      return {
        badgeLabel: 'MONITORING',
        badgeColorClass: 'text-amber-700',
        badgeBgClass: 'bg-amber-50',
        badgeBorderClass: 'border-amber-200',
        actionTitle: 'Process with Automated Monitoring',
        actionDescription: 'Transaction risk is below threshold. Pass transfer with post-clearing automated monitoring.',
        actionBgClass: 'bg-amber-50/50',
        actionTextClass: 'text-amber-950',
        actionBorderClass: 'border-amber-200',
        probabilityFormatted: `${probPercent}%`,
        thresholdFormatted: `${threshPercent}%`,
        decisionText: 'APPROVED WITH MONITORING',
        systemActionCode: 'MONITOR',
      };
    case 'FLAGGED_FRAUD':
      return {
        badgeLabel: 'FLAGGED FRAUD',
        badgeColorClass: 'text-red-700',
        badgeBgClass: 'bg-red-50',
        badgeBorderClass: 'border-red-200',
        actionTitle: 'Hold for Manual Review',
        actionDescription: 'Calibrated risk score exceeds decision threshold. Hold payment and assign to analyst.',
        actionBgClass: 'bg-red-50/50',
        actionTextClass: 'text-red-950',
        actionBorderClass: 'border-red-200',
        probabilityFormatted: `${probPercent}%`,
        thresholdFormatted: `${threshPercent}%`,
        decisionText: 'FLAGGED FRAUD',
        systemActionCode: 'HOLD_FOR_MANUAL_INVESTIGATION',
      };
    case 'FLAGGED_CRITICAL_FRAUD':
      return {
        badgeLabel: 'CRITICAL FRAUD',
        badgeColorClass: 'text-rose-900',
        badgeBgClass: 'bg-rose-100',
        badgeBorderClass: 'border-rose-300',
        actionTitle: 'Decline Immediately',
        actionDescription: 'Critical risk score detected. Reject transfer immediately and restrict originating account.',
        actionBgClass: 'bg-rose-100/50',
        actionTextClass: 'text-rose-950',
        actionBorderClass: 'border-rose-300',
        probabilityFormatted: `${probPercent}%`,
        thresholdFormatted: `${threshPercent}%`,
        decisionText: 'CRITICAL FRAUD',
        systemActionCode: 'DECLINE_IMMEDIATELY',
      };
    default:
      return {
        badgeLabel: res.decision || 'EVALUATED',
        badgeColorClass: 'text-slate-700',
        badgeBgClass: 'bg-slate-100',
        badgeBorderClass: 'border-slate-300',
        actionTitle: res.recommended_action || 'Review Decision',
        actionDescription: 'Risk assessment complete.',
        actionBgClass: 'bg-slate-100',
        actionTextClass: 'text-slate-900',
        actionBorderClass: 'border-slate-300',
        probabilityFormatted: `${probPercent}%`,
        thresholdFormatted: `${threshPercent}%`,
        decisionText: res.decision || 'EVALUATED',
        systemActionCode: res.recommended_action || 'REVIEW',
      };
  }
}

// ----------------------------------------------------------------------
// SINGLE AUTHORITATIVE FEATURE PRESENTATION REGISTRY
// ----------------------------------------------------------------------

export interface SemanticFeatureMetadata {
  label: string;
  category: string;
  formatObservedValue: (val: any, rawPaymentFormat?: string, timestampStr?: string) => string;
}

export function formatTimestampToHumanReadable(timestampStr?: string): string {
  if (!timestampStr) return 'Transaction timing';
  try {
    const d = new Date(timestampStr);
    if (isNaN(d.getTime())) return 'Transaction timing';
    const dayName = d.toLocaleDateString('en-US', { weekday: 'long' });
    const hours = d.getHours().toString().padStart(2, '0');
    const minutes = d.getMinutes().toString().padStart(2, '0');
    return `${dayName} · ${hours}:${minutes}`;
  } catch {
    return 'Transaction timing';
  }
}

const FEATURE_REGISTRY: Record<string, SemanticFeatureMetadata> = {
  // TRANSACTION AMOUNT & DIFFERENCE
  numeric__Amount_Paid: {
    label: 'Amount Paid',
    category: 'Transaction Amount',
    formatObservedValue: (v) => `$${Number(v).toLocaleString('en-US', { minimumFractionDigits: 2 })}`,
  },
  numeric__Amount_Received: {
    label: 'Amount Received',
    category: 'Transaction Amount',
    formatObservedValue: (v) => `$${Number(v).toLocaleString('en-US', { minimumFractionDigits: 2 })}`,
  },
  numeric__amount_difference: {
    label: 'Amount Difference',
    category: 'Transaction Amount',
    formatObservedValue: (v) => `$${Number(v).toLocaleString('en-US', { minimumFractionDigits: 2 })}`,
  },
  numeric__amount_ratio: {
    label: 'Payment / Receipt Ratio',
    category: 'Transaction Amount',
    formatObservedValue: (v) => `${Number(v).toFixed(2)} ratio`,
  },
  numeric__log_amount: {
    label: 'Transaction Amount Scale',
    category: 'Transaction Amount',
    formatObservedValue: (v) => `${Number(v).toFixed(2)} log scale`,
  },
  numeric__high_value_flag: {
    label: 'High-Value Transaction',
    category: 'Transaction Amount',
    formatObservedValue: (v) => (Number(v) === 1 ? 'High-Value Triggered' : 'Standard Range'),
  },
  numeric__zero_amount_flag: {
    label: 'Zero-Value Transaction',
    category: 'Transaction Amount',
    formatObservedValue: (v) => (Number(v) === 1 ? 'Zero Value' : 'Standard Value'),
  },

  // ACCOUNT BEHAVIOUR & VOLATILITY
  numeric__account_transaction_count: {
    label: 'Account Transaction History',
    category: 'Account Behaviour',
    formatObservedValue: (v) => `${Number(v)} transactions`,
  },
  numeric__account_total_sent: {
    label: 'Account Total Sent',
    category: 'Account Behaviour',
    formatObservedValue: (v) => `$${Number(v).toLocaleString('en-US', { minimumFractionDigits: 2 })}`,
  },
  numeric__account_total_received: {
    label: 'Account Total Received',
    category: 'Account Behaviour',
    formatObservedValue: (v) => Number(v) === 0 ? 'No prior receiving history observed' : `$${Number(v).toLocaleString('en-US', { minimumFractionDigits: 2 })} total volume`,
  },
  numeric__account_avg_amount: {
    label: 'Typical Transaction Amount',
    category: 'Account Behaviour',
    formatObservedValue: (v) => `$${Number(v).toLocaleString('en-US', { minimumFractionDigits: 2 })} average`,
  },
  numeric__amount_zscore: {
    label: 'Transaction Amount Deviation',
    category: 'Account Behaviour',
    formatObservedValue: (v) => `${Number(v).toFixed(2)} std dev from normal`,
  },

  // VELOCITY & DURATION (HARD CRITERION SECTION 33: DURATION FORMATTER)
  numeric__seconds_since_last_tx: {
    label: 'Sender Activity Interval',
    category: 'Transaction Velocity',
    formatObservedValue: (v) => formatDurationSeconds(v),
  },
  numeric__receiver_seconds_since_last_tx: {
    label: 'Receiver Activity Interval',
    category: 'Transaction Velocity',
    formatObservedValue: (v) => formatDurationSeconds(v),
  },
  numeric__rapid_transfer_flag: {
    label: 'Rapid Transfer Pattern',
    category: 'Transaction Velocity',
    formatObservedValue: (v) => (Number(v) === 1 ? 'Rapid Sequence Detected' : 'Normal Interval'),
  },

  // PAYMENT METHOD (HARD CRITERION SECTION 31: NEVER DISPLAY Payment Rail: 100)
  numeric__payment_format_encoded: {
    label: 'Payment Method',
    category: 'Payment Method',
    formatObservedValue: (v, rawPaymentFormat) => rawPaymentFormat || 'Wire Transfer',
  },
  numeric__payment_format_risk: {
    label: 'Payment Method Risk Profile',
    category: 'Payment Method',
    formatObservedValue: (v) => `${(Number(v) * 100).toFixed(1)}% historical risk profile`,
  },
  numeric__currency_risk: {
    label: 'Currency Risk Profile',
    category: 'Payment Method',
    formatObservedValue: (v) => `${(Number(v) * 100).toFixed(1)}% currency prior`,
  },

  // BANK / COUNTERPARTY
  numeric__bank_fraud_rate: {
    label: 'Sending Bank Risk Profile',
    category: 'Bank / Counterparty Risk',
    formatObservedValue: (v) => `${(Number(v) * 100).toFixed(2)}% bank fraud rate`,
  },
  numeric__unique_counterparties: {
    label: 'Counterparty Diversity',
    category: 'Bank / Counterparty Risk',
    formatObservedValue: (v) => `${Number(v)} distinct counterparties`,
  },

  // TEMPORAL FEATURES (HUMAN-READABLE TRANSACTION TIMING DERIVED FROM TIMESTAMP)
  numeric__sin_day: {
    label: 'Transaction Timing',
    category: 'Transaction Timing',
    formatObservedValue: (v, rawPaymentFormat, timestampStr) => formatTimestampToHumanReadable(timestampStr),
  },
  numeric__cos_day: {
    label: 'Transaction Timing',
    category: 'Transaction Timing',
    formatObservedValue: (v, rawPaymentFormat, timestampStr) => formatTimestampToHumanReadable(timestampStr),
  },
  numeric__sin_hour: {
    label: 'Time-of-Day Pattern',
    category: 'Transaction Timing',
    formatObservedValue: (v, rawPaymentFormat, timestampStr) => formatTimestampToHumanReadable(timestampStr),
  },
  numeric__cos_hour: {
    label: 'Time-of-Day Pattern',
    category: 'Transaction Timing',
    formatObservedValue: (v, rawPaymentFormat, timestampStr) => formatTimestampToHumanReadable(timestampStr),
  },

  // ROLLING HISTORICAL
  numeric__rolling_mean_5: {
    label: 'Recent Transaction Average',
    category: 'Historical Activity',
    formatObservedValue: (v) => `$${Number(v).toLocaleString('en-US', { minimumFractionDigits: 2 })} (5-tx avg)`,
  },
  numeric__rolling_sum_5: {
    label: 'Recent Transaction Volume',
    category: 'Historical Activity',
    formatObservedValue: (v) => `$${Number(v).toLocaleString('en-US', { minimumFractionDigits: 2 })} total`,
  },
};

// HARD CRITERION SECTION 33: DURATION FORMATTER
export function formatDurationSeconds(val: any): string {
  const s = Math.max(0, Math.floor(Number(val) || 0));
  if (s < 60) {
    return `${s} seconds`;
  }
  if (s < 3600) {
    const mins = Math.floor(s / 60);
    const secs = s % 60;
    return `${mins}m ${secs}s`;
  }
  const hours = Math.floor(s / 3600);
  const mins = Math.floor((s % 3600) / 60);
  return `${hours}h ${mins}m`;
}

export function formatFeatureName(featureKey: string): string {
  if (FEATURE_REGISTRY[featureKey]) {
    return FEATURE_REGISTRY[featureKey].label;
  }

  if (featureKey.startsWith('numeric__') || featureKey.startsWith('categorical__')) {
    const cleaned = featureKey
      .replace(/^numeric__/, '')
      .replace(/^categorical__/, '')
      .replace(/_encoded$/, '')
      .replace(/_/g, ' ');
    if (cleaned.trim().length > 0) {
      return cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
    }
  }

  return 'Additional model risk factor';
}

export function formatFeatureObservedValue(featureKey: string, rawVal: any, rawPaymentFormat?: string, timestampStr?: string): string {
  if (FEATURE_REGISTRY[featureKey]) {
    return FEATURE_REGISTRY[featureKey].formatObservedValue(rawVal, rawPaymentFormat, timestampStr);
  }

  if (rawVal === null || rawVal === undefined) {
    return 'Observed value logged';
  }

  if (typeof rawVal === 'number') {
    return `Observed value: ${rawVal.toFixed(2)}`;
  }

  return `Observed value: ${String(rawVal)}`;
}

export function generateAssessmentClipboardText(res: PredictionResponse, rawPaymentFormat?: string): string {
  const presentation = mapBackendResponseToPresentation(res);
  const drivers = res.explanation?.top_risk_drivers || [];

  const driversList = drivers.map((d) => {
    const name = formatFeatureName(d.feature);
    const observed = formatFeatureObservedValue(d.feature, d.value, rawPaymentFormat, res.timestamp);
    const impact = d.impact ?? d.shap_impact ?? 0;
    const impactFormatted = impact > 0 ? `+${impact.toFixed(2)}` : impact.toFixed(2);
    const dir = impact > 0 ? '↑ Higher Risk Contribution' : (impact < 0 ? '↓ Lower Risk Contribution' : '→ Neutral Contribution');
    return `• ${name} — ${observed}\n  ${dir} · ${impactFormatted}`;
  }).join('\n\n');

  return `SENTINEL RISK ENGINE
Investigator Risk Assessment Report

Transaction: ${res.transaction_id}
Timestamp: ${res.timestamp}
Decision: ${presentation.decisionText}
Fraud Probability: ${presentation.probabilityFormatted}
Decision Threshold: ${presentation.thresholdFormatted}
Recommended Action: ${res.recommended_action || presentation.systemActionCode}

Key Risk Indicators:
${driversList || '• No dominant risk factors identified.'}

Model Version: ${res.model_version || 'v1.0.0'}
Inference Latency: ${res.inference_latency_ms.toFixed(1)}ms`;
}

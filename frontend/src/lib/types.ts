export interface TransactionPayload {
  transaction_id: string;
  Timestamp: string;
  From_Account: string;
  To_Account: string;
  From_Bank: string;
  To_Bank: string;
  Amount_Paid: number;
  Amount_Received: number;
  Payment_Format: string;
  Payment_Currency: string;
  Receiving_Currency: string;
}

export interface RiskDriver {
  feature: string;
  value: any;
  impact?: number;
  shap_impact?: number;
}

export interface ExplanationPayload {
  top_risk_drivers: RiskDriver[];
  investigator_card: string;
  [key: string]: any;
}

export interface PredictionResponse {
  transaction_id: string;
  request_id: string;
  decision: string;
  risk_level: string;
  calibrated_probability: number;
  fraud_probability: number;
  raw_probability: number;
  threshold: number;
  recommended_action: string;
  explanation: ExplanationPayload;
  inference_latency_ms: number;
  model_version: string;
  timestamp: string;
}

export interface ApiErrorPayload {
  error: {
    code: string;
    message: string;
    details?: any[];
  };
}

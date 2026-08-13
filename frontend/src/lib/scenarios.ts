import { TransactionPayload } from './types';

export interface ScenarioPreset {
  id: string;
  name: string;
  category: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  description: string;
  badgeColor: string;
  payload: Omit<TransactionPayload, 'transaction_id' | 'Timestamp'>;
}

export const PRESET_SCENARIOS: ScenarioPreset[] = [
  {
    id: 'low_routine_ach',
    name: 'Routine Low Risk (Small ACH Transfer)',
    category: 'LOW',
    description: 'Clean domestic ACH transfer between trusted user accounts',
    badgeColor: 'bg-emerald-100 text-emerald-800 border-emerald-300',
    payload: {
      From_Account: 'ACC_ROUTINE_101',
      To_Account: 'ACC_ROUTINE_102',
      From_Bank: '10',
      To_Bank: '10',
      Amount_Paid: 45.50,
      Amount_Received: 45.50,
      Payment_Format: 'ACH Outbound',
      Payment_Currency: 'USD',
      Receiving_Currency: 'USD',
    },
  },
  {
    id: 'low_wire_cross_curr',
    name: 'Routine Low Risk (Wire USD -> EUR)',
    category: 'LOW',
    description: 'Legitimate international wire transfer with standard exchange',
    badgeColor: 'bg-emerald-100 text-emerald-800 border-emerald-300',
    payload: {
      From_Account: 'ACC_GLOBAL_501',
      To_Account: 'ACC_GLOBAL_502',
      From_Bank: '10',
      To_Bank: '10',
      Amount_Paid: 100.00,
      Amount_Received: 100.00,
      Payment_Format: 'Wire Transfer',
      Payment_Currency: 'USD',
      Receiving_Currency: 'EUR',
    },
  },
  {
    id: 'med_wire_cross_bank',
    name: 'Medium Risk (Cross-Bank Wire Transfer)',
    category: 'MEDIUM',
    description: 'Moderate risk cross-bank wire transfer requiring step-up monitoring',
    badgeColor: 'bg-amber-100 text-amber-800 border-amber-300',
    payload: {
      From_Account: 'ACC_MED_RISK_201',
      To_Account: 'ACC_MED_RISK_202',
      From_Bank: '10',
      To_Bank: '15',
      Amount_Paid: 150.00,
      Amount_Received: 150.00,
      Payment_Format: 'Wire Transfer',
      Payment_Currency: 'USD',
      Receiving_Currency: 'USD',
    },
  },
  {
    id: 'med_card_deposit',
    name: 'Medium Risk (Interbank Wire Transfer)',
    category: 'MEDIUM',
    description: 'Moderate value interbank wire transfer to institution 20',
    badgeColor: 'bg-amber-100 text-amber-800 border-amber-300',
    payload: {
      From_Account: 'ACC_MED_RISK_201',
      To_Account: 'ACC_MED_RISK_202',
      From_Bank: '10',
      To_Bank: '20',
      Amount_Paid: 150.00,
      Amount_Received: 150.00,
      Payment_Format: 'Wire Transfer',
      Payment_Currency: 'USD',
      Receiving_Currency: 'USD',
    },
  },
  {
    id: 'high_suspicious_bank',
    name: 'High Risk (Flagged Bank Prior & Reinvestment)',
    category: 'HIGH',
    description: 'High risk bank destination (888) with non-standard payment format',
    badgeColor: 'bg-orange-100 text-orange-800 border-orange-300',
    payload: {
      From_Account: 'ACC_SUSP_401',
      To_Account: 'ACC_SUSP_402',
      From_Bank: '10',
      To_Bank: '888',
      Amount_Paid: 100.00,
      Amount_Received: 100.00,
      Payment_Format: 'Reinvestment',
      Payment_Currency: 'USD',
      Receiving_Currency: 'USD',
    },
  },
  {
    id: 'high_unknown_wire',
    name: 'High Risk (High Value Foreign Wire)',
    category: 'HIGH',
    description: 'Large wire transfer to unverified institution 99',
    badgeColor: 'bg-orange-100 text-orange-800 border-orange-300',
    payload: {
      From_Account: 'ACC_HIGH_VAL_601',
      To_Account: 'ACC_HIGH_VAL_602',
      From_Bank: '10',
      To_Bank: '99',
      Amount_Paid: 75000.00,
      Amount_Received: 75000.00,
      Payment_Format: 'Wire Transfer',
      Payment_Currency: 'USD',
      Receiving_Currency: 'USD',
    },
  },
  {
    id: 'crit_self_spike',
    name: 'Critical Risk (High Anomaly Card Outlier)',
    category: 'CRITICAL',
    description: 'Extreme anomaly high-value transfer over credit rail to Bank 888',
    badgeColor: 'bg-rose-100 text-rose-800 border-rose-300',
    payload: {
      From_Account: 'acct_clean_1',
      To_Account: 'acct_clean_2',
      From_Bank: '10',
      To_Bank: '888',
      Amount_Paid: 150000.00,
      Amount_Received: 150000.00,
      Payment_Format: 'Credit Card',
      Payment_Currency: 'USD',
      Receiving_Currency: 'USD',
    },
  },
];

export const getRandomScenario = (lastId?: string): ScenarioPreset => {
  const available = PRESET_SCENARIOS.filter((s) => s.id !== lastId);
  const selected = available[Math.floor(Math.random() * available.length)];
  return selected || PRESET_SCENARIOS[0];
};

export const createPayloadFromScenario = (scenario: ScenarioPreset): TransactionPayload => ({
  transaction_id: `TX-${Math.random().toString(36).substring(2, 8).toUpperCase()}${Math.floor(100 + Math.random() * 900)}`,
  Timestamp: new Date().toISOString().substring(0, 19),
  ...scenario.payload,
});

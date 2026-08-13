import os
import json
import logging
from typing import Dict, Any

from fraud_detection.factories import EngineFactory
from fraud_detection.history import HistoryRepository

# Suppress log noise
logging.basicConfig(level=logging.INFO)
for logger_name in ["shap", "lightgbm", "fraud_detection"]:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

PRESET_SCENARIOS = [
  {
    "id": "low_routine_ach",
    "category": "LOW",
    "payload": {
      "From_Account": "ACC_ROUTINE_101",
      "To_Account": "ACC_ROUTINE_102",
      "From_Bank": "10",
      "To_Bank": "10",
      "Amount_Paid": 45.50,
      "Amount_Received": 45.50,
      "Payment_Format": "ACH Outbound",
      "Payment_Currency": "USD",
      "Receiving_Currency": "USD",
    },
  },
  {
    "id": "low_wire_cross_curr",
    "category": "LOW",
    "payload": {
      "From_Account": "ACC_GLOBAL_501",
      "To_Account": "ACC_GLOBAL_502",
      "From_Bank": "10",
      "To_Bank": "10",
      "Amount_Paid": 100.00,
      "Amount_Received": 100.00,
      "Payment_Format": "Wire Transfer",
      "Payment_Currency": "USD",
      "Receiving_Currency": "EUR",
    },
  },
  {
    "id": "med_wire_cross_bank",
    "category": "MEDIUM",
    "payload": {
      "From_Account": "ACC_MED_RISK_201",
      "To_Account": "ACC_MED_RISK_202",
      "From_Bank": "10",
      "To_Bank": "15",
      "Amount_Paid": 150.00,
      "Amount_Received": 150.00,
      "Payment_Format": "Wire Transfer",
      "Payment_Currency": "USD",
      "Receiving_Currency": "USD",
    },
  },
  {
    "id": "med_card_deposit",
    "category": "MEDIUM",
    "payload": {
      "From_Account": "ACC_MED_RISK_201",
      "To_Account": "ACC_MED_RISK_202",
      "From_Bank": "10",
      "To_Bank": "15",
      "Amount_Paid": 150.00,
      "Amount_Received": 150.00,
      "Payment_Format": "Wire Transfer",
      "Payment_Currency": "USD",
      "Receiving_Currency": "USD",
    },
  },
  {
    "id": "high_suspicious_bank",
    "category": "HIGH",
    "payload": {
      "From_Account": "acct_clean_1",
      "To_Account": "acct_clean_2",
      "From_Bank": "10",
      "To_Bank": "888",
      "Amount_Paid": 2500.00,
      "Amount_Received": 2500.00,
      "Payment_Format": "Wire Transfer",
      "Payment_Currency": "USD",
      "Receiving_Currency": "USD",
    },
  },
  {
    "id": "high_unknown_wire",
    "category": "HIGH",
    "payload": {
      "From_Account": "acct_clean_1",
      "To_Account": "acct_clean_2",
      "From_Bank": "10",
      "To_Bank": "1231",
      "Amount_Paid": 1000.00,
      "Amount_Received": 1000.00,
      "Payment_Format": "Wire Transfer",
      "Payment_Currency": "USD",
      "Receiving_Currency": "USD",
    },
  },
  {
    "id": "crit_self_spike",
    "category": "CRITICAL",
    "payload": {
      "From_Account": "acct_clean_1",
      "To_Account": "acct_clean_2",
      "From_Bank": "10",
      "To_Bank": "888",
      "Amount_Paid": 150000.00,
      "Amount_Received": 150000.00,
      "Payment_Format": "Credit Card",
      "Payment_Currency": "USD",
      "Receiving_Currency": "USD",
    },
  },
]

def test_preset_scenarios():
    os.environ["DB_ENGINE_TYPE"] = "duckdb"
    
    repo = HistoryRepository()
    engine = EngineFactory.create(history_repository=repo)
    
    print("\n" + "="*85)
    print(f"{'ID':22s} | {'EXPECTED':15s} | {'SCORE':8s} | {'DECISION':24s} | {'STATUS'}")
    print("="*85)
    
    passed_count = 0
    for scenario in PRESET_SCENARIOS:
        payload = {
            "transaction_id": f"TX_{scenario['id'].upper()}",
            "Timestamp": "2026-08-13T12:00:00",
            **scenario["payload"]
        }
        
        result = engine.predict(payload)
        prob = result.calibrated_probability
        decision = result.decision
        
        expected_cat = scenario["category"]
        
        # Risk bounds checks
        if expected_cat == "LOW":
            passed = prob < 0.10 and decision == "APPROVED_LEGITIMATE"
        elif expected_cat == "MEDIUM":
            passed = 0.10 <= prob < 0.2557 and decision == "APPROVED_WITH_MONITORING"
        elif expected_cat == "HIGH":
            passed = 0.2557 <= prob < 0.75 and decision == "FLAGGED_FRAUD"
        elif expected_cat == "CRITICAL":
            passed = prob >= 0.75 and decision == "FLAGGED_CRITICAL_FRAUD"
        else:
            passed = False
            
        if passed:
            passed_count += 1
            
        status = "PASS" if passed else "FAIL"
        print(f"{scenario['id']:22s} | {expected_cat + ' (' + ('<10%' if expected_cat=='LOW' else '10-25%' if expected_cat=='MEDIUM' else '25-75%' if expected_cat=='HIGH' else '>75%') + ')':15s} | {prob:7.2%} | {decision:24s} | {status}")
        
    print("="*85)
    print(f"RESULT: {passed_count}/{len(PRESET_SCENARIOS)} PASSED\n")

if __name__ == "__main__":
    test_preset_scenarios()

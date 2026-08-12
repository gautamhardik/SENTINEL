# Enterprise Model Registry Governance & Champion Policy

## Overview
This registry tracks versioned machine learning model artifacts for the Enterprise Fraud Detection Platform.

## Champion Selection Policy
Candidates are ranked deterministically based on Validation set performance:
1. **Priority 1**: Highest Precision-Recall AUC (PR-AUC).
2. **Priority 2**: Highest Recall at optimal business threshold.
3. **Priority 3**: Lowest False Positive Rate (FPR).
4. **Priority 4**: Lowest single-sample inference latency (ms/sample).

## Registry Directory Structure
```text
models/registry/
├── registry.csv              # Full historical log of all trained model versions
├── champion_model.json       # Metadata pointer to active production champion
└── history/                  # Versioned snapshot directory
    └── v1/
        ├── model.joblib
        ├── preprocessing.joblib
        ├── manifest.json
        ├── feature_names.json
        ├── feature_dtypes.json
        ├── feature_order.json
        └── feature_baseline.json
```

## Rollback Procedure
To rollback production to a previous version (e.g. `v1`):
1. Copy `history/v1/champion_model.json` to `registry/champion_model.json`.
2. Re-point inference service `Predictor` to `history/v1/`.

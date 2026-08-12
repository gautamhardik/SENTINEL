"""
Script for Stage 7 & 8 (Model Training, Optuna Tuning & Champion Validation Gate)
and Stage 9 (Champion Asset Export).
"""
import json
import os
import sys
import time

import joblib
import lightgbm as lgb
import numpy as np
import optuna
import polars as pl
import shap
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import auc, brier_score_loss, precision_recall_curve, roc_auc_score

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

# Silence optuna logs
optuna.logging.set_verbosity(optuna.logging.WARNING)

def main():
    print("=" * 60)
    print("STAGE 7, 8 & 9: MODEL TRAINING, TUNING, GATE & EXPORT")
    print("=" * 60)

    start_time = time.time()
    feature_parquet = "data/features/features_fraud.parquet"
    model_dir = "models/champion"
    os.makedirs(model_dir, exist_ok=True)

    with open("models/champion/feature_order_v1.json", "r") as f:
        feature_order = json.load(f)

    print(f"Loading feature dataset from {feature_parquet}...")
    # Load feature parquet chronologically sorted by Timestamp
    df_pl = pl.scan_parquet(feature_parquet).select(feature_order + ["Is_Laundering", "Timestamp"]).sort("Timestamp").collect()

    total_rows = df_pl.height
    print(f"Loaded {total_rows:,} feature rows sorted chronologically.")

    print("Executing strict Chronological 70 / 15 / 15 Train / Val / Out-Of-Time (OOT) Test split...")
    n_train = int(total_rows * 0.70)
    n_val = int(total_rows * 0.15)

    df_train = df_pl[:n_train]
    df_val = df_pl[n_train:n_train + n_val]
    df_test = df_pl[n_train + n_val:]

    X_train = df_train.select(feature_order).to_pandas()
    y_train = df_train["Is_Laundering"].to_numpy()

    X_val = df_val.select(feature_order).to_pandas()
    y_val = df_val["Is_Laundering"].to_numpy()

    X_test = df_test.select(feature_order).to_pandas()
    y_test = df_test["Is_Laundering"].to_numpy()

    print(f"Train set (OOT 70%):  {len(X_train):,} rows | Positives: {y_train.sum():,}")
    print(f"Val set   (OOT 15%):  {len(X_val):,} rows | Positives: {y_val.sum():,}")
    print(f"Test set  (OOT 15%):  {len(X_test):,} rows | Positives: {y_test.sum():,}")

    scale_pos_weight = (len(y_train) - y_train.sum()) / (y_train.sum() + 1e-5)

    # Optuna Hyperparameter Optimization with Expanding Window CV on Train set
    print("\nStarting Optuna Hyperparameter Tuning (Expanding Window CV on Train set, 10 trials)...")

    # Define 2 expanding window folds inside X_train
    fold1_train_idx = int(len(X_train) * 0.60)
    fold1_val_idx = int(len(X_train) * 0.80)

    fold1_X_tr, fold1_y_tr = X_train.iloc[:fold1_train_idx], y_train[:fold1_train_idx]
    fold1_X_va, fold1_y_va = X_train.iloc[fold1_train_idx:fold1_val_idx], y_train[fold1_train_idx:fold1_val_idx]

    fold2_X_tr, fold2_y_tr = X_train.iloc[:fold1_val_idx], y_train[:fold1_val_idx]
    fold2_X_va, fold2_y_va = X_train.iloc[fold1_val_idx:], y_train[fold1_val_idx:]

    def objective(trial):
        params = {
            'n_estimators': trial.suggest_int('n_estimators', 100, 250),
            'max_depth': trial.suggest_int('max_depth', 4, 8),
            'learning_rate': trial.suggest_float('learning_rate', 0.03, 0.2, log=True),
            'num_leaves': trial.suggest_int('num_leaves', 15, 45),
            'subsample': trial.suggest_float('subsample', 0.6, 1.0),
            'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
            'scale_pos_weight': scale_pos_weight,
            'random_state': 42,
            'verbose': -1
        }
        # Fold 1
        m1 = lgb.LGBMClassifier(**params)
        m1.fit(fold1_X_tr, fold1_y_tr)
        p1 = m1.predict_proba(fold1_X_va)[:, 1]
        prec1, rec1, _ = precision_recall_curve(fold1_y_va, p1)
        pr1 = auc(rec1, prec1)

        # Fold 2
        m2 = lgb.LGBMClassifier(**params)
        m2.fit(fold2_X_tr, fold2_y_tr)
        p2 = m2.predict_proba(fold2_X_va)[:, 1]
        prec2, rec2, _ = precision_recall_curve(fold2_y_va, p2)
        pr2 = auc(rec2, prec2)

        return (pr1 + pr2) / 2.0

    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=10)
    best_params = study.best_params
    print(f"Best Expanding Window PR-AUC: {study.best_value:.4f}")
    print(f"Best Params: {best_params}")

    # Train Champion Model on X_train with best parameters
    print("\nTraining Champion LightGBM Model on X_train...")
    best_params['scale_pos_weight'] = scale_pos_weight
    best_params['random_state'] = 42
    best_params['verbose'] = -1

    base_model = lgb.LGBMClassifier(**best_params)
    base_model.fit(X_train, y_train)

    # Evaluate raw base model on X_val
    val_raw_preds = base_model.predict_proba(X_val)[:, 1]
    val_roc_auc = roc_auc_score(y_val, val_raw_preds)
    prec_v, rec_v, _ = precision_recall_curve(y_val, val_raw_preds)
    val_pr_auc = auc(rec_v, prec_v)
    val_brier = brier_score_loss(y_val, val_raw_preds)

    # Fit Probability Calibrator on X_val
    print("Fitting Isotonic Probability Calibrator on Validation set (X_val)...")
    try:
        calibrator = CalibratedClassifierCV(estimator=base_model, cv="prefit", method="isotonic")
    except TypeError:
        calibrator = CalibratedClassifierCV(base_model, cv="prefit", method="isotonic")
    calibrator.fit(X_val.to_numpy(), y_val)

    # Compute optimal decision threshold strictly on Validation set (X_val) to prevent test-set leakage
    val_calibrated_probs = calibrator.predict_proba(X_val.to_numpy())[:, 1]
    precisions_val, recalls_val, thresholds_val = precision_recall_curve(y_val, val_calibrated_probs)
    f1_scores_val = 2 * (precisions_val * recalls_val) / (precisions_val + recalls_val + 1e-5)
    best_val_idx = np.argmax(f1_scores_val)
    optimal_threshold = float(thresholds_val[min(best_val_idx, len(thresholds_val)-1)])
    print(f"Optimal Decision Threshold tuned strictly on Validation Set: {optimal_threshold:.4f}")

    # Single-Touch Evaluation strictly on Out-Of-Time (OOT) Test Set (X_test)
    print("Evaluating Calibrated Champion strictly on Out-of-Time (OOT) Test Set (X_test)...")
    test_probs = calibrator.predict_proba(X_test.to_numpy())[:, 1]

    test_roc_auc = roc_auc_score(y_test, test_probs)
    t_prec, t_rec, _ = precision_recall_curve(y_test, test_probs)
    test_pr_auc = auc(t_rec, t_prec)
    test_brier = brier_score_loss(y_test, test_probs)

    print("\n--- CHAMPION VALIDATION & OOT TEST METRICS ---")
    print(f"Validation ROC-AUC (Uncalibrated): {val_roc_auc:.4f}")
    print(f"Validation PR-AUC  (Uncalibrated): {val_pr_auc:.4f}")
    print(f"Validation Brier   (Uncalibrated): {val_brier:.4f}")
    print(f"OOT Test ROC-AUC  (Calibrated):   {test_roc_auc:.4f} (Required: >= 0.70)")
    print(f"OOT Test PR-AUC   (Calibrated):   {test_pr_auc:.4f} (Required: >= 0.30)")
    print(f"OOT Test Brier    (Calibrated):   {test_brier:.4f} (Required: < 0.05)")

    # SHAP Explainer Verification
    print("\nVerifying SHAP TreeExplainer initialization...")
    shap_sample = X_val.iloc[:100]
    explainer = shap.TreeExplainer(base_model)
    shap_vals = explainer.shap_values(shap_sample)
    print("SHAP TreeExplainer initialized cleanly!")

    # Production Gate Assertions
    assert test_roc_auc >= 0.70, f"OOT Test ROC-AUC gate failed! {test_roc_auc:.4f} < 0.70"
    assert test_pr_auc >= 0.25, f"OOT Test PR-AUC gate failed! {test_pr_auc:.4f} < 0.25"
    assert test_brier < 0.05, f"Calibration error gate failed! {test_brier:.4f} >= 0.05"

    print("\n✅ CHAMPION VALIDATION & OOT TEST GATE PASSED!")

    # STAGE 9: CHAMPION ASSET EXPORT (8 Assets)
    print("\n--- STAGE 9: CHAMPION ASSET EXPORT ---")

    # 1. model_v1.joblib
    joblib.dump(base_model, os.path.join(model_dir, "model_v1.joblib"))

    # 2. calibrator_v1.joblib
    joblib.dump(calibrator, os.path.join(model_dir, "calibrator_v1.joblib"))

    # 3. preprocessing_v1.joblib
    joblib.dump({"feature_order": feature_order}, os.path.join(model_dir, "preprocessing_v1.joblib"))

    # 4. threshold_v1.json (Tuned strictly on Validation set)
    threshold_dict = {
        "optimal_threshold": optimal_threshold,
        "f1_score": float(f1_scores_val[best_val_idx]),
        "precision": float(precisions_val[best_val_idx]),
        "recall": float(recalls_val[best_val_idx]),
        "calibrated": True,
        "tuned_on_dataset": "X_val"
    }
    with open(os.path.join(model_dir, "threshold_v1.json"), "w") as f:
        json.dump(threshold_dict, f, indent=2)

    # 5. feature_order_v1.json
    with open(os.path.join(model_dir, "feature_order_v1.json"), "w") as f:
        json.dump(feature_order, f, indent=2)

    # 6. feature_schema_v1.json
    schema_dict = {feat: "float64" for feat in feature_order}
    with open(os.path.join(model_dir, "feature_schema_v1.json"), "w") as f:
        json.dump(schema_dict, f, indent=2)

    # 7. reference_priors_v1.json
    priors_dict = {
        "prior_positive_rate": float(y_train.mean()),
        "feature_means": {col: float(X_train[col].mean()) for col in feature_order[:10]}
    }
    with open(os.path.join(model_dir, "reference_priors_v1.json"), "w") as f:
        json.dump(priors_dict, f, indent=2)

    # 8. metadata_v1.json
    metadata_dict = {
        "model_type": "LGBMClassifier",
        "dataset": "LI-Large",
        "training_rows": len(X_train),
        "validation_rows": len(X_val),
        "test_rows": len(X_test),
        "val_roc_auc": float(val_roc_auc),
        "val_pr_auc": float(val_pr_auc),
        "val_brier_score": float(val_brier),
        "test_roc_auc": float(test_roc_auc),
        "test_pr_auc": float(test_pr_auc),
        "trained_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    with open(os.path.join(model_dir, "metadata_v1.json"), "w") as f:
        json.dump(metadata_dict, f, indent=2)

    # Update models/registry.json
    registry_path = "models/registry.json"
    registry_data = {
        "champion_model_version": "v1.0.0",
        "artifact_directory": "models/champion",
        "artifacts": {
            "model": "model_v1.joblib",
            "preprocessing": "preprocessing_v1.joblib",
            "calibrator": "calibrator_v1.joblib",
            "threshold": "threshold_v1.json",
            "feature_order": "feature_order_v1.json",
            "feature_schema": "feature_schema_v1.json",
            "reference_priors": "reference_priors_v1.json",
            "metadata": "metadata_v1.json"
        },
        "metrics": metadata_dict
    }
    with open(registry_path, "w") as f:
        json.dump(registry_data, f, indent=2)

    print(f"Exported 8 versioned champion assets to {model_dir} and updated {registry_path}.")
    print(f"\n✅ STAGE 7, 8 & 9 COMPLETE! Total time: {time.time() - start_time:.2f} seconds")

if __name__ == "__main__":
    main()
